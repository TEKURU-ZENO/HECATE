import os
import yaml
from typing import Any, Dict

def load_profile(profile_name: str) -> Dict[str, Any]:
    # Resolve the path to scripts/profiles/<profile_name>.yaml
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    profile_path = os.path.join(base_dir, "scripts", "profiles", f"{profile_name}.yaml")
    
    if not os.path.exists(profile_path):
        # Fallback to current directory profile
        profile_path = os.path.join(os.getcwd(), "scripts", "profiles", f"{profile_name}.yaml")
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Evaluation profile '{profile_name}' not found at: {profile_path}")
            
    with open(profile_path, "r") as f:
        config = yaml.safe_load(f)
    return config
