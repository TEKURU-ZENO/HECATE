import os


class BaseSettings:
    def __init__(self):
        self.neo4j_uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
        self.neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        self.neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")
        
        # "neo4j" or "mock"
        self.graph_mode = os.environ.get("HECATE_GRAPH_MODE", "mock")
        self.port = int(os.environ.get("GRAPH_SERVICE_PORT", "8005"))
        self.host = "0.0.0.0"
        
        self.archive_days = int(os.environ.get("GRAPH_ARCHIVE_DAYS", "30"))



