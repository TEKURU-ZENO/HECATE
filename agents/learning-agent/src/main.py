"""HECATE learning-agent entrypoint."""
import asyncio

import structlog

from .agent import LearningAgent
from .config import settings

log = structlog.get_logger()

async def main() -> None:
    log.info("learning-agent.starting", version="0.1.0")
    agent = LearningAgent(settings)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
