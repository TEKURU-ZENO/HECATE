import pytest
from src.agent import RcaAgent
from src.config import Settings


@pytest.fixture
def settings():
    return Settings(kafka_bootstrap_servers="localhost:9092")


@pytest.fixture
def agent(settings):
    return RcaAgent(settings)


class TestRcaAgent:
    def test_initialization(self, agent):
        assert agent is not None
        assert agent._running is False
