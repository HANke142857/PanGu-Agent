"""
统一日志配置 —— 控制台 + 滚动文件。

- 根 logger 写 logs/backend.log（含 uvicorn / 应用 / 访问日志）
- "idmas.frontend" logger 写 logs/frontend.log（前端浏览器运行时回传）

日志目录优先取环境变量 IDMAS_LOG_DIR，否则用项目根下的 logs/。
setup_logging() 幂等，可重复调用。
"""
from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_CONFIGURED = False

# 本文件位于 idmas/infrastructure/observability/，parents[3] 即项目根目录
_PROJECT_ROOT = Path(__file__).resolve().parents[3]

_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
_DATEFMT = "%Y-%m-%d %H:%M:%S"


def log_dir() -> Path:
    d = os.environ.get("IDMAS_LOG_DIR")
    path = Path(d) if d else (_PROJECT_ROOT / "logs")
    path.mkdir(parents=True, exist_ok=True)
    return path


def _coerce_level(level) -> int:
    if isinstance(level, int):
        return level
    name = getattr(level, "value", level)
    if isinstance(name, str):
        return getattr(logging, name.upper(), logging.INFO)
    return logging.INFO


def _rotating(path: Path) -> RotatingFileHandler:
    h = RotatingFileHandler(path, maxBytes=10 * 1024 * 1024, backupCount=5, encoding="utf-8")
    h.setFormatter(logging.Formatter(_FMT, _DATEFMT))
    return h


def setup_logging(level="INFO") -> Path:
    """配置根日志与前端日志，返回日志目录。"""
    global _CONFIGURED
    lvl = _coerce_level(level)
    d = log_dir()

    root = logging.getLogger()
    if not _CONFIGURED:
        root.setLevel(lvl)

        console = logging.StreamHandler()
        console.setFormatter(logging.Formatter(_FMT, _DATEFMT))
        root.addHandler(console)
        root.addHandler(_rotating(d / "backend.log"))

        # 让 uvicorn 的日志也并入根 handler（避免重复输出）
        for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
            lg = logging.getLogger(name)
            lg.handlers.clear()
            lg.propagate = True

        # 前端浏览器日志单独成文件
        fe = logging.getLogger("idmas.frontend")
        fe.setLevel(logging.INFO)
        fe.propagate = False
        fe.addHandler(_rotating(d / "frontend.log"))

        _CONFIGURED = True
        logging.getLogger(__name__).info("日志已初始化，目录: %s", d)
    else:
        root.setLevel(lvl)
    return d
