from .base import BaseSettings

class DevSettings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9094"
