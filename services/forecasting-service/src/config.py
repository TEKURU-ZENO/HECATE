import os


class Settings:
    def __init__(self):
        self.host = os.environ.get("FORECASTING_HOST", "0.0.0.0")
        self.port = int(os.environ.get("FORECASTING_PORT", 8003))
        self.scrape_interval = 5  # default telemetry cycle duration in seconds
