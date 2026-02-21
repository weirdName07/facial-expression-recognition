"""
Unified backend runner — real AI inference pipeline.

Captures webcam via OpenCV, runs YOLOv11 face detection + PyTorch emotion
classification, and broadcasts results via WebSocket gateway. rPPG remains
mock (future real implementation requires CHROM/POS signal processing).

Run:  python backend/run_all_services.py
"""

import sys
import os
import asyncio
import base64
import time
import math
import random
import logging
import signal
import threading
import queue

# Ensure project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cv2
import numpy as np
import uvicorn

from backend.shared.redis_client import RedisPubSub
from backend.gateway.main import app as gateway_app, start_event
from backend.services.face_tracking.face_detector import load_model as load_face_model, detect_faces
from backend.services.expression_recognition.emotion_classifier import (
    load_model as load_emotion_model, classify_emotion, EMOTION_CLASSES
)
from backend.services.heart_rate.rppg_engine import RPPGEngine

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
log = logging.getLogger("unified-runner")


# ═══════════════════════════════════════════════════════════════════
#  CAMERA CAPTURE THREAD (blocking OpenCV in a background thread)
# ═══════════════════════════════════════════════════════════════════
class CameraThread:
    """Captures webcam frames in a separate thread. Non-blocking for asyncio."""

    def __init__(self, camera_index: int = 0, target_fps: int = 15):
        self.cap = None
        # Allow override via environment variable
        env_cam = os.getenv("CAMERA_INDEX")
        self.camera_index = int(env_cam) if env_cam is not None else self._find_best_camera(camera_index)
        
        self.target_fps = target_fps
        self.frame_queue: queue.Queue = queue.Queue(maxsize=2)
        self._running = False
        self._thread = None
        
    def _find_best_camera(self, default_idx: int) -> int:
        """
        Windows Phone Link or virtual cameras often hijack index 0.
        This probes indices 0-2 and picks the one that successfully opens
        and has the highest default resolution (usually the real webcam).
        """
        log.info("Probing available cameras to avoid virtual/phone links...")
        best_idx = default_idx
        max_area = 0
        
        for idx in range(3):
            # Using CAP_DSHOW for faster probing on Windows
            cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
            if cap.isOpened():
                w = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
                h = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
                area = w * h
                log.info(f"Camera index {idx} found: {int(w)}x{int(h)}")
                
                # We assume the real webcam has a standard/higher resolution
                # compared to dummy virtual interfaces.
                if area > max_area:
                    max_area = area
                    best_idx = idx
                cap.release()
                
        log.info(f"Selected Camera Index: {best_idx}")
        return best_idx

    def start(self):
        log.info(f"Starting VideoCapture on index {self.camera_index}...")
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            log.warning(f"Failed to open camera {self.camera_index}. Trying fallback to 0.")
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        self._running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        log.info("Camera capture thread started")

    def _capture_loop(self):
        interval = 1.0 / self.target_fps
        while self._running:
            ret, frame = self.cap.read()
            if not ret:
                continue
            # Drop old frames — always keep the latest
            if self.frame_queue.full():
                try:
                    self.frame_queue.get_nowait()
                except queue.Empty:
                    pass
            self.frame_queue.put(frame)
            time.sleep(interval)

    def get_frame(self) -> np.ndarray | None:
        try:
            return self.frame_queue.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        self._running = False
        if self.cap:
            self.cap.release()
        log.info("Camera capture thread stopped")


class BoxSmoother:
    """EMA smoother for bounding box coordinates [x_min, y_min, x_max, y_max]."""
    def __init__(self, alpha: float = 0.2):
        self.alpha = alpha
        self.state: np.ndarray | None = None

    def smooth(self, box_coords: list[float]) -> list[float]:
        box_arr = np.array(box_coords)
        if self.state is None:
            self.state = box_arr
        else:
            self.state = self.alpha * box_arr + (1 - self.alpha) * self.state
        return [round(float(x), 4) for x in self.state]


# ═══════════════════════════════════════════════════════════════════
#  EMA SMOOTHER — for temporally stable outputs
# ═══════════════════════════════════════════════════════════════════
class EMASmoother:
    """Exponential Moving Average smoother for emotion probabilities."""

    def __init__(self, alpha: float = 0.3):
        self.alpha = alpha
        self.state: dict | None = None

    def smooth(self, raw_probs: dict) -> dict:
        if self.state is None:
            self.state = dict(raw_probs)
        else:
            for k in raw_probs:
                self.state[k] = self.alpha * raw_probs[k] + (1 - self.alpha) * self.state.get(k, 0)
        # Normalise
        total = sum(self.state.values())
        if total > 0:
            return {k: round(v / total, 4) for k, v in self.state.items()}
        return self.state


