"""HECATE reporting-agent entrypoint."""
import asyncio

import structlog

from .agent import ReportingAgent
from .config import settings

log = structlog.get_logger()

async def main() -> None:
    log.info("reporting-agent.starting", version="0.1.0")
    agent = ReportingAgent(settings)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())
