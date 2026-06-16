import structlog

log = structlog.get_logger()


class CoreService:
    """Business logic helper for policy-service"""

    def __init__(self) -> None:
        pass

    def do_work(self) -> bool:
        log.info("service.performing_action")
        return True
