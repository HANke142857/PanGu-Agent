"""
IDMAS LangGraph Worker 入口。

职责：
  - 连接 RabbitMQ，消费 task.created 队列
  - 为每个任务运行 Master Graph 并回写结果（见 services.TaskProcessor）
  - 优雅关闭（SIGINT/SIGTERM）

启动方式::

    cd D:\\PanGu-Agent
    PYTHONPATH=. python -m idmas.worker

水平扩展：直接多开 Worker 实例；触发条件——队列积压 > 20。
"""

from __future__ import annotations

import asyncio
import logging
import signal

from idmas.config.settings import get_settings
from idmas.infrastructure.mq.consumer import run_worker


def _configure_logging() -> None:
    settings = get_settings()
    logging.basicConfig(
        level=settings.APP_LOG_LEVEL.value,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


async def _main() -> None:
    _configure_logging()
    log = logging.getLogger("idmas.worker")

    worker_task = asyncio.create_task(run_worker())

    loop = asyncio.get_running_loop()
    stop = asyncio.Event()

    def _request_stop() -> None:
        log.info("收到停止信号，准备优雅关闭…")
        stop.set()

    # Windows 的 ProactorEventLoop 不支持 add_signal_handler，降级为 KeyboardInterrupt。
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            pass

    done, _ = await asyncio.wait(
        {worker_task, asyncio.create_task(stop.wait())},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if not worker_task.done():
        worker_task.cancel()
        try:
            await worker_task
        except asyncio.CancelledError:
            pass
    log.info("Worker 已退出")


def main() -> None:
    try:
        asyncio.run(_main())
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
