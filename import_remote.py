import requests
import json
import os
import re
import time
from tqdm import tqdm
import concurrent.futures as futures
from typing import Callable, Dict, Iterable, Optional, Tuple, List, Set
from pyquery import PyQuery
import urllib.parse as urlparse
from requests.models import Response
from functools import wraps
from threading import Lock
import clip_model
import ocr_model
from pymongo.collection import Collection
import utils
from datetime import datetime
import glob

###################################### Tips!!! ######################################
# if u want to show a pixiv image, u can use this function to get the image content #
# getImageResponseContent(url)                                                      #                                         
# it will return the image content in bytes                                         #
#####################################################################################

# case 1: download bookmarks
# n_images: max number of images to download
# capacity: limit of download size
# app = BookmarkCrawler(n_images=20, capacity=2000)
# app.run()

# case 2: download a certain artist's works
# app = UserCrawler(artist_id="6657532", capacity=2000)
# app.run()

# case 3: download images by keyword
# keyword: keyword to search
# order: False - by date, True - by popularity
# mode: safe, r18, all
# app = KeywordCrawler(keyword="Genshin",
#                      order=False, mode=["safe", "r18", "all"][-1], n_images=20, capacity=2000)
# app.run()


# config
OUTPUT_CONFIG = {
    # verbose mode
    "VERBOSE": True,
    # debug mode
    "PRINT_ERROR": True
}

NETWORK_CONFIG = {
    # clash default
    "PROXY": {"https": "127.0.0.1:7890"},
    "HEADER": {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/101.0.4951.54 Safari/537.36",
    }
}

USER_CONFIG = {
    # your uid , get from profile page: https://www.pixiv.net/users/{UID}
    "USER_ID": "101646786",
    # https://www.pixiv.net/ranking.php - F12 - Network - refresh - ranking.php - copy the cookie
    "COOKIE": "first_visit_datetime_pc=2024-04-04%2022%3A15%3A25; cc1=2024-04-04%2022%3A15%3A25; __cf_bm=wdhpSECu9ccvqdmexsNGbzw9ALKnjIrQrFSzxloL3_E-1712236525-1.0.1.1-7qLu7BTvzXWtFzRRhrscqJbAlb8n5zKG6EM_ecx2EeMYUlO0mzvBobG5AUn6eEUbS_DIDiu29bjf7h.3xll9gZTKpbPybiU..rYAD_kdS.Y; p_ab_id=8; p_ab_id_2=7; p_ab_d_id=365498253; yuid_b=JJZ4aEA; cf_clearance=hzuyb2owmYKN3_1MpH.3rfybZwCRqAQPUa3pf2KhGMY-1712236528-1.0.1.1-jq5jFo0pno71QHwGy1dpcXCXzdxtGS12UnGoAaHJCvvwz2dQ_3cwtdNw4SAnmLO6oAergegl5CM88gaHDcYaog; _gid=GA1.2.1464907464.1712236533; PHPSESSID=101646786_rX2cfjjK5Fr9OTNJuNOcX6wUyjS9EYcl; device_token=19785245088c97823b5623e8298fbcd4; privacy_policy_agreement=6; c_type=24; privacy_policy_notification=0; a_type=0; b_type=1; _ga_MZ1NL4PHH0=GS1.1.1712236542.1.0.1712236793.0.0.0; _im_vid=01HTMM8BRGNV53GQB9GZJYYREG; QSI_S_ZN_5hF4My7Ad6VNNAi=v:0:0; login_ever=yes; _gcl_au=1.1.1142587435.1712236858; _ga_75BBYNYN9J=GS1.1.1712236531.1.1.1712236861.0.0.0; _ga=GA1.2.112172624.1712236531; _gat_UA-1830249-3=1"
}

DOWNLOAD_CONFIG = {
    "STORE_PATH": "image_remote/",
    # times of retrying
    "N_TIMES": 2,
    # tag.json
    "WITH_TAG": False,
    # the delay time when failing
    "FAIL_DELAY": 3,
    # concurrency
    "N_THREAD": 8,
    # delay of starting a thread
    "THREAD_DELAY": 1,
}

