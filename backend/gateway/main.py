from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.redis_client import RedisPubSub
import asyncio
import json
import logging

app = FastAPI(title="Facial Expression Event Gateway")
logging.basicConfig(level=logging.INFO)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections.copy():
            try:
                await connection.send_json(message)
            except RuntimeError:
                 # In case connection was closed unexpectedly during loop
                 pass

manager = ConnectionManager()
r = RedisPubSub()

@app.on_event("startup")
async def startup_event():
    # Start Redis subscription listener in the background
    asyncio.create_task(r.subscribe("inference_results", manager.broadcast))
    logging.info("Gateway service started and connected to Redis inference_results channel.")

@app.on_event("shutdown")
async def shutdown_event():
    await r.close()

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
             # Wait for client messages (e.g. ping/pong, config updates)
             data = await websocket.receive_text()
             # We can optionally handle client configuration updates here
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
