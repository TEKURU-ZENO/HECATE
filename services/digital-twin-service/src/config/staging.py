from .base import BaseSettings

class StagingSettings(BaseSettings):
    calibration_alpha: float = 0.1
    database_url: str = "postgresql://hecate_user:hecate_pass@postgres-staging:5432/hecate"
    kafka_bootstrap_servers: str = "kafka-staging:9092"
