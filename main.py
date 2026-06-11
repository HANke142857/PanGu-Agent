#!/usr/bin/env python3
"""
IDMAS 一键启动器
================
在项目根目录运行本文件，即可同时拉起后端(FastAPI/uvicorn) 与 前端(Vite)，
并把两个进程的输出实时写入 logs/ 下的日志文件，方便排错。

用法示例
--------
    python main.py                  # 后端(:8080) + 前端(:5173) 一起启动
    python main.py --no-backend     # 只起前端（后端已在 Docker 里跑时用这个）
    python main.py --no-frontend    # 只起后端
    python main.py --mock           # 前端用内置假数据，不连后端
    python main.py --backend-port 8081 --frontend-port 5174

日志
----
    logs/backend.log    后端 uvicorn / 应用 / 访问日志（也由后端自身滚动写入）
    logs/frontend.log   前端 Vite dev server 输出 + 浏览器运行时错误回传
    logs/launcher.log   启动器自身事件

说明
----
* 前端默认连真实后端(VITE_USE_MOCK=false)，IDMAS_LOG_DIR 指向 logs/。
* 首次启动会自动在 frontend/ 执行 npm install。
* 本地起后端需先：pip install -r idmas/requirements.txt
* 按 Ctrl+C 一并优雅退出。
"""
from __future__ import annotations

import argparse
import datetime as _dt
import os
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
FRONTEND_DIR = ROOT / "frontend"
LOG_DIR = Path(os.environ.get("IDMAS_LOG_DIR", str(ROOT / "logs")))
LOG_DIR.mkdir(parents=True, exist_ok=True)

# Windows 控制台默认 GBK；子进程输出含 ➜/emoji 等字符时写 stdout 会 UnicodeEncodeError。
# 保留控制台原编码、仅把无法编码的字符替换掉，避免镜像线程崩溃。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")  # type: ignore[union-attr]
    except (AttributeError, ValueError):
        pass

_procs: list[subprocess.Popen] = []
_threads: list[threading.Thread] = []


def _stamp() -> str:
    return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg: str) -> None:
    line = f"[idmas] {msg}"
    print(f"\033[36m{line}\033[0m", flush=True)
    with open(LOG_DIR / "launcher.log", "a", encoding="utf-8") as f:
        f.write(f"{_stamp()} {line}\n")


def err(msg: str) -> None:
    line = f"[idmas] {msg}"
    print(f"\033[31m{line}\033[0m", flush=True)
    with open(LOG_DIR / "launcher.log", "a", encoding="utf-8") as f:
        f.write(f"{_stamp()} ERROR {line}\n")


def _npm() -> str:
    return "npm.cmd" if os.name == "nt" else "npm"


def _pump(proc: subprocess.Popen, log_path: Path, tag: str) -> threading.Thread:
    """把子进程输出实时写到 控制台 + 日志文件。"""
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"\n===== {tag} 启动 @ {_stamp()} =====\n")

    def run() -> None:
        assert proc.stdout is not None
        with open(log_path, "a", encoding="utf-8") as fh:
            for raw in iter(proc.stdout.readline, ""):
                if not raw:
                    break
                line = f"{tag} | {raw}"
                # 控制台可能是 GBK，子进程输出含 ➜/中文等字符会触发 UnicodeEncodeError；
                # 退而以当前编码 replace 写入，绝不让镜像线程因个别字符崩溃。
                try:
                    sys.stdout.write(line)
                except UnicodeEncodeError:
                    enc = getattr(sys.stdout, "encoding", None) or "utf-8"
                    sys.stdout.buffer.write(line.encode(enc, "replace"))
                sys.stdout.flush()
                fh.write(raw)
                fh.flush()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    _threads.append(t)
    return t


def start_backend(host: str, port: int) -> subprocess.Popen:
    log(f"启动后端 · uvicorn http://{host}:{port} (reload)  → logs/backend.log")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    env["IDMAS_LOG_DIR"] = str(LOG_DIR)
    env["PYTHONUNBUFFERED"] = "1"
    cmd = [
        sys.executable, "-m", "uvicorn", "idmas.main:app",
        "--host", host, "--port", str(port), "--reload",
    ]
    p = subprocess.Popen(
        cmd, cwd=str(ROOT), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    _pump(p, LOG_DIR / "backend.log", "BACKEND")
    return p


def ensure_frontend_deps() -> None:
    if not (FRONTEND_DIR / "node_modules").exists():
        log("未检测到 frontend/node_modules，执行 npm install（首次较慢）…")
        subprocess.run([_npm(), "install"], cwd=str(FRONTEND_DIR), check=True)


def start_frontend(port: int, api_base: str, use_mock: bool) -> subprocess.Popen:
    ensure_frontend_deps()
    log(f"启动前端 · Vite http://localhost:{port} (mock={'on' if use_mock else 'off'})  → logs/frontend.log")
    env = os.environ.copy()
    env["VITE_USE_MOCK"] = "true" if use_mock else "false"
    env["IDMAS_API_BASE"] = api_base
    cmd = [_npm(), "run", "dev", "--", "--port", str(port), "--host"]
    p = subprocess.Popen(
        cmd, cwd=str(FRONTEND_DIR), env=env,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
    )
    _pump(p, LOG_DIR / "frontend.log", "FRONTEND")
    return p


def _terminate_all() -> None:
    for p in _procs:
        if p.poll() is None:
            try:
                p.terminate() if os.name == "nt" else p.send_signal(signal.SIGINT)
            except Exception:
                pass
    deadline = time.time() + 8
    for p in _procs:
        try:
            p.wait(timeout=max(0.1, deadline - time.time()))
        except Exception:
            try:
                p.kill()
            except Exception:
                pass


def main() -> int:
    ap = argparse.ArgumentParser(description="IDMAS 一键启动器")
    ap.add_argument("--no-backend", action="store_true", help="不启动后端（后端在 Docker 中运行时使用）")
    ap.add_argument("--no-frontend", action="store_true", help="不启动前端")
    ap.add_argument("--backend-port", type=int, default=8080)
    ap.add_argument("--frontend-port", type=int, default=5173)
    ap.add_argument("--host", default="0.0.0.0", help="后端绑定地址")
    ap.add_argument("--mock", action="store_true", help="前端使用内置假数据（不连后端）")
    args = ap.parse_args()

    if args.no_backend and args.no_frontend:
        err("--no-backend 与 --no-frontend 不能同时使用。")
        return 2

    api_base = f"http://localhost:{args.backend_port}"
    log(f"日志目录：{LOG_DIR}")

    try:
        if not args.no_backend:
            _procs.append(start_backend(args.host, args.backend_port))
            time.sleep(1.5)
        if not args.no_frontend:
            _procs.append(start_frontend(args.frontend_port, api_base, args.mock))

        log(f"已启动。前端 http://localhost:{args.frontend_port}   后端文档 {api_base}/docs")
        log("按 Ctrl+C 停止。")

        while True:
            for p in _procs:
                code = p.poll()
                if code is not None:
                    err(f"子进程 (pid={p.pid}) 退出 code={code}，停止其余服务…")
                    return code or 0
            time.sleep(0.5)
    except FileNotFoundError as e:
        err(f"找不到可执行文件：{e}（请确认已安装 Node.js/npm 与 Python 依赖）")
        return 1
    except KeyboardInterrupt:
        log("收到 Ctrl+C，正在停止…")
        return 0
    finally:
        _terminate_all()
        log("已停止全部服务。")


if __name__ == "__main__":
    raise SystemExit(main())