# ═══════════════════════════════════════════════════════════════════
#  rPPG MOCK — realistic ECG waveform (kept from previous version)
# ═══════════════════════════════════════════════════════════════════
class MockHeartRateEngine:
    def __init__(self):
        self.base_bpm = 72.0
        self.current_bpm = 72.0
        self.phase = 0.0
        self.calibration_frames = 30

    @staticmethod
    def _ecg_beat(t: float) -> float:
        p = 0.12 * math.exp(-((t - 0.15) ** 2) / 0.002)
        q = -0.08 * math.exp(-((t - 0.30) ** 2) / 0.0004)
        r = 0.85 * math.exp(-((t - 0.35) ** 2) / 0.0006)
        s = -0.15 * math.exp(-((t - 0.40) ** 2) / 0.0006)
        tw = 0.18 * math.exp(-((t - 0.60) ** 2) / 0.006)
        return p + q + r + s + tw

    def step(self) -> dict:
        self.base_bpm += random.gauss(0, 0.1)
        self.base_bpm = max(62, min(85, self.base_bpm))
        self.current_bpm += 0.05 * (self.base_bpm - self.current_bpm)

        n_samples = 50
        beat_period = 60.0 / self.current_bpm
        total_time = 2.0 * beat_period
        waveform = []
        for i in range(n_samples):
            t_sec = self.phase + (i / n_samples) * total_time
            t_in_beat = (t_sec % beat_period) / beat_period
            val = self._ecg_beat(t_in_beat) + random.gauss(0, 0.015)
            waveform.append(round(val, 3))
        self.phase += total_time * 0.3

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