log_lock = Lock()

def writeFailLog(text: str):
    with log_lock:
        with open("fail_log.txt", "a+") as f:
            f.write(text)

def timeLog(func):
    @wraps(func)
    def clocked(*args, **kwargs):
        from time import time
        start_time = time()
        ret = func(*args, **kwargs)
        print("{}() finishes after {:.2f} s".format(
            func.__name__, time() - start_time))
        return ret
    return clocked

def printInfo(msg):
    print("[INFO]: {}".format(msg))

def printWarn(expr: bool, msg):
    if expr:
        print("[WARN]: {}".format(msg))

def printError(expr: bool, msg):
    if expr:
        print("[ERROR]: {}".format(msg))
        raise RuntimeError()

def checkDir(dir_path):
    if not os.path.exists(dir_path):
        os.makedirs(dir_path)
        printInfo(f"create {dir_path}")

def import_single_image(filename: str, url: str, clip: clip_model.CLIPModel, ocr: ocr_model.OCRModel,
                        config: dict, mongo_collection: Collection) -> None:
    # if there is an item with the same url, then skip
    if mongo_collection.find_one({"url": url}) is not None:
        print("Skipping file:", filename)
        return
    filetype = utils.get_file_type(filename)
    if filetype is None:
        print("Skipping file:", filename)
        return

    image_feature, image_size = clip.get_image_feature(filename)
    if image_feature is None:
        print("Skipping file:", filename)
        return
    image_feature = image_feature.astype(config['storage-type'])

    ocr_text = ocr.get_ocr_text(filename)

    stat = os.stat(filename)

    image_mtime = datetime.fromtimestamp(stat.st_mtime)
    image_datestr = image_mtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Save to MongoDB
    document = {
        'url': url,
        'extension': filetype,
        'height': image_size[1],
        'width': image_size[0],
        'filesize': stat.st_size,
        'date': image_datestr,
        'feature': image_feature.tobytes(),
        'ocr_text': ocr_text
    }

    ret = mongo_collection.insert_one(document)

    try:
        os.remove(filename)
    except:
        print("remove failed")

def getImageResponseContent(url):
    image_name = url[url.rfind("/") + 1:]
    result = re.search("/(\d+)_", url)
    printError(result is None, "bad url in image downloader")
    image_id = result.group(1)
    headers = {"Referer": f"https://www.pixiv.net/artworks/{image_id}"}
    headers.update(NETWORK_CONFIG["HEADER"])

    response = requests.get(
    url, headers=headers,
    proxies=NETWORK_CONFIG["PROXY"],
    timeout=(3, 10))

    return response.content

