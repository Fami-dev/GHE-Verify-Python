#!/usr/bin/env python3
"""Run bot and API server together."""

import os
import signal
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _start_process(script_name: str) -> subprocess.Popen:
    script_path = os.path.join(BASE_DIR, script_name)
    return subprocess.Popen([sys.executable, script_path], cwd=BASE_DIR)


def _stop_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    proc.terminate()
    try:
        proc.wait(timeout=8)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    processes = {
        "bot": _start_process("bot.py"),
        "api": _start_process("api_server.py"),
    }

    print("[run_all] Started bot.py and api_server.py")
    print(f"[run_all] bot pid={processes['bot'].pid}, api pid={processes['api'].pid}")

    exit_code = 0
    try:
        while True:
            for name, proc in processes.items():
                code = proc.poll()
                if code is not None:
                    print(f"[run_all] {name} exited with code {code}. Stopping all services.")
                    exit_code = code if code != 0 else exit_code
                    return exit_code
            time.sleep(1)
    except KeyboardInterrupt:
        print("[run_all] Interrupted by user. Stopping services...")
        return exit_code
    finally:
        for proc in processes.values():
            _stop_process(proc)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
