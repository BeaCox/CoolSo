import os
from functools import lru_cache
from paddleocr import PaddleOCR

import utils

def download_ocr_model(config):
    """
    Function to download OCR models if not already downloaded.

    Args:
    - config (dict): Configuration dictionary containing paths and model names.
    """
    download_path = config["ocr-model-download"]
    download_link_dict = {
        "ch_PP-OCRv4_det_infer": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_det_infer.tar",
        "ch_PP-OCRv4_rec_infer": "https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/ch_PP-OCRv4_rec_infer.tar",
    }
    det_model = config["ocr-det-model"]
    rec_model = config["ocr-rec-model"]
    for model_name in [det_model, rec_model]:
        if not os.path.exists(os.path.join(download_path, model_name)):
            print("Downloading", model_name)
            os.system(f"wget {download_link_dict[model_name]} -P {download_path}")
            os.system(f"tar -xf {os.path.join(download_path, model_name)}.tar -C {download_path}")
            os.system(f"rm {os.path.join(download_path, model_name)}.tar")


class OCRModel:
    def __init__(self, config):
        """
        Initializes the OCR model.

        Args:
        - config (dict): Configuration dictionary containing model paths and settings.
        """
        download_ocr_model(config)

        self.config = config
        self.model = PaddleOCR(
            ocr_version="PP-OCRv4",
            det_model_dir="{}/{}".format(config['ocr-model-download'], config['ocr-det-model']),
            rec_model_dir="{}/{}".format(config['ocr-model-download'], config['ocr-rec-model']),
            use_gpu=(config["device"] == "cuda"),
        )

    def get_ocr_text(self, image_path: str) -> str:
        """
        Performs OCR on the given image and returns the extracted text.

        Args:
        - image_path (str): Path to the input image.

        Returns:
        - str: Extracted text from the image.
        """
        try:
            ocr_result = self.model.ocr(img=image_path, cls=False)
        except Exception as e:
            print(f"Error processing {image_path}: {e}")
            return None

        if not ocr_result:
            return None

        ocr_text = ""
        for line in ocr_result:
            if line is None:
                continue

            for text_info in line:
                ocr_text += text_info[1][0] + " "

        return ocr_text.strip()

@lru_cache(maxsize=1)
def get_ocr_model():
    """
    Returns an instance of the OCR model, caching the result.

    Returns:
    - OCRModel: Instance of the OCR model.
    """
    config = utils.get_config()
    return OCRModel(config)


if __name__ == "__main__":
    model = get_ocr_model()
