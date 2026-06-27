import os

env = os.environ.get("HECATE_ENV", "dev").lower()

if env == "prod" or env == "production":
    from .prod import ProdSettings as Settings
elif env == "staging":
    from .staging import StagingSettings as Settings
elif env == "testing" or env == "test":
    from .testing import TestingSettings as Settings
else:
    from .dev import DevSettings as Settings

settings = Settings()
