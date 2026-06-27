from dataclasses import dataclass

@dataclass
class Experiment:
    id: str
    scenario: str
    profile: str
    seed: int
    repetitions: int
