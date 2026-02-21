"""
Unified backend runner — runs ALL services + aggregator in a single process.
Run from the project root:
    python backend/run_all_services.py
"""

import sys
import os
import asyncio
import json
import time
import math
import random
import logging

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import uvicorn
from backend.shared.redis_client import RedisPubSub
from backend.gateway.main import app as gateway_app

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("unified-runner")


# ═══════════════════════════════════════════════════════════════════
#  TEMPORALLY SMOOTH FACE TRACKING  (simulates stable detection)
# ═══════════════════════════════════════════════════════════════════
class SmoothFaceTracker:
    """
    Generates temporally-stable mock bounding boxes with very low jitter.
    In production this would be YOLOv11 + ByteTrack.
    """

    def __init__(self):
        # Centred face position in normalised coordinates (0-1)
        self.cx = 0.50
        self.cy = 0.40
        self.half_w = 0.14
        self.half_h = 0.25

    def step(self):
        # Very subtle drift to simulate natural head movement
        self.cx += random.gauss(0, 0.002)
        self.cy += random.gauss(0, 0.001)
        # Clamp to reasonable range
        self.cx = max(0.30, min(0.70, self.cx))
        self.cy = max(0.25, min(0.55, self.cy))

        return {
            "face_id": "person_1",
            "bbox": {
                "x_min": round(self.cx - self.half_w, 4),
                "y_min": round(self.cy - self.half_h, 4),
                "x_max": round(self.cx + self.half_w, 4),
                "y_max": round(self.cy + self.half_h, 4),
            },
            "landmarks": [
                {"x": round(self.cx - 0.04, 4), "y": round(self.cy - 0.04, 4)},
                {"x": round(self.cx + 0.04, 4), "y": round(self.cy - 0.04, 4)},
                {"x": round(self.cx, 4),         "y": round(self.cy + 0.06, 4)},
            ],
            "confidence": round(0.96 + random.uniform(0, 0.03), 3),
        }


tracker = SmoothFaceTracker()


async def face_tracking_loop(redis: RedisPubSub):
    frame = 0
    log.info("Face Tracking loop started (smooth)")
    try:
        while True:
            await asyncio.sleep(0.1)  # 10 FPS
            face = tracker.step()
            await redis.publish("face_crops", {"frame": frame, "faces": [face]})
            frame += 1
    except asyncio.CancelledError:
        log.info("Face tracking loop cancelled")


# ═══════════════════════════════════════════════════════════════════
#  TEMPORALLY SMOOTH EXPRESSION RECOGNITION
# ═══════════════════════════════════════════════════════════════════
EMOTIONS = ["Happy", "Neutral", "Sad", "Angry", "Surprise", "Fear", "Disgust"]
EMA_ALPHA = 0.08  # Low alpha = smoother/slower transitions

class SmoothExpressionEngine:
    """
    Generates emotion probabilities that transition slowly and naturally.
    Uses EMA (Exponential Moving Average) smoothing.
    """

    def __init__(self):
        # Start neutral
        self.current_probs = {e: (0.9 if e == "Neutral" else 0.02) for e in EMOTIONS}
        self.target_probs = dict(self.current_probs)
        self.frames_until_shift = 50  # Change target emotion every ~5s

    def step(self) -> dict:
        self.frames_until_shift -= 1

        if self.frames_until_shift <= 0:
            # Pick a new dominant emotion with weighted probabilities
            dominant = random.choices(
                EMOTIONS,
                weights=[5, 4, 1, 1, 2, 1, 0.5],
                k=1
            )[0]
            # Generate new target distribution centred on the dominant emotion
            raw = {}
            for e in EMOTIONS:
                if e == dominant:
                    raw[e] = random.uniform(0.6, 0.85)
                else:
                    raw[e] = random.uniform(0.01, 0.1)
            total = sum(raw.values())
            self.target_probs = {e: v / total for e, v in raw.items()}
            # Next shift in 30-80 frames (3-8 seconds at 10 FPS)
            self.frames_until_shift = random.randint(30, 80)

        # EMA smoothing toward target
        for e in EMOTIONS:
            self.current_probs[e] += EMA_ALPHA * (self.target_probs[e] - self.current_probs[e])

        # Normalise
        total = sum(self.current_probs.values())
        probs = {e: round(v / total, 4) for e, v in self.current_probs.items()}

        dominant = max(probs, key=probs.get)
        return {
            "dominant_emotion": dominant,
            "probabilities": probs,
            "confidence": round(probs[dominant], 3),
        }


expr_engine = SmoothExpressionEngine()


async def expression_callback(data: dict, redis: RedisPubSub):
    for face in data.get("faces", []):
        result = expr_engine.step()
        result["face_id"] = face["face_id"]
        await redis.publish("expression_results", result)


