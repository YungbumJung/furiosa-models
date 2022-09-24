import json
import os
from pathlib import Path
from typing import List

import numpy as np
from pycocotools.coco import COCO
from pycocotools.cocoeval import COCOeval
import tqdm

from furiosa.models.vision import SSDResNet34
from furiosa.models.vision.postprocess import ObjectDetectionResult
from furiosa.models.vision.ssd_resnet34 import NativePostProcessor, postprocess, preprocess
from furiosa.registry import Model
from furiosa.runtime import session

EXPECTED_ACCURACY = 0.21321479317934577  # e2e-testing's accuracy
EXPECTED_ACCURACY_RUST = 0.22013336390711905
EXPECTED_ACCURACY_CPP = 0.22013360530400045


def load_coco_from_env_variable():
    coco_val_images = os.environ.get('COCO_VAL_IMAGES')
    coco_val_labels = os.environ.get('COCO_VAL_LABELS')

    if coco_val_images is None or coco_val_labels is None:
        raise Exception("Environment variables not set")

    coco = COCO(coco_val_labels)

    return Path(coco_val_images), coco


def test_mlcommons_ssd_resnet34_accuracy():
    model: Model = SSDResNet34()

    image_directory, coco = load_coco_from_env_variable()
    detections = []
    instances_val2017 = Path(os.environ.get('COCO_VAL_LABELS'))
    with open(instances_val2017, encoding="ascii") as file:
        annotations = json.load(file)
    label_to_category = {
        label: category["id"] for label, category in enumerate(annotations["categories"], 1)
    }

    with session.create(model.enf) as sess:
        for image_src in tqdm.tqdm(coco.dataset["images"]):
            image_path = str(image_directory / image_src["file_name"])
            image, contexts = preprocess([image_path])
            outputs = sess.run(image).numpy()
            batch_result = postprocess(outputs, contexts, confidence_threshold=0.05)
            result = np.squeeze(batch_result, axis=0)  # squeeze the batch axis

            for res in result:
                detection = {
                    "image_id": image_src["id"],
                    "category_id": label_to_category[res.index],
                    "bbox": [
                        res.boundingbox.left,
                        res.boundingbox.top,
                        (res.boundingbox.right - res.boundingbox.left),
                        (res.boundingbox.bottom - res.boundingbox.top),
                    ],
                    "score": res.score,
                }
                detections.append(detection)
    coco_detections = coco.loadRes(detections)
    coco_eval = COCOeval(coco, coco_detections, iouType="bbox")
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    print("mAP:", coco_eval.stats[0])
    assert coco_eval.stats[0] == EXPECTED_ACCURACY, "Accuracy check failed"


def test_mlcommons_ssd_resnet34_with_native_rust_pp_accuracy():
    model = SSDResNet34(use_native_post=True)
    processor = NativePostProcessor(model, version="rust")

    image_directory, coco = load_coco_from_env_variable()
    detections = []
    instances_val2017 = Path(os.environ.get('COCO_VAL_LABELS'))
    with open(instances_val2017, encoding="ascii") as file:
        annotations = json.load(file)
    label_to_category = {
        label: category["id"] for label, category in enumerate(annotations["categories"], 1)
    }

    with session.create(model.enf) as sess:
        for image_src in tqdm.tqdm(coco.dataset["images"]):
            image_path = str(image_directory / image_src["file_name"])
            image, contexts = preprocess([image_path])
            outputs = sess.run(image).numpy()
            result = processor.eval(outputs, context=contexts[0])

            for res in result:
                detection = {
                    "image_id": image_src["id"],
                    "category_id": label_to_category[res.index],
                    "bbox": [
                        res.boundingbox.left,
                        res.boundingbox.top,
                        (res.boundingbox.right - res.boundingbox.left),
                        (res.boundingbox.bottom - res.boundingbox.top),
                    ],
                    "score": res.score,
                }
                detections.append(detection)
    coco_detections = coco.loadRes(detections)
    coco_eval = COCOeval(coco, coco_detections, iouType="bbox")
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    print("mAP:", coco_eval.stats[0])
    assert coco_eval.stats[0] == EXPECTED_ACCURACY_RUST, "Accuracy check failed"


def test_mlcommons_ssd_resnet34_with_native_cpp_pp_accuracy():
    model = SSDResNet34(use_native_post=True)
    processor = NativePostProcessor(model, version="cpp")

    image_directory, coco = load_coco_from_env_variable()
    detections = []
    instances_val2017 = Path(os.environ.get('COCO_VAL_LABELS'))
    with open(instances_val2017, encoding="ascii") as file:
        annotations = json.load(file)
    label_to_category = {
        label: category["id"] for label, category in enumerate(annotations["categories"], 1)
    }

    with session.create(model.enf) as sess:
        for image_src in tqdm.tqdm(coco.dataset["images"]):
            image_path = str(image_directory / image_src["file_name"])
            image, contexts = preprocess([image_path])
            outputs = sess.run(image).numpy()
            result = processor.eval(outputs, context=contexts[0])

            for res in result:
                detection = {
                    "image_id": image_src["id"],
                    "category_id": label_to_category[res.index],
                    "bbox": [
                        res.boundingbox.left,
                        res.boundingbox.top,
                        (res.boundingbox.right - res.boundingbox.left),
                        (res.boundingbox.bottom - res.boundingbox.top),
                    ],
                    "score": res.score,
                }
                detections.append(detection)
    coco_detections = coco.loadRes(detections)
    coco_eval = COCOeval(coco, coco_detections, iouType="bbox")
    coco_eval.evaluate()
    coco_eval.accumulate()
    coco_eval.summarize()
    print("mAP:", coco_eval.stats[0])
    assert coco_eval.stats[0] == EXPECTED_ACCURACY_CPP, "Accuracy check failed"
