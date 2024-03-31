import time
from functools import lru_cache
from PIL import Image
import torch
import clip
import utils

class CLIPModel:
    def __init__(self, config):
        """
        Initialize the CLIPModel class.

        Args:
            config (dict): Configuration dictionary.
        """
        self.config = config
        if self.config.get('device') == 'cuda' and not torch.cuda.is_available():
            self.device = 'cpu'
        else:
            self.device = self.config.get('device', 'cuda' if torch.cuda.is_available() else 'cpu')
        self.model, self.preprocess = self.get_model()

    def get_model(self):
        """
        Load the CLIP model and return the model and preprocess function.

        Returns:
            tuple: Containing the CLIP model and preprocess function.
        """
        args = {}
        if 'clip-model-download' in self.config:
            args['download_root'] = self.config['clip-model-download']
        return clip.load(self.config['clip-model'], device=self.device, **args)

    def get_image_feature(self, image_path):
        """
        Get the image feature vector.

        Args:
            image_path (str): Path to the image.

        Returns:
            tuple: Containing the image feature vector and image size, or None if the image failed to load.
        """
        try:
            image = Image.open(image_path)
            image_size = image.size
            image = self.preprocess(image).unsqueeze(0).to(self.device)
        except:
            return None, None  # Failed to load image

        with torch.no_grad():
            feat = self.model.encode_image(image)
            feat = feat.detach().cpu().numpy()
        return feat, image_size

    def get_text_feature(self, text: str):
        """
        Get the text feature vector.

        Args:
            text (str): Input text.

        Returns:
            numpy.ndarray: Text feature vector.
        """
        text = clip.tokenize([text]).to(self.device)
        feat = self.model.encode_text(text)
        return feat.detach().cpu().numpy()

@lru_cache(maxsize=1)
def get_model() -> CLIPModel:
    """
    Get the CLIPModel instance, using LRU cache.

    Returns:
        CLIPModel: CLIPModel instance.
    """
    config = utils.get_config()
    _time_start = time.time()
    model = CLIPModel(config)
    _time_end = time.time()
    print(f"[DEBUG] CLIP model loaded in {_time_end - _time_start:.3f} seconds")
    return model

if __name__ == "__main__":
    model = get_model()
    print(model.model)