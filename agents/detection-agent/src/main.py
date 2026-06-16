"""HECATE detection-agent entrypoint."""

import asyncio

import structlog

from .agent import DetectionAgent
from .config import settings

log = structlog.get_logger()


async def main() -> None:
    log.info("detection-agent.starting", version="0.1.0")
    agent = DetectionAgent(settings)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
