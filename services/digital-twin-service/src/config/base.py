class BaseSettings:
    title: str = "HECATE Digital Twin Service"
    version: str = "2.0.0"
    port: int = 8006
    calibration_alpha: float = 0.1
    database_url: str = "sqlite:///hecate.db"
    kafka_bootstrap_servers: str = "localhost:9092"
