from .base import BaseSettings

class DevSettings(BaseSettings):
    def __init__(self):
        super().__init__()
        if hasattr(self, "kafka_bootstrap_servers"):
            self.kafka_bootstrap_servers = "localhost:9094"
