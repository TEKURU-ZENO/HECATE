import os

class BaseSettings:
    def __init__(self):
        self.kafka_bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.digital_twin_service_url = os.environ.get(
            "DIGITAL_TWIN_SERVICE_URL", "http://localhost:8006/api/v1/twin/simulate"
        )
