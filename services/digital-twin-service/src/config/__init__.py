import os

env = os.environ.get("HECATE_ENV", "dev").lower()

if env == "prod" or env == "production":
    from .prod import ProdSettings
    settings = ProdSettings()
elif env == "staging":
    from .staging import StagingSettings
    settings = StagingSettings()
elif env == "testing" or env == "test":
    from .testing import TestingSettings
    settings = TestingSettings()
else:
    from .dev import DevSettings
    settings = DevSettings()
