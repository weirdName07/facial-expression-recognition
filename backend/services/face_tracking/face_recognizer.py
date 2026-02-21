"""
Face Recognizer module using DeepFace.
Calculates embeddings and performs matching against the known_faces/ directory.
"""

import os
import logging
import pickle
import numpy as np
import cv2
from pathlib import Path
from deepface import DeepFace

log = logging.getLogger(__name__)

# Directory where known person subfolders are kept
KNOWN_FACES_DIR = Path(__file__).parent.parent.parent / "known_faces"

# Model used for embeddings. 'Facenet512' is very accurate.
# 'VGG-Face' is also good but larger.
ENFORCE_DETECTION = False # Set to false since detector already found the face
MODEL_NAME = "Facenet512"

def load_recognizer():
    """ Warmup DeepFace by pre-loading the requested model. """
    log.info(f"Warming up DeepFace recognizer model: {MODEL_NAME}...")
    try:
        # Just call a represent on a dummy image to trigger model download/loading
        dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
        DeepFace.represent(dummy_img, model_name=MODEL_NAME, enforce_detection=False)
        log.info("DeepFace models loaded successfully.")
    except Exception as e:
        log.error(f"Failed to warmup DeepFace: {e}")

def recognize_face(face_crop: np.ndarray, db_path: str = None) -> str:
    """
    Takes an OpenCV BGR face crop and identifies it using DeepFace.find().
    
    If you want to use a cached DB, DeepFace handles its own pkl file.
    """
    if db_path is None:
        db_path = str(KNOWN_FACES_DIR)

    try:
        # DeepFace.find returns a list of dataframes
        # It's better for large DBs, but for small ones we can use represent + manual cosine
        # Let's use it directly as it's very robust.
        results = DeepFace.find(
            img_path=face_crop,
            db_path=db_path,
            model_name=MODEL_NAME,
            enforce_detection=ENFORCE_DETECTION,
            silent=True
        )
        
        if results and not results[0].empty:
            # results[0] is the top DF matches
            best_match = results[0].iloc[0]['identity']
            # identity is the path to the image, e.g., 'known_faces/Rito/pic.jpg'
            # We want the folder name
            person_name = Path(best_match).parent.name
            return person_name
            
    except Exception as e:
        log.warning(f"Recognition error: {e}")
        
    return "Guest"

def analyze_demographics(face_crop: np.ndarray):
    """
    Analyzes gender, age, etc. using DeepFace.
    """
    try:
        analysis = DeepFace.analyze(
            img_path=face_crop,
            actions=['gender', 'age'],
            enforce_detection=ENFORCE_DETECTION,
            silent=True
        )
        
        if isinstance(analysis, list):
            analysis = analysis[0]
            
        gender_dict = analysis.get('gender', {})
        dominant_gender = max(gender_dict, key=gender_dict.get) if gender_dict else "Unknown"
        age = analysis.get('age', 'Unknown')
        
        return dominant_gender, age
    except Exception as e:
        log.warning(f"Demographics analysis failed: {e}")
        return "Unknown", "Unknown"
