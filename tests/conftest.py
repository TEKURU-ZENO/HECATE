import pytest
@pytest.fixture(scope="session")
def global_config():
    return {"env": "test", "broker": "localhost:9092"}