# ═══════════════════════════════════════════════════════════════════
#  MAIN INFERENCE LOOP
# ═══════════════════════════════════════════════════════════════════
async def inference_loop(redis: RedisPubSub, camera: CameraThread):
    """
    Main inference loop:
      1. Wait for start signal from frontend
      2. Start camera and run inference session
      3. Stop camera and wait again if start signal is cleared
    """
    try:
        while True:
            log.info("Inference loop waiting for START_INF from frontend...")
            await start_event.wait()
            log.info("Start signal received! Initialising camera...")
            
            camera.start()
            # Give camera a moment to initialise
            await asyncio.sleep(1.0)

            # Signal handler for graceful shutdown
            stop_event = asyncio.Event()

            def handle_signal():
                log.info("Received stop signal...")
                stop_event.set()
                start_event.clear()

            loop = asyncio.get_running_loop()
            for sig in (signal.SIGINT, signal.SIGTERM):
                loop.add_signal_handler(sig, handle_signal)
            
            emotion_smoother = EMASmoother(alpha=0.25)
            box_smoothers: dict[str, BoxSmoother] = {}
            face_cache: dict[str, dict] = {}
            hr_engines: dict[str, RPPGEngine] = {}
            frame_id = 0

            log.info("Inference session active — processing real camera frames")

            try:
                while start_event.is_set() and not stop_event.is_set():
                    await asyncio.sleep(0.01)  # Minimal sleep to yield to event loop, allows max FPS

                    frame = camera.get_frame()
                    if frame is None:
                        continue

                    # ── Face Detection (run in thread to avoid blocking event loop) ──
                    detected = await asyncio.to_thread(detect_faces, frame, 0.35)

                    # ── Build per-face data ──
                    faces_payload = {}
                    current_time = time.time()
                    
                    for face_data in detected:
                        fid = face_data["face_id"]

                        # 1. Smooth bounding box (Fast - Every Frame)
                        if fid not in box_smoothers:
                            box_smoothers[fid] = BoxSmoother(alpha=0.25)
                        
                        bbox_raw = [
                            face_data["bbox"]["x_min"],
                            face_data["bbox"]["y_min"],
                            face_data["bbox"]["x_max"],
                            face_data["bbox"]["y_max"]
                        ]
                        sx1, sy1, sx2, sy2 = box_smoothers[fid].smooth(bbox_raw)

                        # 2. Identity & Demographics (Slow - Throttled/Cached)
                        # We only re-run biometrics if it's a new face or every ~2 seconds (30 frames)
                        cache_entry = face_cache.get(fid)
                        should_refresh = (
                            cache_entry is None or 
                            (frame_id - cache_entry["last_throttle_frame"]) >= 30
                        )

                        if should_refresh:
                            import backend.services.face_tracking.face_recognizer as fr
                            # Run ID and Demographics in parallel threads
                            try:
                                # Identities & Demographics (Slow)
                                person_name = await asyncio.to_thread(fr.recognize_face, face_data["crop"])
                                gender, age = await asyncio.to_thread(fr.analyze_demographics, face_data["crop"], fid)
                                
                                biometrics = {
                                    "identity": person_name,
                                    "gender": gender,
                                    "age": age,
                                    "last_throttle_frame": frame_id
                                }
                                face_cache[fid] = biometrics
                            except Exception as e:
                                log.warning(f"Face analysis failed for ID {fid}: {e}")
                                # Use old values if failed, or defaults if new
                                if cache_entry is None:
                                    face_cache[fid] = {
                                        "identity": "Guest", "gender": "Unknown", "age": "Unknown",
                                        "last_throttle_frame": frame_id
                                    }
                        
                        # Extract from cache
                        biometrics = face_cache[fid]

                        # 3. Expression classification (Fast - Every Frame)
                        try:
                            dominant, conf, probs = await asyncio.to_thread(
                                classify_emotion, face_data["crop"]
                            )
                            smoothed = emotion_smoother.smooth(probs)
                            dominant = max(smoothed, key=smoothed.get)
                            conf = smoothed[dominant]
                        except Exception as e:
                            log.warning(f"Emotion classification failed: {e}")
                            smoothed = {em: round(1.0 / 7, 4) for em in EMOTION_CLASSES}
                            dominant = "Neutral"
                            conf = smoothed["Neutral"]

                        # 4. rPPG (Fast - Every Frame)
                        if fid not in hr_engines:
                            hr_engines[fid] = RPPGEngine(fs=15.0) # Match target FPS
                        
                        bpm, quality = hr_engines[fid].update(face_data["crop"])
                        pulse_data = hr_engines[fid].get_waveform(window_size=60)
                        state = hr_engines[fid].get_state()
                        
                        rppg_payload = {
                            "bpm": bpm,
                            "waveform": pulse_data,
                            "quality_score": quality,
                            "calibration_state": state["state_text"]
                        }

                        faces_payload[fid] = {
                            "identity": biometrics["identity"],
                            "gender": biometrics["gender"],
                            "age": biometrics["age"],
                            "bbox": {
                                "x_min": sx1, "y_min": sy1, "x_max": sx2, "y_max": sy2
                            },
                            "tracking_confidence": face_data["confidence"],
                            "expression": {
                                "dominant_emotion": dominant,
                                "probabilities": smoothed,
                                "confidence": round(conf, 3),
                            },
                            "rppg": rppg_payload,
                        }

                    # Clean up old smoothers & caches
                    current_fids = {f["face_id"] for f in detected}
                    for fid in list(box_smoothers.keys()):
                        if fid not in current_fids:
                            del box_smoothers[fid]
                    for fid in list(face_cache.keys()):
                        if fid not in current_fids:
                            del face_cache[fid]
                    for fid in list(hr_engines.keys()):
                        if fid not in current_fids:
                            del hr_engines[fid]

                    # ── Encode frame as base64 JPEG for frontend display ──
                    _, jpeg_buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    frame_b64 = base64.b64encode(jpeg_buf).decode('ascii')

                    # ── Publish ──
                    payload = {
                        "frame_id": frame_id,
                        "timestamp": time.time(),
                        "faces": faces_payload,
                        "frame": frame_b64,
                    }
                    await redis.publish("inference_results", payload)
                    frame_id += 1

                if stop_event.is_set():
                    break
                
                log.info("Inference session ended (start_event cleared).")

            except Exception as e:
                log.error(f"Inference session error: {e}")
            finally:
                camera.stop()
                log.info("Camera released.")
                while not camera.frame_queue.empty():
                    camera.get_frame()

            if stop_event.is_set():
                 break

    except asyncio.CancelledError:
        log.info("Inference loop cancelled")


# ═══════════════════════════════════════════════════════════════════
#  MAIN
# ═══════════════════════════════════════════════════════════════════
async def run_gateway():
    config = uvicorn.Config(
        gateway_app, 
        host="0.0.0.0", 
        port=8000, 
        log_level="info",
        ws_ping_interval=None, # Disable to prevent AssertionError crashes during heavy inference
        ws_ping_timeout=None
    )
    server = uvicorn.Server(config)
    await server.serve()


async def main():
    log.info("=" * 60)
    log.info("  Facial Expression Platform — AI Inference Runner")
    log.info("=" * 60)

    # ── Load AI models ──
    log.info("Loading YOLO-Face detector...")
    await asyncio.to_thread(load_face_model)

    log.info("Loading PyTorch emotion classifier...")
    await asyncio.to_thread(load_emotion_model)

    log.info("Loading FaceNet Identity Recognizer...")
    import backend.services.face_tracking.face_recognizer as fr
    await asyncio.to_thread(fr.load_recognizer)

    # ── Camera Setup (lazily started in inference_loop) ──
    camera = CameraThread(camera_index=0, target_fps=15)

    # ── Redis ──
    redis = RedisPubSub()

    try:
        await asyncio.gather(
            run_gateway(),
            inference_loop(redis, camera),
        )
    finally:
        camera.stop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Shutting down all services…")
