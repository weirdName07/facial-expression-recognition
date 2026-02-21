import asyncio
import logging
from fastapi import FastAPI
from backend.shared.redis_client import RedisPubSub
from backend.shared.models import FaceTrackingData, BoundingBox, Point

# NOTE: Stub for face tracking. In production, this would initialize
# YOLOv11 or RetinaFace with DeepSORT/ByteTrack.
# from ultralytics import YOLO
# model = YOLO('yolov11n-face.pt')

app = FastAPI(title="Face Detection & Tracking Service")
logging.basicConfig(level=logging.INFO)
r = RedisPubSub()

async def mock_tracking_loop():
    """Mock tracking inference loop emitting 30 FPS bounding boxes."""
    frame_count = 0
    try:
        while True:
            # Simulate processing delay
            await asyncio.sleep(1/30) 
            
            # Emit mock data
            data = FaceTrackingData(
                face_id="p1",
                bbox=BoundingBox(x_min=0.3, y_min=0.2, x_max=0.5, y_max=0.6),
                landmarks=[Point(x=0.35, y=0.3), Point(x=0.45, y=0.3), Point(x=0.4, y=0.4)], # Left eye, Right eye, Nose 
                confidence=0.98
            )
            
            # Publish to a channel for expression and rPPG services to pick up
            await r.publish("face_crops", {"frame": frame_count, "faces": [data.model_dump()]})
            frame_count += 1
            
    except asyncio.CancelledError:
        logging.info("Tracking task cancelled")

@app.on_event("startup")
async def startup_event():
    logging.info("Face Tracking Service Starting...")
    asyncio.create_task(mock_tracking_loop())

@app.on_event("shutdown")
async def shutdown_event():
    await r.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
