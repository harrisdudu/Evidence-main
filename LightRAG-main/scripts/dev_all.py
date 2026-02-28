import argparse
import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path


def _which(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise SystemExit(f"未找到命令：{name}。请先确保它已安装且在 PATH 中。")
    return path


def _terminate_process(proc: subprocess.Popen) -> None:
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except Exception:
        return


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--api-port", type=int, default=9621)
    parser.add_argument("--web-port", type=int, default=5173)
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    webui_dir = repo_root / "lightrag_webui"

    _which("uv")
    _which("bun")

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    backend_cmd = [
        "uv",
        "run",
        "lightrag-server",
        "--host",
        args.host,
        "--port",
        str(args.api_port),
    ]
    frontend_cmd = [
        "bun",
        "run",
        "dev",
        "--",
        "--host",
        args.host,
        "--port",
        str(args.web_port),
    ]

    backend = subprocess.Popen(
        backend_cmd,
        cwd=str(repo_root),
        env=os.environ.copy(),
        creationflags=creationflags,
    )
    frontend = subprocess.Popen(
        frontend_cmd,
        cwd=str(webui_dir),
        env=os.environ.copy(),
        creationflags=creationflags,
    )

    procs = [backend, frontend]

    def shutdown() -> None:
        for p in procs:
            _terminate_process(p)
        for p in procs:
            try:
                p.wait(timeout=8)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    def handle_signal(_signum, _frame) -> None:
        shutdown()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, handle_signal)

    while True:
        codes = [p.poll() for p in procs]
        if any(code is not None for code in codes):
            shutdown()
            return next((code for code in codes if code is not None), 0) or 0
        try:
            signal.pause()
        except AttributeError:
            try:
                backend.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass
            try:
                frontend.wait(timeout=0.5)
            except subprocess.TimeoutExpired:
                pass


if __name__ == "__main__":
    sys.exit(main())

