# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Mock Engine for Frontend Development & Independent UI Testing
Cung cấp dữ liệu giả lập chuẩn theo `data_contract.py` cho:
1. Pre-Trip Decision Intelligence (Ma trận đánh đổi Trade-Off Matrix & XAI)
2. On-Trip Edge-AI Safeguard (Luồng sự kiện âm thanh thời gian thực & Looming detector)
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn import từ thư mục gốc
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import random
import time
from typing import Optional, List

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
from data_contract import (
    DetectionPayload,
    UserPreferenceProfile,
    RouteSegment,
    RouteScenario,
    DecisionResponse
)


# ============================================================================
# 1. MOCK ON-TRIP REAL-TIME AUDIO EVENTS (GIẢ LẬP SỰ KIỆN ÂM THANH TRÊN ĐƯỜNG)
# ============================================================================

def generate_mock_payload(force_danger_type: Optional[str] = None) -> DetectionPayload:
    """
    Giả lập một khung dữ liệu âm thanh từ hệ thống Edge-AI.
    Có hỗ trợ tham số `force_danger_type` để test thủ công trên giao diện.
    """
    now = time.time()
    
    # 1. Chế độ ép kiểu cảnh báo (dùng khi bấm nút test trên giao diện)
    if force_danger_type == "LOOMING_TRUCK":
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(92.0, 102.0), 1),
            is_danger=True,
            danger_type="TRUCK_APPROACH",
            label="Heavy truck / Air horn (Looming hazard)",
            confidence=round(random.uniform(0.92, 0.98), 2),
            latency_ms=round(random.uniform(16.0, 24.0), 1),
            direction="RIGHT",
            is_looming=True
        )
    elif force_danger_type == "VEHICLE_HORN":
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(78.0, 86.0), 1),
            is_danger=True,
            danger_type="VEHICLE_HORN",
            label="Motorbike horn / Car horn",
            confidence=round(random.uniform(0.82, 0.94), 2),
            latency_ms=round(random.uniform(18.0, 28.0), 1),
            direction="LEFT",
            is_looming=False
        )
    elif force_danger_type == "EMERGENCY_SIREN":
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(88.0, 96.0), 1),
            is_danger=True,
            danger_type="EMERGENCY_SIREN",
            label="Ambulance / Fire engine siren",
            confidence=round(random.uniform(0.90, 0.99), 2),
            latency_ms=round(random.uniform(20.0, 30.0), 1),
            direction="CENTER",
            is_looming=False
        )
    elif force_danger_type == "SAFE":
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(45.0, 62.0), 1),
            is_danger=False,
            danger_type="SAFE",
            label="Urban ambience / Speech",
            confidence=round(random.uniform(0.85, 0.95), 2),
            latency_ms=round(random.uniform(14.0, 20.0), 1),
            direction="UNKNOWN",
            is_looming=False
        )

    # 2. Chế độ ngẫu nhiên tự nhiên (Random stream)
    rand = random.random()
    if rand < 0.70:
        # 70% thời gian: Âm thanh nền an toàn
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(45.0, 65.0), 1),
            is_danger=False,
            danger_type="SAFE",
            label="Urban ambient noise",
            confidence=round(random.uniform(0.80, 0.95), 2),
            latency_ms=round(random.uniform(14.0, 22.0), 1),
            direction="UNKNOWN",
            is_looming=False
        )
    elif rand < 0.85:
        # 15% thời gian: Còi xe máy / ô tô
        direction = random.choice(["LEFT", "RIGHT", "CENTER"])
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(76.0, 85.0), 1),
            is_danger=True,
            danger_type="VEHICLE_HORN",
            label="Vehicle horn, car horn",
            confidence=round(random.uniform(0.78, 0.92), 2),
            latency_ms=round(random.uniform(18.0, 28.0), 1),
            direction=direction,
            is_looming=False
        )
    elif rand < 0.95:
        # 10% thời gian: Xe tải lớn áp sát (Looming hazard)
        direction = random.choice(["LEFT", "RIGHT"])
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(88.0, 98.0), 1),
            is_danger=True,
            danger_type="TRUCK_APPROACH",
            label="Heavy truck / Air horn (Looming)",
            confidence=round(random.uniform(0.88, 0.97), 2),
            latency_ms=round(random.uniform(16.0, 24.0), 1),
            direction=direction,
            is_looming=True
        )
    else:
        # 5% thời gian: Còi xe ưu tiên
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(86.0, 95.0), 1),
            is_danger=True,
            danger_type="EMERGENCY_SIREN",
            label="Emergency vehicle (Ambulance siren)",
            confidence=round(random.uniform(0.89, 0.98), 2),
            latency_ms=round(random.uniform(20.0, 32.0), 1),
            direction="CENTER",
            is_looming=False
        )


