"""
UrbanVibe - Acoustic-Aware Decision Intelligence Engine (MCDA Core)
Module tính toán ra quyết định lộ trình Pre-Trip an toàn cho người khiếm thính.
Áp dụng:
- Ràng buộc an toàn cứng (Hard Safety Constraint: ARI_max <= tau_cutoff)
- Lọc tập tối ưu Pareto (Pareto Frontier Filter)
- Hàm chi phí đa tiêu chí (Weighted-Sum MCDA with Length-Weighted ARI_P90)
- Phạt độ bất định Bayesian (Bayesian Uncertainty Penalty)
- Diễn giải đánh đổi minh bạch (Explainable AI - XAI)
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from data_contract import RouteScenario, UserPreferenceProfile, DecisionResponse


class DecisionEngine:
    """
    Lõi thuật toán Decision Intelligence cho quy trình hỗ trợ ra quyết định Pre-Trip.
    """

    def __init__(
        self,
        tau_cutoff: float = 9.0,
        lambda_ari: float = 0.6,
        sigma_0_sq: float = 1.0,
    ):
        """
        Khởi tạo Decision Engine.
        :param tau_cutoff: Ngưỡng cắt an toàn cứng (mặc định 9.0/10)
        :param lambda_ari: Trọng số kết hợp ARI_eval = lambda * ARI_mean + (1 - lambda) * ARI_p90
        :param sigma_0_sq: Hệ số độ bất định Bayesian ban đầu
        """
        self.tau_cutoff = tau_cutoff
        self.lambda_ari = lambda_ari
        self.sigma_0_sq = sigma_0_sq

    def compute_bayesian_uncertainty(self, n_trips: int) -> float:
        """
        Tính toán phạt độ bất định Bayesian:
        U(s) = sigma_0^2 / sqrt(N_trips + 1), kẹp trong [0.0, 1.0].
        """
        n = max(0, int(n_trips))
        u = self.sigma_0_sq / math.sqrt(n + 1)
        return min(1.0, max(0.0, round(u, 4)))

    def compute_ari_eval(self, scenario: RouteScenario) -> float:
        """
        Tính chỉ số rủi ro âm thanh kết hợp:
        ARI_eval = lambda * ARI_mean + (1 - lambda) * ARI_p90
        """
        eval_val = (self.lambda_ari * scenario.ari_mean) + ((1.0 - self.lambda_ari) * scenario.ari_p90)
        return round(eval_val, 3)

    def filter_hard_safety_constraints(
        self, scenarios: List[RouteScenario], tau_cutoff: Optional[float] = None
    ) -> Tuple[List[RouteScenario], List[Dict[str, Any]]]:
        """
        Bước 1: Ràng buộc an toàn cứng (Hard Safety Filter).
        Loại bỏ mọi tuyến đường có ARI_max > tau_cutoff.
        Nếu ARI_max == 0, lấy max(ARI_p90, ARI_mean) làm ước lượng đỉnh.
        """
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
                    "reason": f"Vi phạm ràng buộc an toàn cứng: ARI đỉnh ({peak_ari:.1f}) > ngưỡng an toàn ({cutoff:.1f})",
                })
            else:
                valid_scenarios.append(sc)

        return valid_scenarios, filtered_out

    def filter_pareto_frontier(self, scenarios: List[RouteScenario]) -> List[RouteScenario]:
        """
        Bước 2: Lọc tập phương án Pareto (Pareto Frontier Filter).
        Xét 3 tiêu chí cần cực tiểu hóa:
        - Thời gian T: sc.time_min
        - Rủi ro kết hợp ARI_eval: compute_ari_eval(sc)
        - Độ bất định Bayesian U: sc.uncertainty
        Tuyến A thống trị Tuyến B nếu A <= B trên cả 3 tiêu chí và A < B ở ít nhất 1 tiêu chí.
        Tập Pareto là tập các tuyến không bị tuyến nào khác thống trị.
        """
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
                # Kiểm tra sc_j có thống trị sc_i hay không
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
        """
        Bước 3: Hàm chi phí đa tiêu chí (Weighted-Sum MCDA Cost):
        C(P) = w_time * (T / T_max) + w_ari * (ARI_eval / 10.0) + w_uncert * (U / U_max)
        """
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
        """
        Bước 4: Module Diễn giải Đánh đổi Minh bạch (Explainable AI - XAI).
        So sánh định lượng giữa tuyến đề xuất và tuyến nhanh nhất (Fastest Route).
        """
        if not all_candidates:
            return "Không có tuyến đường phù hợp để đánh giá.", {}

        fastest = min(all_candidates, key=lambda s: s.time_min)
        rec_ari = self.compute_ari_eval(recommended)
        fast_ari = self.compute_ari_eval(fastest)

        delta_time = round(recommended.time_min - fastest.time_min, 1)
        time_ratio_pct = round((delta_time / fastest.time_min) * 100, 1) if fastest.time_min > 0 else 0.0

        delta_ari = round(fast_ari - rec_ari, 2)
        ari_reduction_pct = round((delta_ari / fast_ari) * 100, 1) if fast_ari > 0 else 0.0

        # Phân tích theo ngữ cảnh
        if recommended.route_id == fastest.route_id:
            text = (
                f"{recommended.name} là phương án tối ưu toàn diện theo sở thích '{profile.name}': "
                f"Thời gian nhanh nhất ({recommended.time_min:.1f} phút) với mức rủi ro kiểm soát ở mức "
                f"ARI={rec_ari:.1f}/10."
            )
        elif ari_reduction_pct > 0:
            text = (
                f"{recommended.name} được đề xuất: Chấp nhận tốn thêm {delta_time:.1f} phút (+{time_ratio_pct}%) "
                f"để giảm {ari_reduction_pct}% rủi ro âm thanh (ARI từ {fast_ari:.1f} xuống {rec_ari:.1f}/10)"
            )
            if recommended.truck_density < fastest.truck_density:
                text += f" và giảm mật độ xe tải từ {fastest.truck_density*100:.0f}% xuống {recommended.truck_density*100:.0f}%."
            else:
                text += "."
        else:
            text = (
                f"{recommended.name} được đề xuất cân bằng theo hồ sơ '{profile.name}': "
                f"Thời gian {recommended.time_min:.1f} phút, ARI={rec_ari:.1f}/10, độ bất định U={recommended.uncertainty:.2f}."
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
        """
        Quy trình xử lý toàn diện Pre-Trip Decision Intelligence:
        1. Cập nhật độ bất định Bayesian (nếu chưa có).
        2. Lọc ràng buộc an toàn cứng (Hard Safety Constraint).
        3. Lọc tập phương án tối ưu Pareto.
        4. Tính điểm chi phí MCDA cho từng phương án.
        5. Chọn phương án tối ưu P* = argmin C(P).
        6. Sinh diễn giải XAI và cấu trúc DecisionResponse.
        """
        if profile is None:
            profile = UserPreferenceProfile.balanced()
        profile.normalize()

        # Cập nhật độ bất định Bayesian nếu chưa có
        for sc in scenarios:
            if sc.uncertainty <= 0:
                sc.uncertainty = self.compute_bayesian_uncertainty(sc.n_trips)
            sc.is_recommended = False

        # Bước 1: Ràng buộc an toàn cứng
        valid_scenarios, filtered_out = self.filter_hard_safety_constraints(scenarios)

        if not valid_scenarios:
            return DecisionResponse(
                pareto_scenarios=[],
                recommended_scenario=None,
                tradeoff_metadata={"error": "Toàn bộ kịch bản bị loại do vượt ngưỡng rủi ro an toàn cứng."},
                all_scenarios=scenarios,
                filtered_out_scenarios=filtered_out,
            )

        # Bước 2: Lọc tập Pareto Frontier
        pareto_scenarios = self.filter_pareto_frontier(valid_scenarios)

        # Bước 3: Tính điểm MCDA cho tất cả các kịch bản hợp lệ
        t_max = max(s.time_min for s in valid_scenarios) if valid_scenarios else 1.0
        u_max = max(s.uncertainty for s in valid_scenarios) if valid_scenarios else 1.0

        for sc in valid_scenarios:
            sc.mcda_score = self.compute_mcda_cost(sc, profile, t_max=t_max, u_max=u_max)

        # Bước 4: Lựa chọn kịch bản tối ưu trong tập Pareto
        # (Nếu có nhiều kịch bản trong Pareto, chọn kịch bản có mcda_score nhỏ nhất)
        candidates_to_pick = pareto_scenarios if pareto_scenarios else valid_scenarios
        best_scenario = min(candidates_to_pick, key=lambda s: s.mcda_score)
        best_scenario.is_recommended = True

        # Bước 5: Sinh giải thích XAI
        xai_text, tradeoff_meta = self.generate_xai_explanation(
            recommended=best_scenario,
            all_candidates=valid_scenarios,
            profile=profile,
        )
        best_scenario.xai_explanation = xai_text

        return DecisionResponse(
            pareto_scenarios=pareto_scenarios,
            recommended_scenario=best_scenario,
            tradeoff_metadata=tradeoff_meta,
            all_scenarios=scenarios,
            filtered_out_scenarios=filtered_out,
        )

    @staticmethod
    def get_benchmark_scenarios() -> List[RouteScenario]:
        """
        Tạo bộ kịch bản giao thông mẫu chuẩn xác tại TP.HCM theo đặc tả V2.5:
        - Tuyến A: Trục Đại Lộ (Nhanh nhất - Nhiều xe tải, rủi ro âm thanh cao)
        - Tuyến B: SafeRoute (Đường gom / Hành lang xanh - Giảm rủi ro lớn, tốn thêm ít phút)
        - Tuyến C: Chuyển tiếp Metro & Phương tiện công cộng (An toàn nhất)
        - Tuyến D: Tuyến bị thống trị hoàn toàn (Chậm hơn và rủi ro cao hơn để test Pareto)
        - Tuyến E: Tuyến vi phạm ràng buộc an toàn cứng (ARI_max > 9.0 để test Hard Safety)
        """
        return [
            RouteScenario(
                route_id="ROUTE_A",
                name="Tuyến A (Trục Đại Lộ - Nhanh nhất)",
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
                name="Tuyến B (SafeRoute - Khuyên dùng)",
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
                name="Tuyến C (Chuyển tiếp Metro & Đường Gom)",
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
                name="Tuyến D (Tuyến Bị Thống Trị Pareto)",
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
                name="Tuyến E (Vi Phạm Ràng Buộc Cắt Rủi Ro)",
                time_min=18.0,
                distance_km=11.0,
                ari_mean=7.0,
                ari_p90=9.6,
                uncertainty=0.05,
                truck_density=0.80,
                ari_max=9.8,  # > tau_cutoff 9.0
                n_trips=200,
            ),
        ]
