import asyncio
import json
import math
import time

import websockets

HOST = "127.0.0.1"
PORT = 8765


async def handler(websocket):
    print("Client connected")
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                continue

            score = float(data.get("score", 0))
            airborne = bool(data.get("airborne", False))

            # Keep response light and deterministic for low-latency control updates.
            base = min(1.0, score / 140.0)
            pulse = 0.03 * math.sin(time.time() * 3.0)
            difficulty_scale = max(0.0, min(1.0, base + pulse))

            payload = {
                "difficulty_scale": difficulty_scale,
                "airborne_bonus": 0.04 if airborne else 0.0,
                "ts": time.time(),
            }
            await websocket.send(json.dumps(payload))
    except websockets.exceptions.ConnectionClosed:
        print("Client disconnected")


async def main():
    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        print(f"Realtime server running at ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
