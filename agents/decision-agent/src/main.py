"""HECATE decision-agent entrypoint."""
import asyncio
import structlog
from .agent import DecisionAgent
from .config import settings

log = structlog.get_logger()

async def main() -> None:
    log.info("decision-agent.starting", version="0.1.0")
    agent = DecisionAgent(settings)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())