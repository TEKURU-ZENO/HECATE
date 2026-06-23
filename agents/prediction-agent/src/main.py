import asyncio

import structlog

from .agent import PredictionAgent
from .config import Settings

# Configure logging
structlog.configure()
log = structlog.get_logger()


async def main():
    settings = Settings()
    log.info("prediction_agent.starting")
    agent = PredictionAgent(settings)
    try:
        await agent.run()
    except KeyboardInterrupt:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
