import time
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple


@dataclass
class DetectionPayload:
    timestamp: float
    db: float
    is_danger: bool
    danger_type: str
    label: str
    confidence: float
    latency_ms: float
    direction: str = "UNKNOWN"
    is_looming: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class UserPreferenceProfile:
    def __init__(
        self,
        profile_name: Optional[str] = None,
        name: Optional[str] = None,
        display_title: str = "",
        w_time: float = 0.40,
        w_ari: float = 0.45,
        w_uncertainty: Optional[float] = None,
        w_uncert: Optional[float] = None,
        tau_cutoff: float = 9.0,
    ):
        self.profile_name = profile_name or name or "BALANCED"
        self.display_title = display_title or f"{self.profile_name} Profile"
        self.w_time = float(w_time)
        self.w_ari = float(w_ari)
        uncert = w_uncertainty if w_uncertainty is not None else (w_uncert if w_uncert is not None else 0.15)
        self.w_uncertainty = float(uncert)
        self.tau_cutoff = float(tau_cutoff)
        self.normalize()

    def normalize(self) -> "UserPreferenceProfile":
        total = self.w_time + self.w_ari + self.w_uncertainty
        if total > 0 and abs(total - 1.0) > 1e-4:
            self.w_time = round(self.w_time / total, 3)
            self.w_ari = round(self.w_ari / total, 3)
            self.w_uncertainty = round(1.0 - self.w_time - self.w_ari, 3)
        return self

    @property
    def name(self) -> str:
        return self.profile_name

    @name.setter
    def name(self, val: str):
        self.profile_name = val

    @property
    def w_uncert(self) -> float:
        return self.w_uncertainty

    @w_uncert.setter
    def w_uncert(self, val: float):
        self.w_uncertainty = val

    @classmethod
    def safe_first(cls) -> "UserPreferenceProfile":
        return cls(
            profile_name="SAFE_FIRST",
            display_title="Safe-First (Maximum Acoustic Protection)",
            w_time=0.15,
            w_ari=0.70,
            w_uncertainty=0.15,
            tau_cutoff=8.5,
        )

    @classmethod
    def balanced(cls) -> "UserPreferenceProfile":
        return cls(
            profile_name="BALANCED",
            display_title="Balanced (Recommended)",
            w_time=0.40,
            w_ari=0.45,
            w_uncertainty=0.15,
            tau_cutoff=9.0,
        )

    @classmethod
    def fast_first(cls) -> "UserPreferenceProfile":
        return cls(
            profile_name="FAST_FIRST",
            display_title="Fast-First (Time Optimized)",
            w_time=0.75,
            w_ari=0.15,
            w_uncertainty=0.10,
            tau_cutoff=9.8,
        )

    @classmethod
    def get_presets(cls) -> Dict[str, "UserPreferenceProfile"]:
        return {
            "SAFE_FIRST": cls.safe_first(),
            "BALANCED": cls.balanced(),
            "FAST_FIRST": cls.fast_first(),
        }

    @classmethod
    def get_preset(cls, profile_name: str) -> "UserPreferenceProfile":
        key = profile_name.upper().replace("-", "_").replace(" ", "_")
        return cls.get_presets().get(key, cls.balanced())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_name": self.profile_name,
            "name": self.name,
            "display_title": self.display_title,
            "w_time": self.w_time,
            "w_ari": self.w_ari,
            "w_uncertainty": self.w_uncertainty,
            "w_uncert": self.w_uncert,
            "tau_cutoff": self.tau_cutoff,
        }


