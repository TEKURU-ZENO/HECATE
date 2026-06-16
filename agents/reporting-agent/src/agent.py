import asyncio

import structlog

from .config import Settings

log = structlog.get_logger()


class ReportingAgent:
    """HECATE Reporting Agent — Generates formatted summaries and notifications for incidents core logic class."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._running = False

    async def run(self) -> None:
        self._running = True
        log.info("agent.running", agent_class="ReportingAgent")
        while self._running:
            await asyncio.sleep(10)

    async def stop(self) -> None:
        self._running = False
        log.info("agent.stopped")

    async def generate_report(self, incident_id: str) -> str:
        """Builds incident MTTR summary report templates."""
        log.info("generating.incident_report", incident_id=incident_id)
        return f"Report for {incident_id}"
