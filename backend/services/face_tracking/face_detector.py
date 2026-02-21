"""
YOLOv11 Face Detector — uses ultralytics YOLO for real-time face detection.

Attempts to load a face-specific YOLOv11 model first, falls back to
general object detection (person class) if unavailable.
"""

import logging
import numpy as np
from pathlib import Path
from typing import List, Dict, Any

log = logging.getLogger(__name__)

# Will be assigned after model loads
_model = None
_face_specific = False


def load_model():
    """
    Load the YOLO face detection model.
    Priority:
      1. yolo11n-face.pt (community face model)
      2. yolo11n.pt (general COCO — filter for 'person' class)
    """
    global _model, _face_specific
    from ultralytics import YOLO

    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(exist_ok=True)

    face_model_path = models_dir / "yolo11n-face.pt"

    if face_model_path.exists():
        log.info(f"Loading face-specific YOLO model: {face_model_path}")
        _model = YOLO(str(face_model_path))
        _face_specific = True
    else:
        log.info("Face model not found, using general yolo11n.pt (person detection)")
        _model = YOLO("yolo11n.pt")  # auto-downloads from ultralytics hub
        _face_specific = False

    log.info("YOLO model loaded successfully")


def detect_faces(frame: np.ndarray, conf_threshold: float = 0.4) -> List[Dict[str, Any]]:
    """
    Run face detection on a BGR frame.

    Returns list of dicts:
      [{
        "face_id": str,
        "bbox": {"x_min": float, "y_min": float, "x_max": float, "y_max": float},
        "confidence": float,
        "crop": np.ndarray  # BGR face crop
      }]

    Bounding boxes are normalised to [0, 1].
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    h, w = frame.shape[:2]

    results = _model(frame, verbose=False, conf=conf_threshold)

    faces = []
    for r in results:
        boxes = r.boxes
        for i, box in enumerate(boxes):
            cls_id = int(box.cls[0])

            # If using general model, only keep 'person' class (id 0)
            if not _face_specific and cls_id != 0:
                continue

            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].cpu().numpy()

            # Normalise to 0-1
            x_min = max(0.0, x1 / w)
            y_min = max(0.0, y1 / h)
            x_max = min(1.0, x2 / w)
            y_max = min(1.0, y2 / h)

            # Crop the face region (in pixel coords)
            px1, py1 = int(max(0, x1)), int(max(0, y1))
            px2, py2 = int(min(w, x2)), int(min(h, y2))
            crop = frame[py1:py2, px1:px2]

            if crop.size == 0:
                continue

            faces.append({
                "face_id": f"person_{i + 1}",
                "bbox": {
                    "x_min": round(float(x_min), 4),
                    "y_min": round(float(y_min), 4),
                    "x_max": round(float(x_max), 4),
                    "y_max": round(float(y_max), 4),
                },
                "confidence": round(conf, 3),
                "crop": crop,
            })

    return faces
