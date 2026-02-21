import asyncio
import websockets
import json

async def test():
    async with websockets.connect("ws://localhost:8000/ws/stream") as ws:
        for i in range(3):
            msg = await asyncio.wait_for(ws.recv(), timeout=5)
            data = json.loads(msg)
            print(f"Frame {data.get('frame_id')}: faces={list(data.get('faces', {}).keys())}")
            if data.get("faces"):
                fid = list(data["faces"].keys())[0]
                f = data["faces"][fid]
                expr = f.get("expression", {})
                rppg = f.get("rppg", {})
                print(f"  expression: {expr.get('dominant_emotion')} ({expr.get('confidence')})")
                print(f"  rppg bpm: {rppg.get('bpm')} state: {rppg.get('calibration_state')}")

asyncio.run(test())
