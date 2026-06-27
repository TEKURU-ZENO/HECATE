from .base import BaseSettings

class TestingSettings(BaseSettings):
    calibration_alpha: float = 0.1
    database_url: str = "sqlite:///hecate_events.db"
    kafka_bootstrap_servers: str = "localhost:9094"
