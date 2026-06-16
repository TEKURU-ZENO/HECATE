"""HECATE rca-agent entrypoint."""

import asyncio

import structlog

from .agent import RcaAgent
from .config import settings

log = structlog.get_logger()


async def main() -> None:
    log.info("rca-agent.starting", version="0.1.0")
    agent = RcaAgent(settings)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
