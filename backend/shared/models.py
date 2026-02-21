from pydantic import BaseModel
from typing import List, Dict, Tuple, Optional

class Point(BaseModel):
    x: float
    y: float

class BoundingBox(BaseModel):
    x_min: float
    y_min: float
    x_max: float
    y_max: float

class FaceTrackingData(BaseModel):
    face_id: str
    bbox: BoundingBox
    landmarks: List[Point] # e.g. 5 points for eyes, nose, mouth
    confidence: float

class ExpressionData(BaseModel):
    face_id: str
    dominant_emotion: str
    probabilities: Dict[str, float]
    confidence: float

class HeartRateData(BaseModel):
    face_id: str
    bpm: float
    quality_score: float
    waveform: List[float] # Recent sliding window for rendering
    calibration_state: str # e.g., "CALIBRATING", "STABLE", "UNSTABLE"

class AggregatedFrameData(BaseModel):
    frame_id: int
    timestamp: float
    faces: Dict[str, dict] # key: face_id, value: aggregated info
