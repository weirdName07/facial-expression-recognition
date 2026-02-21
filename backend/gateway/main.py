from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Response, status
from fastapi.middleware.cors import CORSMiddleware
from backend.shared.redis_client import RedisPubSub
from contextlib import asynccontextmanager
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
start_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    asyncio.create_task(r.subscribe("inference_results", manager.broadcast))
    logging.info("Gateway service started and connected to Redis inference_results channel.")
    yield
    # Shutdown
    await r.close()
    logging.info("Gateway service shutdown complete.")

app = FastAPI(title="Facial Expression Event Gateway", lifespan=lifespan)

@app.get("/health")
async def health_check():
    """Health check for Docker/K8s monitoring."""
    return {"status": "ok", "connections": len(manager.active_connections)}

@app.websocket("/ws/stream")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
             # Wait for client messages
             data = await websocket.receive_text()
             try:
                 msg = json.loads(data)
                 if msg.get("type") == "START_INF":
                     logging.info("Received START_INF command from frontend")
                     start_event.set()
             except:
                 pass
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        # If no one is left, signal the runner to stop
        if not manager.active_connections:
            logging.info("All clients disconnected. Clearing start_event.")
            start_event.clear()
    except Exception as e:
        logging.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)
        if not manager.active_connections:
            start_event.clear()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
