"""HECATE remediation-agent entrypoint."""
import asyncio
import structlog
from .agent import RemediationAgent
from .config import settings

log = structlog.get_logger()

async def main() -> None:
    log.info("remediation-agent.starting", version="0.1.0")
    agent = RemediationAgent(settings)
    await agent.run()

if __name__ == "__main__":
    asyncio.run(main())