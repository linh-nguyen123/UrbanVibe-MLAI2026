import math
import time
from typing import List, Dict, Any, Optional, Tuple
from data_contract import (
    RouteScenario,
    RouteSegment,
    UserPreferenceProfile,
    DecisionResponse,
)


def calculate_haversine_distance(coord1: List[float], coord2: List[float]) -> float:
    lon1, lat1 = coord1
    lon2, lat2 = coord2
    radius_km = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return radius_km * c


def generate_arc_waypoints(
    start: List[float], end: List[float], num_points: int = 12, offset_ratio: float = 0.0
) -> List[Tuple[float, float]]:
    lon1, lat1 = start
    lon2, lat2 = end
    points = []
    for i in range(num_points):
        fraction = float(i) / float(num_points - 1)
        base_lon = lon1 + fraction * (lon2 - lon1)
        base_lat = lat1 + fraction * (lat2 - lat1)
        perp_offset = math.sin(fraction * math.pi) * offset_ratio
        pt_lon = round(base_lon - perp_offset * (lat2 - lat1), 5)
        pt_lat = round(base_lat + perp_offset * (lon2 - lon1), 5)
        points.append((pt_lat, pt_lon))
    return points


class DecisionEngine:
    def __init__(
        self,
        tau_cutoff: float = 9.0,
        lambda_ari: float = 0.6,
        sigma_0_sq: float = 1.0,
    ):
        self.tau_cutoff = tau_cutoff
        self.lambda_ari = lambda_ari
        self.sigma_0_sq = sigma_0_sq

    def compute_bayesian_uncertainty(self, n_trips: int) -> float:
        n = max(0, int(n_trips))
        u = self.sigma_0_sq / math.sqrt(n + 1)
        return min(1.0, max(0.0, round(u, 4)))

    def compute_ari_eval(self, scenario: RouteScenario) -> float:
        val = (self.lambda_ari * scenario.ari_mean) + ((1.0 - self.lambda_ari) * scenario.ari_p90)
        return round(val, 3)

    def filter_hard_safety_constraints(
        self, scenarios: List[RouteScenario], tau_cutoff: Optional[float] = None
    ) -> Tuple[List[RouteScenario], List[Dict[str, Any]]]:
        cutoff = self.tau_cutoff if tau_cutoff is None else tau_cutoff
        valid_scenarios: List[RouteScenario] = []
        filtered_out: List[Dict[str, Any]] = []

        for sc in scenarios:
            peak_ari = sc.ari_max if sc.ari_max > 0 else max(sc.ari_p90, sc.ari_mean)
            if peak_ari > cutoff:
                filtered_out.append({
                    "route_id": sc.route_id,
                    "name": sc.name,
                    "peak_ari": peak_ari,
                    "cutoff": cutoff,
                    "reason": f"Hard safety constraint violation: peak ARI ({peak_ari:.1f}) exceeds cutoff ({cutoff:.1f})",
                })
            else:
                valid_scenarios.append(sc)

        return valid_scenarios, filtered_out

    def filter_pareto_frontier(self, scenarios: List[RouteScenario]) -> List[RouteScenario]:
        if not scenarios:
            return []

        criteria = []
        for sc in scenarios:
            ari_eval = self.compute_ari_eval(sc)
            uncert = sc.uncertainty if sc.uncertainty > 0 else self.compute_bayesian_uncertainty(sc.n_trips)
            criteria.append((sc.time_min, ari_eval, uncert, sc))

        pareto_list: List[RouteScenario] = []
        for i, (t_i, ari_i, u_i, sc_i) in enumerate(criteria):
            is_dominated = False
            for j, (t_j, ari_j, u_j, sc_j) in enumerate(criteria):
                if i == j:
                    continue
                if t_j <= t_i and ari_j <= ari_i and u_j <= u_i:
                    if t_j < t_i or ari_j < ari_i or u_j < u_i:
                        is_dominated = True
                        break
            if not is_dominated:
                sc_i.is_pareto_optimal = True
                pareto_list.append(sc_i)
            else:
                sc_i.is_pareto_optimal = False

        return pareto_list

    def compute_mcda_cost(
        self,
        scenario: RouteScenario,
        profile: UserPreferenceProfile,
        t_max: float,
        u_max: float = 1.0,
    ) -> float:
        ari_eval = self.compute_ari_eval(scenario)
        uncert = scenario.uncertainty if scenario.uncertainty > 0 else self.compute_bayesian_uncertainty(scenario.n_trips)

        t_norm = (scenario.time_min / t_max) if t_max > 0 else 0.0
        ari_norm = min(1.0, max(0.0, ari_eval / 10.0))
        u_norm = min(1.0, max(0.0, uncert / u_max)) if u_max > 0 else 0.0

        cost = (profile.w_time * t_norm) + (profile.w_ari * ari_norm) + (profile.w_uncertainty * u_norm)
        return round(cost, 4)

    def generate_xai_explanation(
        self,
        recommended: RouteScenario,
        all_candidates: List[RouteScenario],
        profile: UserPreferenceProfile,
    ) -> Tuple[str, Dict[str, Any]]:
        if not all_candidates:
            return "No valid route scenarios available for evaluation.", {}

        fastest = min(all_candidates, key=lambda s: s.time_min)
        rec_ari = self.compute_ari_eval(recommended)
        fast_ari = self.compute_ari_eval(fastest)

        delta_time = round(recommended.time_min - fastest.time_min, 1)
        time_ratio_pct = round((delta_time / fastest.time_min) * 100, 1) if fastest.time_min > 0 else 0.0

        delta_ari = round(fast_ari - rec_ari, 2)
        ari_reduction_pct = round((delta_ari / fast_ari) * 100, 1) if fast_ari > 0 else 0.0

        if recommended.scenario_id == fastest.scenario_id:
            text = (
                f"{recommended.name} is the optimal choice under '{profile.name}' preferences: "
                f"Fastest travel time ({recommended.time_min:.1f} min) with acoustic risk controlled at "
                f"ARI={rec_ari:.1f}/10."
            )
        elif ari_reduction_pct > 0:
            text = (
                f"{recommended.name} is recommended: Takes {delta_time:.1f} min longer (+{time_ratio_pct}%) "
                f"to reduce acoustic risk by {ari_reduction_pct}% (ARI from {fast_ari:.1f} down to {rec_ari:.1f}/10)"
            )
            if recommended.truck_density < fastest.truck_density:
                text += f" and avoids high truck density corridors ({recommended.truck_density*100:.0f}% vs {fastest.truck_density*100:.0f}%)."
            else:
                text += "."
        else:
            text = (
                f"{recommended.name} is selected under '{profile.name}' preferences: "
                f"Time: {recommended.time_min:.1f} min, ARI: {rec_ari:.1f}/10, uncertainty: {recommended.uncertainty:.2f}."
            )

        metadata = {
            "fastest_route_id": fastest.route_id,
            "fastest_time_min": fastest.time_min,
            "fastest_ari_eval": fast_ari,
            "recommended_route_id": recommended.route_id,
            "recommended_time_min": recommended.time_min,
            "recommended_ari_eval": rec_ari,
            "delta_time_min": delta_time,
            "time_increase_pct": time_ratio_pct,
            "ari_reduction_score": delta_ari,
            "ari_reduction_pct": ari_reduction_pct,
            "profile_used": profile.name,
            "weights": {
                "w_time": profile.w_time,
                "w_ari": profile.w_ari,
                "w_uncertainty": profile.w_uncertainty,
            },
        }

        return text, metadata

    def evaluate(
        self,
        scenarios: List[RouteScenario],
        profile: Optional[UserPreferenceProfile] = None,
        origin: str = "Origin",
        destination: str = "Destination",
    ) -> DecisionResponse:
        if profile is None:
            profile = UserPreferenceProfile.balanced()
        profile.normalize()

        for sc in scenarios:
            if sc.uncertainty <= 0:
                sc.uncertainty = self.compute_bayesian_uncertainty(sc.n_trips)
            sc.is_recommended = False

        valid_scenarios, filtered_out = self.filter_hard_safety_constraints(scenarios, tau_cutoff=self.tau_cutoff)
        if not valid_scenarios:
            return DecisionResponse(
                origin=origin,
                destination=destination,
                timestamp=time.time(),
                active_profile=profile,
                scenarios=scenarios,
                recommended_scenario_id="",
                pareto_count=0,
                tradeoff_metadata={"error": "All route candidates violated the hard safety constraint."},
                filtered_out_scenarios=filtered_out,
            )

        pareto_scenarios = self.filter_pareto_frontier(valid_scenarios)
        t_max = max(s.time_min for s in valid_scenarios) if valid_scenarios else 1.0
        u_max = max(s.uncertainty for s in valid_scenarios) if valid_scenarios else 1.0

        for sc in valid_scenarios:
            sc.mcda_score = self.compute_mcda_cost(sc, profile, t_max=t_max, u_max=u_max)

        candidates = pareto_scenarios if pareto_scenarios else valid_scenarios
        best = min(candidates, key=lambda s: s.mcda_score)
        best.is_recommended = True

        xai_text, tradeoff_meta = self.generate_xai_explanation(
            recommended=best,
            all_candidates=valid_scenarios,
            profile=profile,
        )
        best.xai_explanation = xai_text

        return DecisionResponse(
            origin=origin,
            destination=destination,
            timestamp=time.time(),
            active_profile=profile,
            scenarios=scenarios,
            recommended_scenario_id=best.scenario_id,
            pareto_count=len(pareto_scenarios),
            tradeoff_metadata=tradeoff_meta,
            filtered_out_scenarios=filtered_out,
        )

    def plan_trip(
        self,
        origin: str,
        destination: str,
        profile: Optional[UserPreferenceProfile] = None,
        orig_coords: Optional[List[float]] = None,
        dest_coords: Optional[List[float]] = None,
    ) -> DecisionResponse:
        if profile is None:
            profile = UserPreferenceProfile.balanced()

        if orig_coords and dest_coords:
            dist_direct = calculate_haversine_distance(orig_coords, dest_coords)
            p_start = orig_coords
            p_end = dest_coords
        else:
            dist_direct = 9.2
            p_start = [106.6578, 10.7725]
            p_end = [106.7722, 10.8507]

        dist_direct = max(1.8, dist_direct)
        dist_a = max(2.4, round(dist_direct * 1.22, 1))
        dist_b = max(2.7, round(dist_direct * 1.34, 1))
        dist_c = max(3.1, round(dist_direct * 1.56, 1))

        if dist_direct < 35.0:
            avg_speed = 25.0
            truck_mult = 1.8
        elif dist_direct < 150.0:
            avg_speed = 50.0
            truck_mult = 0.6
        else:
            avg_speed = 65.0
            truck_mult = 0.3

        dur_a = max(6.0, round((dist_a / (avg_speed * 1.15)) * 60.0))
        dur_b = max(8.0, round((dist_b / avg_speed) * 60.0))
        dur_c = max(12.0, round((dist_c / (avg_speed * 0.75)) * 60.0))

        wp_a = generate_arc_waypoints(p_start, p_end, 14, offset_ratio=0.08)
        wp_b = generate_arc_waypoints(p_start, p_end, 14, offset_ratio=-0.12)
        wp_c = generate_arc_waypoints(p_start, p_end, 14, offset_ratio=0.22)

        scenarios = [
            RouteScenario(
                scenario_id="SCENARIO_A",
                title="Route A (Highway Arterial - Fastest)",
                route_summary="Highway Express / Heavy Truck Corridor",
                duration_min=dur_a,
                distance_km=dist_a,
                avg_ari=8.2,
                ari_p90=9.1,
                uncertainty_penalty=0.08,
                truck_exposure_count=max(2, int(round(dist_a * truck_mult))),
                waypoints=wp_a,
                n_trips=180,
                ari_max=8.9,
            ),
            RouteScenario(
                scenario_id="SCENARIO_B",
                title="Route B (SafeRoute - Recommended)",
                route_summary="Service Roads & Acoustic Buffer Corridor",
                duration_min=dur_b,
                distance_km=dist_b,
                avg_ari=1.8,
                ari_p90=2.4,
                uncertainty_penalty=0.10,
                truck_exposure_count=max(0, int(round(dist_b * truck_mult * 0.15))),
                waypoints=wp_b,
                n_trips=120,
                ari_max=3.5,
            ),
            RouteScenario(
                scenario_id="SCENARIO_C",
                title="Route C (Transit & Green Belt)",
                route_summary="Urban Green Belt / Dedicated Mobility Lane",
                duration_min=dur_c,
                distance_km=dist_c,
                avg_ari=0.6,
                ari_p90=0.9,
                uncertainty_penalty=0.14,
                truck_exposure_count=0,
                waypoints=wp_c,
                n_trips=65,
                ari_max=1.2,
            ),
        ]

        return self.evaluate(
            scenarios=scenarios,
            profile=profile,
            origin=origin,
            destination=destination,
        )

    @staticmethod
    def get_benchmark_scenarios() -> List[RouteScenario]:
        return [
            RouteScenario(
                scenario_id="ROUTE_A",
                title="Route A (Highway - Fastest)",
                duration_min=20.0,
                distance_km=12.5,
                avg_ari=8.5,
                ari_p90=9.2,
                uncertainty_penalty=0.08,
                truck_exposure_count=8,
                ari_max=8.9,
                n_trips=150,
            ),
            RouteScenario(
                scenario_id="ROUTE_B",
                title="Route B (SafeRoute - Recommended)",
                duration_min=27.0,
                distance_km=13.8,
                avg_ari=1.8,
                ari_p90=2.4,
                uncertainty_penalty=0.10,
                truck_exposure_count=2,
                ari_max=3.5,
                n_trips=95,
            ),
            RouteScenario(
                scenario_id="ROUTE_C",
                title="Route C (Transit & Green Corridor)",
                duration_min=38.0,
                distance_km=14.2,
                avg_ari=0.5,
                ari_p90=0.8,
                uncertainty_penalty=0.14,
                truck_exposure_count=0,
                ari_max=1.2,
                n_trips=50,
            ),
            RouteScenario(
                scenario_id="ROUTE_D",
                title="Route D (Pareto Dominated)",
                duration_min=35.0,
                distance_km=15.0,
                avg_ari=8.8,
                ari_p90=9.4,
                uncertainty_penalty=0.25,
                truck_exposure_count=9,
                ari_max=8.9,
                n_trips=15,
            ),
            RouteScenario(
                scenario_id="ROUTE_E",
                title="Route E (Safety Cutoff Exceeded)",
                duration_min=18.0,
                distance_km=11.0,
                avg_ari=7.0,
                ari_p90=9.6,
                uncertainty_penalty=0.05,
                truck_exposure_count=8,
                ari_max=9.8,
                n_trips=200,
            ),
        ]