class Downloader():
    def __init__(self, capacity):
        self.url_group: Set[str] = set()
        self.capacity = capacity
        self.clip = clip_model.get_model()
        self.ocr = ocr_model.get_ocr_model()
        self.config = utils.get_config()
        self.mongo_collection = utils.get_mongo_collection(isRemote=True)

    def add(self, urls: Iterable[str]):
        for url in urls:
            self.url_group.add(url)

    def downloadImage(self, url: str) -> float:
        image_name = url[url.rfind("/") + 1:]
        result = re.search("/(\d+)_", url)
        printError(result is None, "bad url in image downloader")
        image_id = result.group(1)
        print("image_id:", image_id)    
        headers = {"Referer": f"https://www.pixiv.net/artworks/{image_id}"}
        headers.update(NETWORK_CONFIG["HEADER"])

        verbose_output = OUTPUT_CONFIG["VERBOSE"]
        error_output = OUTPUT_CONFIG["PRINT_ERROR"]
        if verbose_output:
            printInfo(f"downloading {image_name}")
        time.sleep(DOWNLOAD_CONFIG["THREAD_DELAY"])

        image_path = DOWNLOAD_CONFIG["STORE_PATH"] + image_name
        if os.path.exists(image_path):
            printWarn(verbose_output, f"{image_path} exists")
            return 0

        wait_time = 10
        for i in range(DOWNLOAD_CONFIG["N_TIMES"]):
            try:
                response = requests.get(
                    url, headers=headers,
                    proxies=NETWORK_CONFIG["PROXY"],
                    timeout=(4, wait_time))

                if response.status_code == 200:
                    image_size = int(
                        response.headers["content-length"])
                    # delete incomplete image
                    if len(response.content) != image_size:
                        time.sleep(DOWNLOAD_CONFIG["FAIL_DELAY"])
                        wait_time += 2
                        continue

                    with open(image_path, "wb") as f:
                        f.write(response.content)
                    import_single_image(image_path, url, self.clip, self.ocr, self.config, self.mongo_collection)
                    if verbose_output:
                        printInfo(f"{image_name} complete")
                    return image_size / (1 << 20)

            except Exception as e:
                printWarn(error_output, e)
                printWarn(error_output,
                        f"This is {i} attempt to download {image_name}")

                time.sleep(DOWNLOAD_CONFIG["FAIL_DELAY"])

        printWarn(error_output, f"fail to download {image_name}")
        writeFailLog(f"fail to download {image_name} \n")
        return 0

    def download(self):
        flow_size = .0
        printInfo("===== downloader start =====")

        n_thread = DOWNLOAD_CONFIG["N_THREAD"]
        with futures.ThreadPoolExecutor(n_thread) as executor:
            with tqdm(total=len(self.url_group), desc="downloading") as pbar:
                for image_size in executor.map(
                        self.downloadImage, self.url_group):
                    flow_size += image_size
                    pbar.update()
                    pbar.set_description(
                        f"downloading / flow {flow_size:.2f}MB")
                    if flow_size > self.capacity:
                        executor.shutdown(wait=False, cancel_futures=True)
                        break

        printInfo("===== downloader complete =====")
        os.rmdir(DOWNLOAD_CONFIG["STORE_PATH"])
        return flow_size
    

def collect(args: Tuple[str, Callable, Optional[Dict]]) \
        -> Optional[Iterable[str]]:
    url, selector, additional_headers = args
    headers = NETWORK_CONFIG["HEADER"]
    if additional_headers is not None:
        headers.update(additional_headers)

    verbose_output = OUTPUT_CONFIG["VERBOSE"]
    error_output = OUTPUT_CONFIG["PRINT_ERROR"]
    if verbose_output:
        printInfo(f"collecting {url}")
    time.sleep(DOWNLOAD_CONFIG["THREAD_DELAY"])

    for i in range(DOWNLOAD_CONFIG["N_TIMES"]):
        try:
            response = requests.get(
                url, headers=headers,
                proxies=NETWORK_CONFIG["PROXY"],
                timeout=4)

            if response.status_code == 200:
                id_group = selector(response)
                if verbose_output:
                    printInfo(f"{url} complete")
                return id_group

        except Exception as e:
            printWarn(error_output, e)
            printWarn(error_output,
                      f"This is {i} attempt to collect {url}")

            time.sleep(DOWNLOAD_CONFIG["FAIL_DELAY"])

    printWarn(error_output, f"fail to collect {url}")
    writeFailLog(f"fail to collect {url} \n")

