from dataclasses import dataclass, field
from typing import Dict, Any, List
from evaluation.core.experiment import Experiment

@dataclass
class EvaluationContext:
    experiment: Experiment
    telemetry: List[Dict[str, Any]] = field(default_factory=list)
    ground_truth: Dict[str, Any] = field(default_factory=dict)
    predictions: List[Dict[str, Any]] = field(default_factory=list)
    services: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
