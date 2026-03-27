import asyncio
import json
import os
import select
import sys
import termios
import time
import tty
from datetime import datetime

import websockets

HOST = "127.0.0.1"
PORT = 8766
READ_TIMEOUT_SEC = 0.05


class RawInput:
    def __enter__(self):
        self.fd = sys.stdin.fileno()
        self.old_settings = termios.tcgetattr(self.fd)
        tty.setraw(self.fd)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        termios.tcsetattr(self.fd, termios.TCSADRAIN, self.old_settings)


def now_iso() -> str:
    return datetime.now().isoformat(timespec="milliseconds")


def build_packet(seq: int, label: str, confidence: float, key: str, delta_ms: int) -> str:
    return json.dumps(
        {
            "seq": seq,
            "timestamp_ms": int(time.time() * 1000),
            "timestamp_iso": now_iso(),
            "label": label,
            "confidence": confidence,
            "key": key,
            "delta_ms": delta_ms,
        }
    )


async def _game_receiver(websocket) -> None:
    last_print_ms = 0
    last_state = None
    try:
        async for raw in websocket:
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                print(f"\n[GAME] {raw}", flush=True)
                continue

            if isinstance(payload, dict):
                score = payload.get("score", "-")
                airborne = payload.get("airborne", "-")
                mi_state = payload.get("mi_state", "-")
                now_ms = int(time.time() * 1000)
                state_tuple = (score, airborne, mi_state)
                if state_tuple != last_state or now_ms - last_print_ms >= 500:
                    print(f"\n[GAME] score={score} airborne={airborne} mi_state={mi_state}", flush=True)
                    last_print_ms = now_ms
                    last_state = state_tuple
            else:
                print(f"\n[GAME] {payload}", flush=True)
    except websockets.exceptions.ConnectionClosed:
        pass


async def keyboard_sender(websocket) -> None:
    print("MI offline keyboard sender")
    print("hotkeys: h=hand, f=foot, r=rest, q=quit")
    print("confidence: + / - adjust step=0.05, c show current")
    print("optional command mode: type ':h 0.85' then Enter")
    print("ready: press h/f/r directly", flush=True)

    seq = 0
    confidence_hand = 0.9
    confidence_foot = 0.9
    last_event_ms = int(time.time() * 1000)
    command_buffer = ""

    with RawInput() as raw:
        while True:
            ready, _, _ = select.select([raw.fd], [], [], READ_TIMEOUT_SEC)
            if not ready:
                await asyncio.sleep(0)
                continue

            ch = os.read(raw.fd, 1).decode("utf-8", errors="ignore")
            if not ch:
                continue
            if ch == "\x03":
                print("\nquit (ctrl-c)", flush=True)
                break

            if command_buffer:
                if ch in ("\r", "\n"):
                    cmd = command_buffer.strip().lower()
                    command_buffer = ""
                    if not cmd:
                        continue
                    parts = cmd.split()
                    if len(parts) == 2 and parts[0] in ("h", "f", "r"):
                        try:
                            cmd_conf = max(0.0, min(1.0, float(parts[1])))
                        except ValueError:
                            print("invalid confidence command")
                            continue
                        if parts[0] == "h":
                            confidence_hand = cmd_conf
                            print(f"\nhand confidence set to {confidence_hand:.2f}", flush=True)
                        elif parts[0] == "f":
                            confidence_foot = cmd_conf
                            print(f"\nfoot confidence set to {confidence_foot:.2f}", flush=True)
                        else:
                            now_ms = int(time.time() * 1000)
                            delta_ms = now_ms - last_event_ms
                            last_event_ms = now_ms
                            seq += 1
                            await websocket.send(build_packet(seq, "rest", 1.0, "r", delta_ms))
                            print(f"\nsent #{seq}: rest conf=1.00 dt={delta_ms}ms", flush=True)
                    else:
                        print("\ncommand format: :h 0.85 / :f 0.80 / :r 1.0", flush=True)
                    continue
                if ch == "\x1b":
                    command_buffer = ""
                    print("\ncommand canceled", flush=True)
                    continue
                command_buffer += ch
                continue

            lower = ch.lower()
            if lower == ":":
                command_buffer = ""
                print("\ncommand mode", flush=True)
                continue
            if lower == "q":
                print("\nquit", flush=True)
                break
            if lower == "+":
                confidence_hand = min(1.0, confidence_hand + 0.05)
                confidence_foot = min(1.0, confidence_foot + 0.05)
                print(f"\nconf hand={confidence_hand:.2f} foot={confidence_foot:.2f}", flush=True)
                continue
            if lower == "-":
                confidence_hand = max(0.0, confidence_hand - 0.05)
                confidence_foot = max(0.0, confidence_foot - 0.05)
                print(f"\nconf hand={confidence_hand:.2f} foot={confidence_foot:.2f}", flush=True)
                continue
            if lower == "c":
                print(f"\nconf hand={confidence_hand:.2f} foot={confidence_foot:.2f}", flush=True)
                continue

            label = ""
            confidence = 1.0
            if lower == "h":
                label = "hand"
                confidence = confidence_hand
            elif lower == "f":
                label = "foot"
                confidence = confidence_foot
            elif lower == "r":
                label = "rest"
                confidence = 1.0
            else:
                continue

            now_ms = int(time.time() * 1000)
            delta_ms = now_ms - last_event_ms
            last_event_ms = now_ms

            seq += 1
            await websocket.send(build_packet(seq, label, confidence, lower, delta_ms))
            print(f"\nsent #{seq}: {label} conf={confidence:.2f} dt={delta_ms}ms", flush=True)


async def main() -> None:
    print(f"MI keyboard websocket server at ws://{HOST}:{PORT}")
    print("Start game in MI + Offline mode, then use hotkeys h/f/r.")

    async def handler(websocket):
        print("Game connected.")
        try:
            receiver_task = asyncio.create_task(_game_receiver(websocket))
            await keyboard_sender(websocket)
            receiver_task.cancel()
        except websockets.exceptions.ConnectionClosed:
            print("Game disconnected.")

    async with websockets.serve(handler, HOST, PORT, max_size=2**20):
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