class Collector():

    def __init__(self, downloader: Downloader):
        self.id_group: Set[str] = set()  # illust_id
        self.downloader = downloader

    def add(self, image_ids: Iterable[str]):
        for image_id in image_ids:
            self.id_group.add(image_id)

    def collectTags(self):
        printInfo("===== tag collector start =====")

        self.tags: Dict[str, List] = dict()
        n_thread = DOWNLOAD_CONFIG["N_THREAD"]
        with futures.ThreadPoolExecutor(n_thread) as executor:
            with tqdm(total=len(self.id_group), desc="collecting tags") as pbar:
                urls = [f"https://www.pixiv.net/artworks/{illust_id}"
                        for illust_id in self.id_group]
                additional_headers = {
                    "Referer": "https://www.pixiv.net/bookmark.php?type=user"}
                for illust_id, tags in zip(
                        self.id_group, executor.map(collect, zip(
                            urls, [selectTag] * len(urls),
                            [additional_headers] * len(urls)))):
                    if tags is not None:
                        self.tags[illust_id] = tags
                    pbar.update()

        file_path = DOWNLOAD_CONFIG["STORE_PATH"] + "tags.json"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.tags, indent=4, ensure_ascii=False))

        printInfo("===== tag collector complete =====")

    def collect(self):
        if DOWNLOAD_CONFIG["WITH_TAG"]:
            self.collectTags()

        printInfo("===== collector start =====")

        n_thread = DOWNLOAD_CONFIG["N_THREAD"]
        with futures.ThreadPoolExecutor(n_thread) as executor:
            with tqdm(total=len(self.id_group), desc="collecting urls") as pbar:
                urls = [f"https://www.pixiv.net/ajax/illust/{illust_id}/pages?lang=zh"
                        for illust_id in self.id_group]
                additional_headers = [
                    {
                        "Referer": f"https://www.pixiv.net/artworks/{illust_id}",
                        "x-user-id": USER_CONFIG["USER_ID"]
                    }
                    for illust_id in self.id_group]
                for urls in executor.map(collect, zip(
                        urls, [selectPage] * len(urls), additional_headers)):
                    if urls is not None:
                        self.downloader.add(urls)
                    pbar.update()

        printInfo("===== collector complete =====")
        printInfo(f"total images: {len(self.downloader.url_group)}")

def selectTag(response: Response) -> List[str]:
    result = re.search("artworks/(\d+)", response.url)
    printError(result is None, "bad response in selectTag")
    illust_id = result.group(1)
    content = json.loads(
        PyQuery(response.text).find(
            "#meta-preload-data").attr("content"))
    return [
        tag["translation"]["en"] if "translation" in tag else tag["tag"]
        for tag in content["illust"][illust_id]["tags"]["tags"]
    ]

def selectPage(response: Response) -> Set[str]:
    group = set()
    for url in response.json()["body"]:
        group.add(url["urls"]["original"])
    return group

def selectUser(response: Response) -> Set[str]:
    return set(response.json()["body"]["illusts"].keys())

def selectBookmark(response: Response) -> Set[str]:
    id_group: Set[str] = set()
    for artwork in response.json()["body"]["works"]:
        illust_id = artwork["id"]
        if isinstance(illust_id, str):
            id_group.add(artwork["id"])
        else:
            writeFailLog(f"disable artwork {illust_id} \n")
    return id_group

def selectKeyword(response: Response) -> Set[str]:
    id_group: Set[str] = set()
    for artwork in response.json()[
            "body"]["illustManga"]["data"]:
        id_group.add(artwork["id"])
    return id_group
    

class BookmarkCrawler():
    def __init__(self, n_images=200, capacity=1024):
        self.n_images = n_images
        self.uid = USER_CONFIG["USER_ID"]
        self.url = f"https://www.pixiv.net/ajax/user/{self.uid}/illusts"

        self.downloader = Downloader(capacity)
        self.collector = Collector(self.downloader)

    def __requestCount(self):
        url = self.url + "/bookmark/tags?lang=zh"
        printInfo("===== requesting bookmark count =====")

        headers = {"COOKIE": USER_CONFIG["COOKIE"]}
        headers.update(NETWORK_CONFIG["HEADER"])
        error_output = OUTPUT_CONFIG["PRINT_ERROR"]
        for i in range(DOWNLOAD_CONFIG["N_TIMES"]):
            try:
                response = requests.get(
                    url, headers=headers,
                    proxies=NETWORK_CONFIG["PROXY"],
                    timeout=4)

                if response.status_code == 200:
                    n_total = int(response.json()["body"]["public"][0]["cnt"])
                    self.n_images = min(self.n_images, n_total)
                    printInfo(f"select {self.n_images}/{n_total} artworks")
                    printInfo("===== request bookmark count complete =====")
                    return

            except Exception as e:
                printWarn(error_output, e)
                printWarn(error_output,
                          f"This is {i} attempt to request bookmark count")

                time.sleep(DOWNLOAD_CONFIG["FAIL_DELAY"])

        printWarn(True, "check COOKIE config")
        printError(True, "===== fail to get bookmark count =====")

    def collect(self):
        ARTWORK_PER = 48
        n_page = (self.n_images - 1) // ARTWORK_PER + 1  # ceil
        printInfo(f"===== start collecting {self.uid}'s bookmarks =====")

        urls: Set[str] = set()
        for i in range(n_page):
            urls.add(self.url + "/bookmarks?tag=&" +
                     f"offset={i * ARTWORK_PER}&limit={ARTWORK_PER}&rest=show&lang=zh")

        n_thread = DOWNLOAD_CONFIG["N_THREAD"]
        with futures.ThreadPoolExecutor(n_thread) as executor:
            with tqdm(total=len(urls), desc="collecting ids") as pbar:
                additional_headers = {"COOKIE": USER_CONFIG["COOKIE"]}
                for image_ids in executor.map(collect, zip(
                        urls, [selectBookmark] * len(urls),
                        [additional_headers] * len(urls))):
                    if image_ids is not None:
                        self.collector.add(image_ids)
                    pbar.update()

        printInfo("===== collect bookmark complete =====")
        printInfo(f"downloadable artworks: {len(self.collector.id_group)}")

    def run(self):
        self.__requestCount()
        self.collect()
        self.collector.collect()
        return self.downloader.download()


