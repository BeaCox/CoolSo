import os
from typing import List

import numpy as np
import torch
from PIL import Image
import utils
from clip_model import get_model
from fuzzywuzzy import fuzz


def cosine_similarity(query_feature, feature_list):
    query_feature = query_feature / np.linalg.norm(query_feature, axis=1, keepdims=True)
    feature_list = feature_list / np.linalg.norm(feature_list, axis=1, keepdims=True)
    sim_score = (query_feature @ feature_list.T)

    return sim_score[0]


class SearchService:
    def __init__(self, isRemote=False):
        self.config = utils.get_config()
        self.device = self.config['device']
        self.feat_dim = utils.get_feature_size(self.config['clip-model'])

        self.model = get_model()
        self.mongo_collection = utils.get_mongo_collection(isRemote)
        self._MAX_SPLIT_SIZE = 8192

    def search_nearest_clip_feature(self, query_feature, topn=20):
        cursor = self.mongo_collection.find({}, {"_id": 0, "filename": 1, "feature": 1})

        filename_list = []
        feature_list = []
        sim_score_list = []
        for doc in cursor:
            feature_list.append(np.frombuffer(doc["feature"], self.config["storage-type"]))
            filename_list.append(doc["filename"])

            if len(feature_list) >= self._MAX_SPLIT_SIZE:
                feature_list = np.array(feature_list)
                sim_score_list.append(cosine_similarity(query_feature, feature_list))
                feature_list = []

        if len(feature_list) > 0:
            feature_list = np.array(feature_list)
            sim_score_list.append(cosine_similarity(query_feature, feature_list))

        if len(sim_score_list) == 0:
            return [], []

        sim_score = np.concatenate(sim_score_list, axis=0)

        top_n_idx = np.argsort(sim_score)[::-1][:topn]
        top_n_filename = [filename_list[idx] for idx in top_n_idx]
        top_n_score = [float(sim_score[idx]) for idx in top_n_idx]

        return top_n_filename, top_n_score

    def search_ocr_text(self, query_text, topn=20):
        # fuzzy search
        cursor = self.mongo_collection.find({}, {"_id": 0, "filename": 1, "ocr_text": 1})

        filename_list = []
        ocr_text_list = []
        for doc in cursor:
            filename_list.append(doc["filename"])
            ocr_text_list.append(doc["ocr_text"])

        # use fuzzywuzzy to calculate similarity score
        score_list = [fuzz.partial_ratio(query_text, ocr_text) for ocr_text in ocr_text_list]

        sorted_indices = sorted(range(len(score_list)), key=lambda k: score_list[k], reverse=True)
        sorted_filename = [filename_list[i] for i in sorted_indices[:topn]]
        sorted_scores = [score_list[i] for i in sorted_indices[:topn]]

        return sorted_filename, sorted_scores

    def convert_result(self, filename_list: List[str], score_list: List[float]):
        doc_result = self.mongo_collection.find(
            {"filename": {"$in": filename_list}},
            {"_id": 0, "filename": 1, "width": 1, "height": 1, "filesize": 1, "date": 1, "ocr_text": 1})
        doc_result = list(doc_result)
        print(doc_result)
        filename_to_doc_dict = {d['filename']: d for d in doc_result}
        ret_list = []
        for filename, score in zip(filename_list, score_list):
            doc = filename_to_doc_dict[filename]

            s = ""
            s += "Score = {:.5f}\n".format(score)
            s += (os.path.basename(filename) + "\n")
            s += "{}x{}, filesize={}, {}\n".format(
                doc['width'], doc['height'],
                doc['filesize'], doc['date']
            )
            s += f"OCR Text: {doc['ocr_text']}\n"

            ret_list.append((filename, s))
        return ret_list

    def search_image(self, query, topn):
        with torch.no_grad():
            if isinstance(query, str):
                target_feature = self.model.get_text_feature(query)
            elif isinstance(query, Image.Image):
                image_input = self.model.preprocess(query).unsqueeze(0).to(self.model.device)
                image_feature = self.model.model.encode_image(image_input)
                target_feature = image_feature.cpu().detach().numpy()
            else:
                assert False, "Invalid query (input) type"

        filename_list, score_list = self.search_nearest_clip_feature(target_feature, topn=int(topn))
        return self.convert_result(filename_list, score_list)

    def search_ocr(self, query_text, topn):
        filename_list, score_list = self.search_ocr_text(query_text, topn=int(topn), )
        return self.convert_result(filename_list, score_list)
