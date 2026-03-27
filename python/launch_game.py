import argparse
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path


def _resolve_godot_binary(explicit_path: str | None) -> str:
    candidates: list[str] = []

    if explicit_path:
        candidates.append(explicit_path)

    env_bin = os.environ.get("GODOT_BIN", "").strip()
    if env_bin:
        candidates.append(env_bin)

    candidates.extend(
        [
            "godot4",
            "godot",
            "/Applications/Godot.app/Contents/MacOS/Godot",
            "/Applications/Godot_mono.app/Contents/MacOS/Godot",
        ]
    )

    for item in candidates:
        resolved = shutil.which(item) if not Path(item).exists() else item
        if resolved and Path(resolved).exists():
            return str(Path(resolved))

    raise FileNotFoundError(
        "Cannot find Godot executable. Please pass --godot-bin or set GODOT_BIN."
    )


def _spawn_process(cmd: list[str], cwd: Path, label: str) -> subprocess.Popen:
    print(f"[launch] starting {label}: {' '.join(cmd)}")
    return subprocess.Popen(cmd, cwd=str(cwd))


def _terminate_processes(processes: list[subprocess.Popen]) -> None:
    for proc in processes:
        if proc.poll() is None:
            proc.terminate()

    deadline = time.time() + 2.0
    while time.time() < deadline:
        alive = [p for p in processes if p.poll() is None]
        if not alive:
            return
        time.sleep(0.05)

    for proc in processes:
        if proc.poll() is None:
            proc.kill()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Launch Godot game from Python with optional MI helper services."
    )
    parser.add_argument("--godot-bin", default=None, help="Path to Godot executable")
    parser.add_argument(
        "--project-path",
        default=None,
        help="Path to Godot project root (default: parent of this python folder)",
    )
    parser.add_argument(
        "--with-mi-keyboard",
        action="store_true",
        help="Start MI offline keyboard sender server (ws://127.0.0.1:8766)",
    )
    parser.add_argument(
        "--with-mi-replay",
        action="store_true",
        help="Start MI offline replay server (ws://127.0.0.1:8766)",
    )
    parser.add_argument(
        "--with-mi-online-stub",
        action="store_true",
        help="Start MI online stub server (ws://127.0.0.1:8767)",
    )
    parser.add_argument(
        "--with-realtime",
        action="store_true",
        help="Start gameplay realtime server (ws://127.0.0.1:8765)",
    )
    args = parser.parse_args()

    python_dir = Path(__file__).resolve().parent
    project_root = (
        Path(args.project_path).resolve()
        if args.project_path
        else python_dir.parent.resolve()
    )

    godot_bin = _resolve_godot_binary(args.godot_bin)

    processes: list[subprocess.Popen] = []

    try:
        if args.with_mi_keyboard and args.with_mi_replay:
            raise ValueError("Use either --with-mi-keyboard or --with-mi-replay, not both.")

        if args.with_mi_keyboard:
            processes.append(
                _spawn_process(
                    [sys.executable, str(python_dir / "mi_keyboard_sender.py")],
                    project_root,
                    "MI keyboard sender",
                )
            )

        if args.with_mi_replay:
            processes.append(
                _spawn_process(
                    [sys.executable, str(python_dir / "mi_offline_replay_server.py")],
                    project_root,
                    "MI replay server",
                )
            )

        if args.with_mi_online_stub:
            processes.append(
                _spawn_process(
                    [sys.executable, str(python_dir / "mi_online_stub_server.py")],
                    project_root,
                    "MI online stub",
                )
            )

        if args.with_realtime:
            processes.append(
                _spawn_process(
                    [sys.executable, str(python_dir / "realtime_server.py")],
                    project_root,
                    "realtime gameplay server",
                )
            )

        game_proc = _spawn_process(
            [godot_bin, "--path", str(project_root)],
            project_root,
            "Godot game",
        )
        processes.append(game_proc)

        def _signal_handler(_sig, _frame):
            print("\n[launch] stopping all processes...")
            _terminate_processes(processes)
            raise SystemExit(0)

        signal.signal(signal.SIGINT, _signal_handler)
        signal.signal(signal.SIGTERM, _signal_handler)

        exit_code = game_proc.wait()
        print(f"[launch] game exited with code {exit_code}")

    finally:
        _terminate_processes(processes)


if __name__ == "__main__":
    main()
