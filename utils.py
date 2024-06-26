import os
import subprocess

import yaml
import hashlib
from functools import lru_cache
import pymongo
from pymongo.collection import Collection
import clip


@lru_cache(maxsize=1)
def get_config() -> dict:
    """
    Load configuration from 'config.yaml' file and validate certain fields.

    Returns:
    - dict: Configuration dictionary.
    """
    with open('config.yaml') as yaml_data_file:
        config = yaml.safe_load(yaml_data_file)

    if "clip-model" in config:
        assert config["clip-model"] in clip.available_models()
    if "device" in config:
        assert config["device"] in ["cuda", "cpu"]
    return config


def get_feature_size(model_name: str) -> int:
    """
    Get the feature size for a given model.

    Args:
    - model_name (str): Name of the CLIP model.

    Returns:
    - int: Feature size for the model.
    
    Raises:
    - ValueError: If the model name is unknown.
    """
    if model_name == "ViT-B/32":
        return 512
    elif model_name == "ViT-L/14":
        return 768
    else:
        raise ValueError("Unknown model")


def get_file_type(image_path: str) -> str:
    """
    Get the file type of an image using the 'file' command.

    Args:
    - image_path (str): Path to the image file.

    Returns:
    - str: File type (e.g., 'png', 'jpg', 'gif', 'bmp') or None if it cannot be determined.
    """
    try:
        result = subprocess.run(["file", "--mime-type", "-b", image_path], capture_output=True, text=True,
                                encoding='utf-8')
        libmagic_output = result.stdout.strip()
    except Exception as e:
        print(f"Error executing file command: {e}")
        return None

    if "png" in libmagic_output:
        return "png"
    if "jpeg" in libmagic_output:
        return "jpg"
    if "gif" in libmagic_output:
        return "gif"
    if "bmp" in libmagic_output:
        return "bmp"
    return None


@lru_cache(maxsize=1)
def get_mongo_collection(isRemote=False) -> Collection:
    """
    Get MongoDB collection based on configuration settings.

    Returns:
    - Collection: MongoDB collection.
    """
    config = get_config()
    mongo_client = pymongo.MongoClient("mongodb://{}:{}/".format(config['mongodb-host'], config['mongodb-port']))
    if isRemote:
        mongo_collection = mongo_client[config['mongodb-database']][config['mongodb-collection-remote']]
    else:
        mongo_collection = mongo_client[config['mongodb-database']][config['mongodb-collection']]
    return mongo_collection


def calc_md5(filepath: str) -> str:
    """
    Calculate MD5 hash of a file.

    Args:
    - filepath (str): Path to the file.

    Returns:
    - str: MD5 hash of the file.
    """
    with open(filepath, 'rb') as f:
        md5 = hashlib.md5()
        while True:
            data = f.read(4096)
            if not data:
                break
            md5.update(data)
        return md5.hexdigest()


def get_full_path(basedir: str, basename: str) -> str:
    """
    Generate full file path based on directory structure.

    Args:
    - basedir (str): Base directory.
    - basename (str): Base name of the file.

    Returns:
    - str: Full file path.
    """
    md5hash, ext = basename.split(".")
    return "{}/{}/{}/{}".format(basedir, ext, md5hash[:2], basename)