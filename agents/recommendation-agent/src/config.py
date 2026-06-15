from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    kafka_bootstrap_servers: str = "localhost:9094"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        extra = "ignore"

settings = Settings()
