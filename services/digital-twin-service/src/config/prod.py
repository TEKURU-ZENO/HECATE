import os
from .base import BaseSettings

class ProdSettings(BaseSettings):
    calibration_alpha: float = 0.05
    database_url: str = os.environ.get("HECATE_PROD_DB_URL", "postgresql://hecate_prod:hecate_secure_pass@postgres-prod:5432/hecate")
    kafka_bootstrap_servers: str = os.environ.get("HECATE_PROD_KAFKA_SERVERS", "kafka-prod:9092")