@dataclass
class RouteSegment:
    segment_id: str
    name: str
    length_m: float
    avg_db: float
    truck_freq: float
    horn_freq: float
    is_blackspot: bool
    ari_score: float
    uncertainty: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RouteScenario:
    def __init__(
        self,
        scenario_id: Optional[str] = None,
        route_id: Optional[str] = None,
        title: Optional[str] = None,
        name: Optional[str] = None,
        route_summary: str = "",
        duration_min: Optional[float] = None,
        time_min: Optional[float] = None,
        distance_km: float = 0.0,
        avg_ari: Optional[float] = None,
        ari_mean: Optional[float] = None,
        ari_p90: float = 0.0,
        composite_ari_eval: float = 0.0,
        uncertainty_penalty: Optional[float] = None,
        uncertainty: Optional[float] = None,
        truck_exposure_count: Optional[int] = None,
        truck_density: Optional[float] = None,
        mcda_cost: Optional[float] = None,
        mcda_score: Optional[float] = None,
        is_pareto_optimal: bool = True,
        is_recommended: bool = False,
        xai_explanation: str = "",
        segments: Optional[List[RouteSegment]] = None,
        waypoints: Optional[List[Tuple[float, float]]] = None,
        n_trips: int = 0,
        ari_max: Optional[float] = None,
    ):
        self.scenario_id = scenario_id or route_id or "ROUTE_A"
        self.title = title or name or self.scenario_id
        self.route_summary = route_summary
        t_val = duration_min if duration_min is not None else (time_min if time_min is not None else 0.0)
        self.duration_min = float(t_val)
        self.distance_km = float(distance_km)

        ari_val = avg_ari if avg_ari is not None else (ari_mean if ari_mean is not None else 0.0)
        self.avg_ari = float(ari_val)
        self.ari_p90 = float(ari_p90)
        self.composite_ari_eval = float(composite_ari_eval if composite_ari_eval > 0 else (0.6 * self.avg_ari + 0.4 * self.ari_p90))

        u_val = uncertainty_penalty if uncertainty_penalty is not None else (uncertainty if uncertainty is not None else 0.0)
        self.uncertainty_penalty = float(u_val)

        if truck_exposure_count is not None:
            self.truck_exposure_count = int(truck_exposure_count)
        elif truck_density is not None:
            self.truck_exposure_count = int(round(truck_density * 10))
        else:
            self.truck_exposure_count = 0

        cost_val = mcda_cost if mcda_cost is not None else (mcda_score if mcda_score is not None else 0.0)
        self.mcda_cost = float(cost_val)

        self.is_pareto_optimal = bool(is_pareto_optimal)
        self.is_recommended = bool(is_recommended)
        self.xai_explanation = xai_explanation
        self.segments = segments or []
        self.waypoints = waypoints or []
        self.n_trips = int(n_trips)
        self._explicit_ari_max = ari_max

    @property
    def route_id(self) -> str:
        return self.scenario_id

    @route_id.setter
    def route_id(self, val: str):
        self.scenario_id = val

    @property
    def name(self) -> str:
        return self.title

    @name.setter
    def name(self, val: str):
        self.title = val

    @property
    def time_min(self) -> float:
        return self.duration_min

    @time_min.setter
    def time_min(self, val: float):
        self.duration_min = val

    @property
    def ari_mean(self) -> float:
        return self.avg_ari

    @ari_mean.setter
    def ari_mean(self, val: float):
        self.avg_ari = val

    @property
    def uncertainty(self) -> float:
        return self.uncertainty_penalty

    @uncertainty.setter
    def uncertainty(self, val: float):
        self.uncertainty_penalty = val

    @property
    def truck_density(self) -> float:
        return float(self.truck_exposure_count) / 10.0

    @truck_density.setter
    def truck_density(self, val: float):
        self.truck_exposure_count = int(round(val * 10))

    @property
    def ari_max(self) -> float:
        if self._explicit_ari_max is not None:
            return self._explicit_ari_max
        if self.segments:
            return max(s.ari_score for s in self.segments)
        return max(self.ari_p90, self.avg_ari)

    @ari_max.setter
    def ari_max(self, val: float):
        self._explicit_ari_max = val

    @property
    def mcda_score(self) -> float:
        return self.mcda_cost

    @mcda_score.setter
    def mcda_score(self, val: float):
        self.mcda_cost = val

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario_id": self.scenario_id,
            "route_id": self.route_id,
            "title": self.title,
            "name": self.name,
            "route_summary": self.route_summary,
            "duration_min": self.duration_min,
            "time_min": self.time_min,
            "distance_km": self.distance_km,
            "avg_ari": self.avg_ari,
            "ari_mean": self.ari_mean,
            "ari_p90": self.ari_p90,
            "composite_ari_eval": self.composite_ari_eval,
            "uncertainty_penalty": self.uncertainty_penalty,
            "uncertainty": self.uncertainty,
            "truck_exposure_count": self.truck_exposure_count,
            "truck_density": self.truck_density,
            "mcda_cost": self.mcda_cost,
            "mcda_score": self.mcda_score,
            "is_pareto_optimal": self.is_pareto_optimal,
            "is_recommended": self.is_recommended,
            "xai_explanation": self.xai_explanation,
            "segments": [s.to_dict() for s in self.segments],
            "waypoints": self.waypoints,
            "n_trips": self.n_trips,
            "ari_max": self.ari_max,
        }


