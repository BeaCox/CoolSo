import os
from glob import glob
from datetime import datetime
from pymongo.collection import Collection
from tqdm import tqdm
import clip_model
import ocr_model
import utils


def import_single_image(filename: str, clip: clip_model.CLIPModel, ocr: ocr_model.OCRModel,
                        config: dict, mongo_collection: Collection) -> None:
    """
    Import a single image file, extract features using CLIP model, perform OCR, and store the information in MongoDB.

    Args:
    - filename (str): Path to the image file.
    - clip (clip_model.CLIPModel): Instance of the CLIP model.
    - ocr (ocr_model.OCRModel): Instance of the OCR model.
    - config (dict): Configuration dictionary.
    - mongo_collection (Collection): MongoDB collection to store the image information.

    Returns:
    - None
    """
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
    print("OCR Text:", ocr_text)

    stat = os.stat(filename)
    new_full_path = filename

    image_mtime = datetime.fromtimestamp(stat.st_mtime)
    image_datestr = image_mtime.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    # Save to MongoDB
    document = {
        'filename': new_full_path,
        'extension': filetype,
        'height': image_size[1],
        'width': image_size[0],
        'filesize': stat.st_size,
        'date': image_datestr,
        'feature': image_feature.tobytes(),
        'ocr_text': ocr_text
    }

    mongo_collection.insert_one(document)


def import_dirs(base_dirs: list, clip: clip_model.CLIPModel, ocr: ocr_model.OCRModel,
                config: dict, mongo_collection: Collection) -> None:
    """
    Import all image files from multiple directories recursively.

    Args:
    - base_dirs (list): List of paths to the base directories.
    - clip (clip_model.CLIPModel): Instance of the CLIP model.
    - ocr (ocr_model.OCRModel): Instance of the OCR model.
    - config (dict): Configuration dictionary.
    - mongo_collection (Collection): MongoDB collection to store the image information.

    Returns:
    - None
    """
    for base_dir in base_dirs:
        filelist = glob(os.path.join(base_dir, '**/*'), recursive=True)
        filelist = [f for f in filelist if os.path.isfile(f)]

        for filename in tqdm(filelist):
            import_single_image(filename, clip, ocr, config, mongo_collection)



