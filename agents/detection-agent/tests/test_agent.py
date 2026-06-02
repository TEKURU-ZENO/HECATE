import pytest
from src.agent import DetectionAgent
from src.config import Settings

@pytest.fixture
def settings():
    return Settings(kafka_bootstrap_servers="localhost:9092")

@pytest.fixture
def agent(settings):
    return DetectionAgent(settings)

class TestDetectionAgent:
    def test_initialization(self, agent):
        assert agent is not None
        assert agent._running is False