"""HECATE monitoring-agent entrypoint."""

import asyncio

import structlog

from .agent import MonitoringAgent
from .config import settings

log = structlog.get_logger()


async def main() -> None:
    log.info("monitoring-agent.starting", version="0.1.0")
    agent = MonitoringAgent(settings)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
