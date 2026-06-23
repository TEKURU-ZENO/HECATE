import os


class Settings:
    def __init__(self):
        self.host = os.environ.get("COPILOT_HOST", "0.0.0.0")
        self.port = int(os.environ.get("COPILOT_PORT", 8004))
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.copilot_mode = os.environ.get(
            "HECATE_COPILOT_MODE", "mock" if not self.gemini_api_key else "gemini"
        )
        self.index_refresh_interval = int(os.environ.get("COPILOT_INDEX_REFRESH_INTERVAL", 60))