# ============================================================================
# 2. MOCK PRE-TRIP DECISION INTELLIGENCE (GIẢ LẬP MA TRẬN ĐÁNH ĐỔI LỘ TRÌNH)
# ============================================================================

def generate_mock_decision_response(
    origin: str = "ĐH Bách Khoa CS1 (Quận 10)",
    destination: str = "Bến xe Miền Đông Mới (TP. Thủ Đức)",
    profile: Optional[UserPreferenceProfile] = None
) -> DecisionResponse:
    """
    Sinh gói phản hồi ra quyết định lộ trình hoàn chỉnh mô phỏng dữ liệu giao thông TP.HCM.
    Tính toán hàm chi phí MCDA C(P) dựa trên profile trọng số của người dùng.
    """
    if profile is None:
        profile = UserPreferenceProfile.get_presets()["BALANCED"]

    # Định nghĩa 3 kịch bản lộ trình chuẩn thực địa
    # Tuyến A: Trục chính Điện Biên Phủ - Xa lộ Hà Nội (Nhanh, nhưng nhiều xe tải và còi hơi)
    scen_a = RouteScenario(
        scenario_id="SCENARIO_A",
        title="Tuyến Nhanh Nhất (Google Maps Baseline)",
        route_summary="Lý Thường Kiệt ➔ Điện Biên Phủ ➔ Cầu Sài Gòn ➔ Xa lộ Hà Nội",
        duration_min=21.0,
        distance_km=9.8,
        avg_ari=8.4,
        ari_p90=9.7,
        composite_ari_eval=0.6 * 8.4 + 0.4 * 9.7,  # 8.92
        uncertainty_penalty=0.08,
        truck_exposure_count=19,
        mcda_cost=0.0,
        is_pareto_optimal=True,
        is_recommended=False,
        xai_explanation=(
            "⚠️ Tuyến nhanh nhất nhưng có mức rủi ro âm thanh rất cao (ARI 8.4/10). "
            "Người lái bị phơi nhiễm 19 lượt xe tải/xe ben hạng nặng và 2 điểm đen giao thông bạo lực âm thanh."
        ),
        waypoints=[(10.772, 106.657), (10.795, 106.710), (10.845, 106.775)]
    )

    # Tuyến B: SafeRoute Khuyên Dùng (Đường gom, tránh trục xe tải lớn, êm ái hơn 77%)
    scen_b = RouteScenario(
        scenario_id="SCENARIO_B",
        title="SafeRoute (Khuyến Nghị Cân Bằng)",
        route_summary="Bắc Hải ➔ Phan Đăng Lưu ➔ Hoàng Hoa Thám ➔ Đường gom Song Hành",
        duration_min=27.0,
        distance_km=10.9,
        avg_ari=1.9,
        ari_p90=3.1,
        composite_ari_eval=0.6 * 1.9 + 0.4 * 3.1,  # 2.38
        uncertainty_penalty=0.14,
        truck_exposure_count=2,
        mcda_cost=0.0,
        is_pareto_optimal=True,
        is_recommended=False,
        xai_explanation=(
            "⭐ KHUYÊN DÙNG TỐI ƯU: Chấp nhận tốn thêm 6 phút (+28% thời gian) nhưng giúp giảm đến 77.4% "
            "mức phơi nhiễm rủi ro âm thanh, tránh hoàn toàn các nút giao điểm đen xe tải và giữ ARI P90 ở mức an toàn 3.1/10."
        ),
        waypoints=[(10.772, 106.657), (10.798, 106.685), (10.835, 106.745), (10.850, 106.780)]
    )

    # Tuyến C: Tuyến Đa Phương Thức / Đường Nội Bộ (Rất an toàn nhưng xa và bất định cao)
    scen_c = RouteScenario(
        scenario_id="SCENARIO_C",
        title="Tuyến Vành Đai Vắng / Đường Gom Nội Bộ",
        route_summary="Trường Chinh ➔ Phạm Văn Đồng ➔ Đường nội bộ Làng Đại học",
        duration_min=36.0,
        distance_km=13.4,
        avg_ari=0.8,
        ari_p90=1.2,
        composite_ari_eval=0.6 * 0.8 + 0.4 * 1.2,  # 0.96
        uncertainty_penalty=0.42,
        truck_exposure_count=0,
        mcda_cost=0.0,
        is_pareto_optimal=True,
        is_recommended=False,
        xai_explanation=(
            "🛡️ Tuyến cực kỳ êm dịu (gần như không có tiếng còi xe và 0 lượt xe tải), "
            "nhưng thời gian di chuyển tăng thêm 15 phút và mức độ bất định dữ liệu cao (U = 0.42) do đi qua nhiều ngõ phụ ít người đo."
        ),
        waypoints=[(10.772, 106.657), (10.820, 106.675), (10.865, 106.755), (10.852, 106.790)]
    )

    candidates = [scen_a, scen_b, scen_c]

    # Tính toán chuẩn hóa Min-Max và Hàm chi phí tổng hợp MCDA C(P)
    # T_norm trong khoảng [0, 1]
    times = [s.duration_min for s in candidates]
    aris = [s.composite_ari_eval for s in candidates]
    uncerts = [s.uncertainty_penalty for s in candidates]

    t_min, t_max = min(times), max(times)
    a_min, a_max = min(aris), max(aris)
    u_min, u_max = min(uncerts), max(uncerts)

    best_scenario = None
    min_cost = float("inf")

    for s in candidates:
        t_norm = (s.duration_min - t_min) / (t_max - t_min) if t_max > t_min else 0.0
        a_norm = (s.composite_ari_eval - a_min) / (a_max - a_min) if a_max > a_min else 0.0
        u_norm = (s.uncertainty_penalty - u_min) / (u_max - u_min) if u_max > u_min else 0.0

        # Công thức hàm chi phí đa tiêu chí
        cost = profile.w_time * t_norm + profile.w_ari * a_norm + profile.w_uncertainty * u_norm
        s.mcda_cost = round(cost, 3)

        # Kiểm tra điều kiện ràng buộc an toàn cứng: ARI_max <= tau_cutoff
        if s.ari_p90 > profile.tau_cutoff:
            s.mcda_cost += 5.0  # Phạt nặng vì vi phạm ngưỡng an toàn cứng

        if s.mcda_cost < min_cost:
            min_cost = s.mcda_cost
            best_scenario = s

    if best_scenario:
        best_scenario.is_recommended = True
        recommended_id = best_scenario.scenario_id
    else:
        scen_b.is_recommended = True
        recommended_id = scen_b.scenario_id

    return DecisionResponse(
        origin=origin,
        destination=destination,
        timestamp=time.time(),
        active_profile=profile,
        scenarios=candidates,
        recommended_scenario_id=recommended_id,
        pareto_count=len(candidates)
    )


