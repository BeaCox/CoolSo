import os
import shutil
from glob import glob
from datetime import datetime
from pymongo.collection import Collection
from tqdm import tqdm
import clip_model
import ocr_model
import utils


def import_single_image(filename: str, clip: clip_model.CLIPModel, ocr: ocr_model.OCRModel,
                        config: dict, mongo_collection: Collection, copy: bool = False) -> None:
    """
    Import a single image file, extract features using CLIP model, perform OCR, and store the information in MongoDB.

    Args:
    - filename (str): Path to the image file.
    - clip (clip_model.CLIPModel): Instance of the CLIP model.
    - ocr (ocr_model.OCRModel): Instance of the OCR model.
    - config (dict): Configuration dictionary.
    - mongo_collection (Collection): MongoDB collection to store the image information.
    - copy (bool): Whether to copy the image file to another directory. Default is False.

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

    if copy:
        md5hash = utils.calc_md5(filename)
        new_basename = md5hash + '.' + filetype
        new_full_path = utils.get_full_path(config['import-image-base'], new_basename)

        if os.path.isfile(new_full_path):
            print("Duplicate file:", filename)
            return

        shutil.copy2(filename, new_full_path)
        stat = os.stat(new_full_path)
    else:
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


def import_dir(base_dir: str, clip: clip_model.CLIPModel, ocr: ocr_model.OCRModel,
               config: dict, mongo_collection: Collection, copy: bool = False) -> None:
    """
    Import all image files from a directory recursively.

    Args:
    - base_dir (str): Path to the base directory.
    - clip (clip_model.CLIPModel): Instance of the CLIP model.
    - ocr (ocr_model.OCRModel): Instance of the OCR model.
    - config (dict): Configuration dictionary.
    - mongo_collection (Collection): MongoDB collection to store the image information.
    - copy (bool): Whether to copy the image files to another directory. Default is False.

    Returns:
    - None
    """
    filelist = glob(os.path.join(base_dir, '**/*'), recursive=True)
    filelist = [f for f in filelist if os.path.isfile(f)]

    for filename in tqdm(filelist):
        import_single_image(filename, clip, ocr, config, mongo_collection, copy=copy)


def main():
    """
    Main function to run the image import process.
    """
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--copy', action='store_true', help='Copy imported images to another directory')
    parser.add_argument('dir', help='Directory containing images to import')
    args = parser.parse_args()

    config = utils.get_config()
    mongo_collection = utils.get_mongo_collection()
    clip = clip_model.get_model()
    ocr = ocr_model.get_ocr_model()
    import_dir(args.dir, clip, ocr, config, mongo_collection, copy=args.copy)


if __name__ == '__main__':
    main()
