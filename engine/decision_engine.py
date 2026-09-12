import math
from typing import List, Dict, Any, Optional, Tuple
from data_contract import RouteScenario, UserPreferenceProfile, DecisionResponse


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
                pareto_list.append(sc_i)

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

        cost = (profile.w_time * t_norm) + (profile.w_ari * ari_norm) + (profile.w_uncert * u_norm)
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

        if recommended.route_id == fastest.route_id:
            text = (
                f"{recommended.name} is the optimal choice under '{profile.name}' preferences: "
                f"Fastest travel time ({recommended.time_min:.1f} min) with an acoustic risk level of "
                f"ARI={rec_ari:.1f}/10."
            )
        elif ari_reduction_pct > 0:
            text = (
                f"{recommended.name} is recommended: Takes {delta_time:.1f} min longer (+{time_ratio_pct}%) "
                f"to reduce acoustic risk by {ari_reduction_pct}% (ARI from {fast_ari:.1f} to {rec_ari:.1f}/10)"
            )
            if recommended.truck_density < fastest.truck_density:
                text += f" and avoids high truck density areas ({recommended.truck_density*100:.0f}% vs {fastest.truck_density*100:.0f}%)."
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
            "weights": {"w_time": profile.w_time, "w_ari": profile.w_ari, "w_uncert": profile.w_uncert},
        }

        return text, metadata

    def evaluate(
        self,
        scenarios: List[RouteScenario],
        profile: Optional[UserPreferenceProfile] = None,
    ) -> DecisionResponse:
        if profile is None:
            profile = UserPreferenceProfile.balanced()
        profile.normalize()

        for sc in scenarios:
            if sc.uncertainty <= 0:
                sc.uncertainty = self.compute_bayesian_uncertainty(sc.n_trips)
            sc.is_recommended = False

        valid_scenarios, filtered_out = self.filter_hard_safety_constraints(scenarios)
        if not valid_scenarios:
            return DecisionResponse(
                pareto_scenarios=[],
                recommended_scenario=None,
                tradeoff_metadata={"error": "All route candidates violated the hard safety constraint."},
                all_scenarios=scenarios,
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
            pareto_scenarios=pareto_scenarios,
            recommended_scenario=best,
            tradeoff_metadata=tradeoff_meta,
            all_scenarios=scenarios,
            filtered_out_scenarios=filtered_out,
        )

    @staticmethod
    def get_benchmark_scenarios() -> List[RouteScenario]:
        return [
            RouteScenario(
                route_id="ROUTE_A",
                name="Route A (Highway - Fastest)",
                time_min=20.0,
                distance_km=12.5,
                ari_mean=8.5,
                ari_p90=9.2,
                uncertainty=0.08,
                truck_density=0.85,
                ari_max=8.9,
                n_trips=150,
            ),
            RouteScenario(
                route_id="ROUTE_B",
                name="Route B (SafeRoute - Recommended)",
                time_min=27.0,
                distance_km=13.8,
                ari_mean=1.8,
                ari_p90=2.4,
                uncertainty=0.10,
                truck_density=0.15,
                ari_max=3.5,
                n_trips=95,
            ),
            RouteScenario(
                route_id="ROUTE_C",
                name="Route C (Transit & Green Corridor)",
                time_min=38.0,
                distance_km=14.2,
                ari_mean=0.5,
                ari_p90=0.8,
                uncertainty=0.14,
                truck_density=0.05,
                ari_max=1.2,
                n_trips=50,
            ),
            RouteScenario(
                route_id="ROUTE_D",
                name="Route D (Pareto Dominated)",
                time_min=35.0,
                distance_km=15.0,
                ari_mean=8.8,
                ari_p90=9.4,
                uncertainty=0.25,
                truck_density=0.90,
                ari_max=8.9,
                n_trips=15,
            ),
            RouteScenario(
                route_id="ROUTE_E",
                name="Route E (Safety Cutoff Exceeded)",
                time_min=18.0,
                distance_km=11.0,
                ari_mean=7.0,
                ari_p90=9.6,
                uncertainty=0.05,
                truck_density=0.80,
                ari_max=9.8,
                n_trips=200,
            ),
        ]
