"""
YOLO Face Detector — robust face tracking for real-time analysis.

Uses a specialized YOLO-Face model downloaded from HuggingFace.
This avoids picking up background objects like posters, which happened
when using the general YOLO "person" class.
"""

import logging
import cv2
import numpy as np
from pathlib import Path
from typing import List, Dict, Any
import urllib.request
import os

log = logging.getLogger(__name__)

# Global YOLO instance
_model = None

def load_model():
    """
    Load the YOLO face detection model.
    Downloads the model if it doesn't exist locally.
    """
    global _model
    from ultralytics import YOLO

    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(exist_ok=True)

    face_model_path = models_dir / "yolov8n-face.pt"
    
    # Download specialized face model if not present
    if not face_model_path.exists():
        log.info(f"Downloading YOLO face model to {face_model_path}...")
        url = "https://huggingface.co/arnabdhar/YOLOv8-Face-Detection/resolve/main/model.pt"
        try:
            urllib.request.urlretrieve(url, str(face_model_path))
            log.info("Download complete.")
        except Exception as e:
            log.error(f"Failed to download face model: {e}")
            raise RuntimeError("Cannot start without face model.")

    log.info(f"Loading YOLO face model: {face_model_path}")
    _model = YOLO(str(face_model_path))
    log.info("YOLO face model loaded successfully")


def detect_faces(frame: np.ndarray, conf_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Run YOLO face detection on a BGR frame.

    Returns list of dicts:
      [{
        "face_id": str,
        "bbox": {"x_min": float, "y_min": float, "x_max": float, "y_max": float},
        "confidence": float,
        "crop": np.ndarray  # BGR face crop
      }]
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    h, w = frame.shape[:2]
    
    # YOLO inference
    results = _model(frame, verbose=False, conf=conf_threshold)

    faces = []
    for r in results:
        boxes = r.boxes
        for i, box in enumerate(boxes):
            # This is a dedicated face model, so we don't need to filter by class
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            # Normalised coords
            x_min = max(0.0, x1 / w)
            y_min = max(0.0, y1 / h)
            x_max = min(1.0, x2 / w)
            y_max = min(1.0, y2 / h)

            # Optional: Add a small margin for better emotion classification
            margin = 0.05
            mw = x_max - x_min
            mh = y_max - y_min
            x_min = max(0.0, x_min - mw * margin)
            y_min = max(0.0, y_min - mh * margin)
            x_max = min(1.0, x_max + mw * margin)
            y_max = min(1.0, y_max + mh * margin)

            # Pixel coords for cropping
            px1, py1 = int(max(0, x_min * w)), int(max(0, y_min * h))
            px2, py2 = int(min(w, x_max * w)), int(min(h, y_max * h))
            
            crop = frame[py1:py2, px1:px2]
            if crop.size == 0:
                continue

            faces.append({
                "face_id": f"face_{i + 1}",
                "bbox": {
                    "x_min": round(float(x_min), 4),
                    "y_min": round(float(y_min), 4),
                    "x_max": round(float(x_max), 4),
                    "y_max": round(float(y_max), 4),
                },
                "confidence": round(float(conf), 3),
                "crop": crop,
            })

    return faces
