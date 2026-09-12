from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

@dataclass
class DetectionPayload:
    timestamp: float
    db: float
    is_danger: bool
    danger_type: str
    label: str
    confidence: float
    latency_ms: float

    def to_dict(self):
        return asdict(self)


@dataclass
class RouteScenario:
    route_id: str
    name: str
    time_min: float
    distance_km: float
    ari_mean: float
    ari_p90: float
    uncertainty: float
    truck_density: float
    xai_explanation: str = ""
    is_recommended: bool = False
    ari_max: float = 0.0
    n_trips: int = 0
    mcda_score: float = 0.0

    @property
    def duration_min(self) -> float:
        return self.time_min

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserPreferenceProfile:
    name: str = "BALANCED"
    w_time: float = 0.4
    w_ari: float = 0.4
    w_uncert: float = 0.2

    def __post_init__(self):
        self.normalize()

    def normalize(self) -> "UserPreferenceProfile":
        total = self.w_time + self.w_ari + self.w_uncert
        if total > 0:
            self.w_time = round(self.w_time / total, 4)
            self.w_ari = round(self.w_ari / total, 4)
            self.w_uncert = round(1.0 - self.w_time - self.w_ari, 4)
        else:
            self.w_time, self.w_ari, self.w_uncert = 0.3333, 0.3333, 0.3334
        return self

    @classmethod
    def safe_first(cls) -> "UserPreferenceProfile":
        return cls(name="SAFE_FIRST", w_time=0.10, w_ari=0.70, w_uncert=0.20)

    @classmethod
    def balanced(cls) -> "UserPreferenceProfile":
        return cls(name="BALANCED", w_time=0.40, w_ari=0.40, w_uncert=0.20)

    @classmethod
    def fast_first(cls) -> "UserPreferenceProfile":
        return cls(name="FAST_FIRST", w_time=0.70, w_ari=0.20, w_uncert=0.10)

    @classmethod
    def get_preset(cls, profile_name: str) -> "UserPreferenceProfile":
        key = profile_name.upper().replace("-", "_").replace(" ", "_")
        presets = {
            "SAFE_FIRST": cls.safe_first(),
            "BALANCED": cls.balanced(),
            "FAST_FIRST": cls.fast_first(),
        }
        return presets.get(key, cls.balanced())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class DecisionResponse:
    pareto_scenarios: List[RouteScenario]
    recommended_scenario: Optional[RouteScenario]
    tradeoff_metadata: Dict[str, Any]
    all_scenarios: List[RouteScenario] = field(default_factory=list)
    filtered_out_scenarios: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "pareto_scenarios": [s.to_dict() for s in self.pareto_scenarios],
            "recommended_scenario": self.recommended_scenario.to_dict() if self.recommended_scenario else None,
            "tradeoff_metadata": self.tradeoff_metadata,
            "all_scenarios": [s.to_dict() for s in self.all_scenarios],
            "filtered_out_scenarios": self.filtered_out_scenarios,
        }