if __name__ == "__main__":
    print("=" * 65)
    print("   URBANVIBE - KIỂM THỬ MOCK DECISION & AUDIO STREAM ENGINE   ")
    print("=" * 65)
    
    # Test sinh kịch bản ra quyết định
    profile = UserPreferenceProfile.get_presets()["BALANCED"]
    resp = generate_mock_decision_response(profile=profile)
    print(f"Khởi hành: {resp.origin} ➔ Đích đến: {resp.destination}")
    print(f"Hồ sơ sở thích áp dụng: {resp.active_profile.display_title}")
    print(f"Tuyến được khuyên dùng: {resp.recommended_scenario_id}")
    print("\nMa trận Đánh đổi Định lượng:")
    for row in resp.get_tradeoff_matrix():
        print(f" - {row['Tên Lộ trình']:<35} | {row['Thời gian']:<8} | ARI: {row['Rủi ro Âm thanh (ARI)']:<9} | {row['Trạng thái']}")
    
    print("\nKiểm thử luồng sự kiện thời gian thực (5 sự kiện):")
    for i in range(5):
        p = generate_mock_payload()
        print(f"[{p.danger_type:<16}] {p.db:>5.1f} dBA | Hướng: {p.direction:<6} | Looming: {p.is_looming!s:<5} | {p.label}")
        time.sleep(0.3)