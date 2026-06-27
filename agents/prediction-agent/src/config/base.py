import os


class BaseSettings:
    def __init__(self):
        self.kafka_bootstrap_servers = os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
        self.forecasting_service_url = os.environ.get(
            "FORECASTING_SERVICE_URL", "http://localhost:8003/api/v1/forecast"
        )
