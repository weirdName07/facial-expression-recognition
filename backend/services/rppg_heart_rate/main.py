import asyncio
import logging
import random
from fastapi import FastAPI
from backend.shared.redis_client import RedisPubSub
from backend.shared.models import HeartRateData

app = FastAPI(title="rPPG Heart Rate Service")
logging.basicConfig(level=logging.INFO)
r = RedisPubSub()

# In production, this service would maintain a sliding window 
# of face frames across time for a given face_id,
# segment the skin, extract RGB signals, and run POS/CHROM algorithm.

async def process_face_crop(data: dict):
    faces = data.get('faces', [])
    for face in faces:
        # Generate a mock waveform for visual testing
        mock_waveform = [random.uniform(-1, 1) for _ in range(50)]
        hr_data = HeartRateData(
            face_id=face['face_id'],
            bpm=random.uniform(65, 80),
            quality_score=0.85,
            waveform=mock_waveform,
            calibration_state="STABLE"
        )
        await r.publish("rppg_results", hr_data.model_dump())

@app.on_event("startup")
async def startup_event():
    logging.info("rPPG Service Subscribing to Face Crops...")
    asyncio.create_task(r.subscribe("face_crops", process_face_crop))

@app.on_event("shutdown")
async def shutdown_event():
    await r.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