class UserCrawler():
    def __init__(self, artist_id, capacity=1024):
        self.artist_id = artist_id

        self.downloader = Downloader(capacity)
        self.collector = Collector(self.downloader)

    def collect(self):
        url = f"https://www.pixiv.net/ajax/user/{self.artist_id}/profile/all?lang=zh"
        additional_headers = {
            "Referer": f"https://www.pixiv.net/users/{self.artist_id}/illustrations",
            "x-user-id": USER_CONFIG["USER_ID"],
            "COOKIE": USER_CONFIG["COOKIE"]
        }
        image_ids = collect(
            (url, selectUser, additional_headers))
        if image_ids is not None:
            self.collector.add(image_ids)
        printInfo(f"===== collect user {self.artist_id} complete =====")

    def run(self):
        self.collect()
        self.collector.collect()
        return self.downloader.download()
    

class KeywordCrawler():
    def __init__(self, keyword: str,
                 order: bool = False, mode: str = "safe",
                 n_images=200, capacity=1024):
        assert mode in ["safe", "r18", "all"]

        self.keyword = keyword
        self.order = order
        self.mode = mode

        self.n_images = n_images

        self.downloader = Downloader(capacity)
        self.collector = Collector(self.downloader)

    def collect(self):
        ARTWORK_PER = 60
        n_page = (self.n_images - 1) // ARTWORK_PER + 1  # ceil
        printInfo(f"===== start collecting {self.keyword} =====")

        urls: Set[str] = set()
        url = "https://www.pixiv.net/ajax/search/artworks/" + \
            "{}?word={}".format(urlparse.quote(self.keyword, safe="()"), urlparse.quote(self.keyword)) + \
            "&order={}".format("popular_d" if self.order else "date_d") + \
            f"&mode={self.mode}" + "&p={}&s_mode=s_tag&type=all&lang=zh"
        for i in range(n_page):
            urls.add(url.format(i + 1))

        n_thread = DOWNLOAD_CONFIG["N_THREAD"]
        with futures.ThreadPoolExecutor(n_thread) as executor:
            with tqdm(total=len(urls), desc="collecting ids") as pbar:
                additional_headers = {"COOKIE": USER_CONFIG["COOKIE"]}
                for image_ids in executor.map(collect, zip(
                        urls, [selectKeyword] * len(urls),
                        [additional_headers] * len(urls))):
                    if image_ids is not None:
                        self.collector.add(image_ids)
                    pbar.update()

        printInfo(f"===== collect {self.keyword} complete =====")
        printInfo(f"downloadable artworks: {len(self.collector.id_group)}")

    def run(self):
        self.collect()
        self.collector.collect()
        return self.downloader.download()
