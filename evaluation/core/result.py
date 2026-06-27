from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class EvaluationResult:
    metric: str
    value: float
    ci: Optional[List[float]] = None
    baseline_values: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
