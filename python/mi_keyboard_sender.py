import asyncio
import json
import sys
import time

import websockets

HOST = "127.0.0.1"
PORT = 8766


def build_packet(seq: int, label: str, confidence: float) -> str:
    return json.dumps(
        {
            "seq": seq,
            "timestamp_ms": int(time.time() * 1000),
            "label": label,
            "confidence": confidence,
        }
    )


async def keyboard_sender(websocket) -> None:
    print("MI offline keyboard sender")
    print("h=hand, f=foot, r=rest, q=quit")
    print("Optional confidence: e.g. h 0.85")

    seq = 0
    loop = asyncio.get_running_loop()
    while True:
        line = await loop.run_in_executor(None, sys.stdin.readline)
        if not line:
            await asyncio.sleep(0.05)
            continue

        text = line.strip().lower()
        if not text:
            continue
        if text == "q":
            print("quit")
            break

        parts = text.split()
        key = parts[0]
        label = "rest"
        if key == "h":
            label = "hand"
        elif key == "f":
            label = "foot"
        elif key == "r":
            label = "rest"
        else:
            print("unknown key, use h/f/r/q")
            continue

        confidence = 0.9 if label != "rest" else 1.0
        if len(parts) >= 2:
            try:
                confidence = float(parts[1])
            except ValueError:
                print("invalid confidence, fallback to default")

        seq += 1
        await websocket.send(build_packet(seq, label, max(0.0, min(1.0, confidence))))
        print(f"sent #{seq}: {label} conf={confidence:.2f}")


async def main() -> None:
    print(f"MI keyboard websocket server at ws://{HOST}:{PORT}")
    print("Start game in MI + Offline mode, then connect and input h/f/r.")

    async def handler(websocket):
        print("Game connected.")
        try:
            await keyboard_sender(websocket)
        except websockets.exceptions.ConnectionClosed:
            print("Game disconnected.")

    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