class DecisionResponse:
    def __init__(
        self,
        origin: str = "",
        destination: str = "",
        timestamp: float = 0.0,
        active_profile: Optional[UserPreferenceProfile] = None,
        scenarios: Optional[List[RouteScenario]] = None,
        recommended_scenario_id: str = "",
        pareto_count: int = 0,
        pareto_scenarios: Optional[List[RouteScenario]] = None,
        recommended_scenario: Optional[RouteScenario] = None,
        tradeoff_metadata: Optional[Dict[str, Any]] = None,
        all_scenarios: Optional[List[RouteScenario]] = None,
        filtered_out_scenarios: Optional[List[Dict[str, Any]]] = None,
    ):
        self.origin = origin
        self.destination = destination
        self.timestamp = timestamp or time.time()
        self.active_profile = active_profile
        self.scenarios = scenarios or all_scenarios or []
        if pareto_scenarios and not self.scenarios:
            self.scenarios = pareto_scenarios

        if recommended_scenario:
            self.recommended_scenario_id = recommended_scenario.scenario_id
        else:
            self.recommended_scenario_id = recommended_scenario_id

        self.pareto_count = pareto_count or len([s for s in self.scenarios if s.is_pareto_optimal])
        self.tradeoff_metadata = tradeoff_metadata or {}
        self.filtered_out_scenarios = filtered_out_scenarios or []

    @property
    def pareto_scenarios(self) -> List[RouteScenario]:
        return [s for s in self.scenarios if s.is_pareto_optimal]

    @property
    def recommended_scenario(self) -> Optional[RouteScenario]:
        return self.get_recommended_scenario()

    @property
    def all_scenarios(self) -> List[RouteScenario]:
        return self.scenarios

    def get_recommended_scenario(self) -> Optional[RouteScenario]:
        for s in self.scenarios:
            if s.scenario_id == self.recommended_scenario_id or s.is_recommended:
                return s
        return self.scenarios[0] if self.scenarios else None

    def get_tradeoff_matrix(self) -> List[Dict[str, Any]]:
        rows = []
        for s in self.scenarios:
            status = "RECOMMENDED" if s.is_recommended else ("Pareto Optimal" if s.is_pareto_optimal else "Dominated")
            rows.append({
                "Scenario ID": s.scenario_id,
                "Route Title": s.title,
                "Travel Time": f"{s.duration_min:.0f} min",
                "Distance": f"{s.distance_km:.1f} km",
                "Acoustic Risk (ARI)": f"{s.avg_ari:.1f} / 10",
                "Peak Risk (P90)": f"{s.ari_p90:.1f} / 10",
                "Truck Exposure": f"{s.truck_exposure_count} events",
                "Uncertainty (U)": f"{s.uncertainty_penalty:.2f}",
                "MCDA Cost Score": f"{s.mcda_cost:.3f}",
                "Status": status,
            })
        return rows

    def to_dict(self) -> Dict[str, Any]:
        return {
            "origin": self.origin,
            "destination": self.destination,
            "timestamp": self.timestamp,
            "active_profile": self.active_profile.to_dict() if self.active_profile else None,
            "scenarios": [s.to_dict() for s in self.scenarios],
            "recommended_scenario_id": self.recommended_scenario_id,
            "pareto_count": self.pareto_count,
            "pareto_scenarios": [s.to_dict() for s in self.pareto_scenarios],
            "recommended_scenario": self.recommended_scenario.to_dict() if self.recommended_scenario else None,
            "tradeoff_metadata": self.tradeoff_metadata,
            "all_scenarios": [s.to_dict() for s in self.scenarios],
            "filtered_out_scenarios": self.filtered_out_scenarios,
        }