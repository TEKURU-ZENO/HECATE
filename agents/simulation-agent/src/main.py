"""HECATE simulation-agent entrypoint."""

import asyncio

import structlog

from .agent import SimulationAgent
from .config import Settings

log = structlog.get_logger()


async def main() -> None:
    log.info("simulation-agent.starting", version="0.1.0")
    settings = Settings()
    agent = SimulationAgent(settings)
    await agent.run()


if __name__ == "__main__":
    asyncio.run(main())
