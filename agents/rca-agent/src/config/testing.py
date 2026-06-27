from .base import BaseSettings

class TestingSettings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9094"