# ═══════════════════════════════════════════════════════════════════
#  TEMPORALLY SMOOTH rPPG HEART RATE
# ═══════════════════════════════════════════════════════════════════
class SmoothHeartRateEngine:
    """
    Produces a realistic, slowly-drifting heart rate and clean PPG waveform.
    """

    def __init__(self):
        self.base_bpm = 72.0          # Resting heart rate
        self.current_bpm = 72.0
        self.phase = 0.0
        self.calibration_frames = 30  # First 3 seconds = calibrating

    def step(self) -> dict:
        # Slowly drift BPM
        self.base_bpm += random.gauss(0, 0.1)
        self.base_bpm = max(62, min(85, self.base_bpm))
        # EMA smooth the displayed BPM
        self.current_bpm += 0.05 * (self.base_bpm - self.current_bpm)

        # Generate clean sinusoidal PPG waveform
        freq = self.current_bpm / 60.0  # Hz
        waveform = []
        for i in range(50):
            t = self.phase + i * 0.02
            # Primary cardiac signal + smaller harmonic
            val = (0.7 * math.sin(2 * math.pi * freq * t)
                   + 0.2 * math.sin(4 * math.pi * freq * t)
                   + random.gauss(0, 0.03))
            waveform.append(round(val, 3))
        self.phase += 0.5

        # Handle calibration state
        if self.calibration_frames > 0:
            self.calibration_frames -= 1
            state = "CALIBRATING"
        else:
            state = "STABLE"

        return {
            "bpm": round(self.current_bpm, 1),
            "quality_score": round(0.85 + random.uniform(0, 0.1), 2),
            "waveform": waveform,
            "calibration_state": state,
        }


hr_engine = SmoothHeartRateEngine()


async def rppg_callback(data: dict, redis: RedisPubSub):
    for face in data.get("faces", []):
        result = hr_engine.step()
        result["face_id"] = face["face_id"]
        await redis.publish("rppg_results", result)


# ═══════════════════════════════════════════════════════════════════
#  AGGREGATOR — Merges all service outputs → "inference_results"
# ═══════════════════════════════════════════════════════════════════
class Aggregator:
    def __init__(self, redis: RedisPubSub):
        self.redis = redis
        self.faces: dict = {}
        self.frame_id = 0

    async def on_face_crops(self, data: dict):
        for face in data.get("faces", []):
            fid = face["face_id"]
            self.faces.setdefault(fid, {})
            self.faces[fid]["bbox"] = face["bbox"]
            self.faces[fid]["landmarks"] = face["landmarks"]
            self.faces[fid]["tracking_confidence"] = face["confidence"]

        # Trigger expression + rPPG processing on same frame
        await expression_callback(data, self.redis)
        await rppg_callback(data, self.redis)

    async def on_expression(self, data: dict):
        fid = data.get("face_id")
        if fid and fid in self.faces:
            self.faces[fid]["expression"] = {
                "dominant_emotion": data["dominant_emotion"],
                "probabilities": data["probabilities"],
                "confidence": data["confidence"],
            }

    async def on_rppg(self, data: dict):
        fid = data.get("face_id")
        if fid and fid in self.faces:
            self.faces[fid]["rppg"] = {
                "bpm": data["bpm"],
                "quality_score": data["quality_score"],
                "waveform": data["waveform"],
                "calibration_state": data["calibration_state"],
            }

    async def broadcast_loop(self):
        log.info("Aggregator broadcast loop started")
        try:
            while True:
                await asyncio.sleep(0.1)
                if self.faces:
                    payload = {
                        "frame_id": self.frame_id,
                        "timestamp": time.time(),
                        "faces": dict(self.faces),
                    }
                    await self.redis.publish("inference_results", payload)
                    self.frame_id += 1
        except asyncio.CancelledError:
            log.info("Aggregator broadcast loop cancelled")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
async def run_gateway():
    config = uvicorn.Config(gateway_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    log.info("=" * 60)
    log.info("  Facial Expression Platform — Unified Backend Runner")
    log.info("=" * 60)

    redis_tracking = RedisPubSub()
    redis_expr_sub = RedisPubSub()
    redis_rppg_sub = RedisPubSub()

    aggregator = Aggregator(redis_tracking)

    await asyncio.gather(
        run_gateway(),
        face_tracking_loop(redis_tracking),
        redis_tracking.subscribe("face_crops", aggregator.on_face_crops),
        redis_expr_sub.subscribe("expression_results", aggregator.on_expression),
        redis_rppg_sub.subscribe("rppg_results", aggregator.on_rppg),
        aggregator.broadcast_loop(),
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down all services…")
