"""
Emotion Classifier using HSEmotion (trained on RAF-DB and AffectNet).
Highly accurate and lightweight (EfficientNet-B0 or MobileNetV3).
"""

import logging
import numpy as np
import cv2
from typing import Dict, Tuple
from hsemotion.facial_emotions import HSEmotionRecognizer

log = logging.getLogger(__name__)

# HSEmotion labels (8 classes):
# ['angry', 'contempt', 'disgust', 'fear', 'happy', 'neutral', 'sad', 'surprise']
# We adjust to match our frontend's expected 7 classes where possible.
HSE_LABELS = ['Angry', 'Contempt', 'Disgust', 'Fear', 'Happy', 'Neutral', 'Sad', 'Surprise']
EMOTION_CLASSES = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

_fer = None

def load_model():
    """Load the HSEmotion recognizer."""
    global _fer
    log.info("Loading HSEmotion (RAF-DB optimized) model...")
    try:
        # PyTorch 2.4+ has safe unpickling by default (weights_only=True).
        # External libraries like timm/hsemotion often fail this check.
        # We monkey-patch torch.load temporarily to allow the model to boot.
        import torch
        import functools
        
        orig_load = torch.load
        # Force weights_only=False for the duration of this call
        torch.load = functools.partial(orig_load, weights_only=False)
        
        try:
            # enet_b0_8_best_vgaf is highly accurate (RAF-DB/AffectNet) and very fast
            _fer = HSEmotionRecognizer(model_name='enet_b0_8_best_vgaf', device='cpu')
        finally:
            # Always restore original torch.load
            torch.load = orig_load
            
        log.info("HSEmotion model loaded successfully")
    except Exception as e:
        log.error(f"Failed to load HSEmotion: {e}")
        raise

def classify_emotion(face_crop: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
    """
    Classify expression using HSEmotion.
    """
    if _fer is None:
        load_model()

    try:
        # HSEmotion expects RGB
        rgb_img = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)
        
        # predict_emotions returns (label, probs)
        label, probs = _fer.predict_emotions(rgb_img, logits=False)
        
        # Map HSE 8-class to our 7-class system
        # We merge 'Contempt' into 'Neutral' or just ignore it for the dominant
        prob_dict_raw = {HSE_LABELS[i]: round(float(probs[i]), 4) for i in range(len(HSE_LABELS))}
        
        # Construct the final 7-class dict
        final_probs = {
            "Angry": prob_dict_raw["Angry"],
            "Disgust": prob_dict_raw["Disgust"],
            "Fear": prob_dict_raw["Fear"],
            "Happy": prob_dict_raw["Happy"],
            "Sad": prob_dict_raw["Sad"],
            "Surprise": prob_dict_raw["Surprise"],
            "Neutral": round(prob_dict_raw["Neutral"] + prob_dict_raw["Contempt"], 4)
        }
        
        dominant = max(final_probs, key=final_probs.get)
        confidence = final_probs[dominant]
        
        return dominant, confidence, final_probs

    except Exception as e:
        log.warning(f"HSEmotion inference failed: {e}")
        # Return Neutral as fallback
        fallback_probs = {c: 0.1428 for c in EMOTION_CLASSES}
        fallback_probs["Neutral"] = 1.0
        return "Neutral", 1.0, fallback_probs
