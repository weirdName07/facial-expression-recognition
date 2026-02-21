"""
Face Recognizer module using DeepFace.
Calculates embeddings and performs matching against the known_faces/ directory.
Includes age smoothing and vector-based matching for stability.
"""

import os
import logging
import pickle
import numpy as np
import cv2
from pathlib import Path
from deepface import DeepFace
from typing import Dict, List, Tuple

log = logging.getLogger(__name__)

# Directory where known person subfolders are kept
KNOWN_FACES_DIR = Path(__file__).parent.parent.parent / "known_faces"
CACHE_PATH = KNOWN_FACES_DIR / "embeddings_v2.pkl"

MODEL_NAME = "Facenet512"
DISTANCE_METRIC = "cosine"
# Typical threshold for Facenet512 + cosine is around 0.3. 
# We'll be slightly more lenient (0.4) to avoid "Guest" if it's borderline.
THRESHOLD = 0.4 

class FaceDatabase:
    def __init__(self):
        self.embeddings: Dict[str, List[np.ndarray]] = {} # name -> list of vectors
        self.age_history: Dict[str, List[int]] = {} # track_id -> list of ages
        
    def load(self):
        """Build/Load the database of known faces."""
        if CACHE_PATH.exists():
            log.info(f"Loading cached embeddings from {CACHE_PATH}")
            with open(CACHE_PATH, "rb") as f:
                self.embeddings = pickle.load(f)
        else:
            self.refresh()

    def refresh(self):
        """Force re-indexing of the known_faces directory."""
        log.info("Indexing known_faces directory...")
        new_db = {}
        
        for person_dir in KNOWN_FACES_DIR.iterdir():
            if not person_dir.is_dir() or person_dir.name.startswith("."):
                continue
                
            name = person_dir.name
            new_db[name] = []
            
            for img_path in person_dir.iterdir():
                if img_path.suffix.lower() not in [".jpg", ".jpeg", ".png"]:
                    continue
                    
                try:
                    # Extract embedding
                    log.info(f"Extracting embedding for {name} from {img_path.name}")
                    result = DeepFace.represent(
                        img_path=str(img_path),
                        model_name=MODEL_NAME,
                        enforce_detection=True
                    )
                    if result:
                        new_db[name].append(np.array(result[0]["embedding"]))
                except Exception as e:
                    log.warning(f"Could not index {img_path}: {e}")
                    
        self.embeddings = new_db
        # Save to cache
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(self.embeddings, f)
        log.info("Database indexing complete.")

    def find_match(self, face_embedding: np.ndarray) -> str:
        """Find best name match for a given embedding."""
        best_name = "Guest"
        min_dist = 1.0
        
        for name, vectors in self.embeddings.items():
            for v in vectors:
                # Cosine distance = 1 - Cosine Similarity
                dist = 1 - (np.dot(face_embedding, v) / (np.linalg.norm(face_embedding) * np.linalg.norm(v)))
                if dist < min_dist:
                    min_dist = dist
                    best_name = name
                    
        if min_dist < THRESHOLD:
            return best_name
        return "Guest"

    def smooth_age(self, track_id: str, raw_age: int) -> int:
        """Moving average for age to stop jumping."""
        if track_id not in self.age_history:
            self.age_history[track_id] = []
        
        history = self.age_history[track_id]
        history.append(raw_age)
        if len(history) > 10:
            history.pop(0)
            
        return int(np.mean(history))

# Global DB instance
_db = FaceDatabase()

def load_recognizer():
    """Warmup and load DB."""
    _db.load()
    # Dummy represent to ensure model is in memory
    dummy_img = np.zeros((224, 224, 3), dtype=np.uint8)
    DeepFace.represent(dummy_img, model_name=MODEL_NAME, enforce_detection=False)

def recognize_face(face_crop: np.ndarray) -> str:
    """Identify face using the vector DB."""
    try:
        # Pre-process for DeepFace to avoid C++ exceptions (ensure it's not too small)
        if face_crop.shape[0] < 20 or face_crop.shape[1] < 20:
             return "Guest"

        result = DeepFace.represent(
            img_path=face_crop,
            model_name=MODEL_NAME,
            enforce_detection=False
        )
        if result:
            emb = np.array(result[0]["embedding"])
            return _db.find_match(emb)
    except Exception as e:
        log.warning(f"Recognition error: {e}")
    return "Guest"

def analyze_demographics(face_crop: np.ndarray, track_id: str = "unknown") -> Tuple[str, int]:
    """Analyze gender and smoothed age."""
    try:
        analysis = DeepFace.analyze(
            img_path=face_crop,
            actions=['gender', 'age'],
            enforce_detection=False,
            silent=True
        )
        if isinstance(analysis, list):
            analysis = analysis[0]
            
        gender_dict = analysis.get('gender', {})
        dominant_gender = max(gender_dict, key=gender_dict.get) if gender_dict else "Unknown"
        age_raw = analysis.get('age', 25)
        
        # Smooth age
        smoothed_age = _db.smooth_age(track_id, int(age_raw))
        
        return dominant_gender, smoothed_age
    except Exception as e:
        log.warning(f"Demographics analysis failed: {e}")
        return "Unknown", 25
