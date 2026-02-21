"""
PyTorch Emotion Classifier — ResNet18 fine-tuned for FER2013 (7 emotions).

If no pretrained FER checkpoint is found, creates a model from scratch
using ImageNet-pretrained ResNet18 with a replaced classification head.
The model will still produce outputs — just not accurate until trained.
In practice you'd download a proper FER2013-trained checkpoint.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Dict, Tuple

import torch
import torch.nn as nn
import torchvision.transforms as T
from PIL import Image

log = logging.getLogger(__name__)

EMOTION_CLASSES = ["Angry", "Disgust", "Fear", "Happy", "Sad", "Surprise", "Neutral"]

# Preprocessing pipeline — FER2013 is 48x48 grayscale, but ResNet expects 224x224 RGB
_transform = T.Compose([
    T.Resize((224, 224)),
    T.Grayscale(num_output_channels=3),  # Convert to 3-channel grayscale
    T.ToTensor(),
    T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

_model = None
_device = None


def load_model():
    """Load the emotion classification model."""
    global _model, _device

    _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Emotion classifier device: {_device}")

    models_dir = Path(__file__).parent.parent.parent / "models"
    models_dir.mkdir(exist_ok=True)
    checkpoint_path = models_dir / "fer_resnet18.pth"

    # Build ResNet18 with 7-class head
    from torchvision.models import resnet18, ResNet18_Weights
    _model = resnet18(weights=ResNet18_Weights.DEFAULT)
    _model.fc = nn.Linear(_model.fc.in_features, len(EMOTION_CLASSES))

    if checkpoint_path.exists():
        log.info(f"Loading FER checkpoint: {checkpoint_path}")
        state = torch.load(str(checkpoint_path), map_location=_device)
        _model.load_state_dict(state, strict=False)
    else:
        log.warning(
            f"No FER checkpoint found at {checkpoint_path}. "
            "Using ImageNet backbone — predictions will be random until a proper "
            "FER2013-trained checkpoint is placed in backend/models/fer_resnet18.pth"
        )

    _model.to(_device)
    _model.eval()
    log.info("Emotion classifier loaded")


def classify_emotion(face_crop_bgr: np.ndarray) -> Tuple[str, float, Dict[str, float]]:
    """
    Classify the dominant emotion from a BGR face crop.

    Returns:
        (dominant_emotion, confidence, probabilities_dict)
    """
    if _model is None:
        raise RuntimeError("Model not loaded. Call load_model() first.")

    # Convert BGR → RGB → PIL → tensor
    rgb = face_crop_bgr[:, :, ::-1]  # BGR → RGB
    pil_img = Image.fromarray(rgb)
    tensor = _transform(pil_img).unsqueeze(0).to(_device)

    with torch.no_grad():
        logits = _model(tensor)
        probs = torch.softmax(logits, dim=1).squeeze().cpu().numpy()

    prob_dict = {EMOTION_CLASSES[i]: round(float(probs[i]), 4) for i in range(len(EMOTION_CLASSES))}
    dominant = max(prob_dict, key=prob_dict.get)
    confidence = prob_dict[dominant]

    return dominant, confidence, prob_dict
