"""HECATE recommendation-agent entrypoint."""
import asyncio

import structlog

from .agent import RecommendationAgent
from .config import settings

log = structlog.get_logger()

async def main() -> None:
    log.info("recommendation-agent.starting", version="0.1.0")
    agent = RecommendationAgent(settings)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
