import asyncio
import json
import random
import time

import websockets

HOST = "127.0.0.1"
PORT = 8767


async def handler(websocket):
    print("Game connected to MI online stub")
    seq = 0
    try:
        while True:
            await asyncio.sleep(0.1)
            seq += 1
            label = random.choices(["rest", "hand", "foot"], weights=[0.65, 0.22, 0.13], k=1)[0]
            confidence = 0.55 + random.random() * 0.42
            packet = {
                "seq": seq,
                "timestamp_ms": int(time.time() * 1000),
                "label": label,
                "confidence": confidence,
            }
            await websocket.send(json.dumps(packet))
    except websockets.exceptions.ConnectionClosed:
        print("Game disconnected")


async def main():
    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        print(f"MI online stub at ws://{HOST}:{PORT}")
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
