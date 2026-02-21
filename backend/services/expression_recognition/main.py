import asyncio
import logging
from fastapi import FastAPI
from backend.shared.redis_client import RedisPubSub
from backend.shared.models import ExpressionData

app = FastAPI(title="Facial Expression Recognition Service")
logging.basicConfig(level=logging.INFO)
r = RedisPubSub()

async def process_face_crop(data: dict):
    # This is a stub for the heavy model inference (AffectNet/FER+)
    # It would receive a face crop from the 'face_crops' channel.
    faces = data.get('faces', [])
    for face in faces:
        expression_data = ExpressionData(
            face_id=face['face_id'],
            dominant_emotion="Happy",
            probabilities={"Happy": 0.85, "Neutral": 0.1, "Surprise": 0.05},
            confidence=0.92
        )
        
        # Publish the result 
        await r.publish("expression_results", expression_data.model_dump())

@app.on_event("startup")
async def startup_event():
    logging.info("Expression Service Subscribing to Face Crops...")
    asyncio.create_task(r.subscribe("face_crops", process_face_crop))

@app.on_event("shutdown")
async def shutdown_event():
    await r.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
