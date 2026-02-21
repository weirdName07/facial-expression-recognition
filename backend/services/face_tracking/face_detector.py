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
    
    # YOLO prediction (running without .track to avoid 'lap' dependency)
    results = _model.predict(frame, verbose=False, conf=conf_threshold)

    detected_faces = []
    for r in results:
        boxes = r.boxes
        if boxes is None:
            continue
            
        for box in boxes:
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()
            
            # Centroid
            cx, cy = (x1 + x2) / 2, (y1 + y2) / 2
            
            detected_faces.append({
                "bbox_raw": [x1, y1, x2, y2],
                "centroid": (cx, cy),
                "conf": conf
            })

    # ── Simple Centroid Tracker ──
    global _next_id, _id_centroids
    if '_next_id' not in globals():
        _next_id = 1
        _id_centroids = {} # {id: (cx, cy)}

    new_id_centroids = {}
    final_faces = []

    for face in detected_faces:
        cx, cy = face["centroid"]
        
        # Find best match in id_centroids
        best_id = None
        min_dist = 50.0 # Pixel threshold
        
        for fid, old_center in _id_centroids.items():
            dist = np.sqrt((cx - old_center[0])**2 + (cy - old_center[1])**2)
            if dist < min_dist:
                min_dist = dist
                best_id = fid
        
        if best_id is None:
            best_id = _next_id
            _next_id += 1
        
        new_id_centroids[best_id] = (cx, cy)
        
        # Prepare final dict
        x1, y1, x2, y2 = face["bbox_raw"]
        x_min, y_min = max(0.0, x1/w), max(0.0, y1/h)
        x_max, y_max = min(1.0, x2/w), min(1.0, y2/h)

        # Margin
        margin = 0.05
        mw, mh = x_max - x_min, y_max - y_min
        x_min, y_min = max(0.0, x_min - mw*margin), max(0.0, y_min - mh*margin)
        x_max, y_max = min(1.0, x_max + mw*margin), min(1.0, y_max + mh*margin)

        px1, py1 = int(x_min * w), int(y_min * h)
        px2, py2 = int(x_max * w), int(y_max * h)
        crop = frame[py1:py2, px1:px2]
        
        if crop.size > 0:
            final_faces.append({
                "face_id": f"face_{best_id}",
                "bbox": {"x_min": x_min, "y_min": y_min, "x_max": x_max, "y_max": y_max},
                "confidence": face["conf"],
                "crop": crop
            })

    _id_centroids = new_id_centroids
    return final_faces
