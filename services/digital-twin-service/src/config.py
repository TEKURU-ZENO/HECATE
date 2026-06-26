import os

class Settings:
    title: str = "HECATE Digital Twin Service"
    version: str = "2.0.0"
    port: int = 8006
    # Accuracy degradation or noise variables if needed
    calibration_alpha: float = 0.1

settings = Settings()
