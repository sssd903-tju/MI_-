import argparse
import asyncio
import json
import time
from pathlib import Path

import websockets

HOST = "127.0.0.1"
PORT = 8766


def load_scenario(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("scenario must be a list")
    return data


async def stream_scenario(websocket, scenario: list[dict], loop: bool) -> None:
    seq = 0
    while True:
        for step in scenario:
            wait_s = float(step.get("wait_s", 0.1))
            label = str(step.get("label", "rest")).lower()
            confidence = float(step.get("confidence", 1.0 if label == "rest" else 0.9))

            if label not in {"hand", "foot", "rest"}:
                label = "rest"
            confidence = max(0.0, min(1.0, confidence))

            seq += 1
            packet = {
                "seq": seq,
                "timestamp_ms": int(time.time() * 1000),
                "label": label,
                "confidence": confidence,
            }
            await websocket.send(json.dumps(packet))
            await asyncio.sleep(max(0.0, wait_s))

        if not loop:
            break


async def run_server(scenario_path: Path, loop_playback: bool) -> None:
    scenario = load_scenario(scenario_path)

    async def handler(websocket):
        print("Game connected, start replay")
        try:
            await stream_scenario(websocket, scenario, loop_playback)
        finally:
            print("Game disconnected")

    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        print(f"MI offline replay server at ws://{HOST}:{PORT}")
        print(f"Scenario: {scenario_path}")
        await asyncio.Future()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", type=Path, default=Path(__file__).parent / "mi_scenarios" / "basic_flow.json")
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()
    asyncio.run(run_server(args.scenario, args.loop))
