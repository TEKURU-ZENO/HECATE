from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9094"
    log_level: str = "INFO"
    prometheus_url: str = "http://localhost:9090"
    scrape_interval_seconds: float = 2.0
    target_service: str = "payment-service"
    target_namespace: str = "hecate-system"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()