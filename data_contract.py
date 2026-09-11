# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Unified Data Contract
Định nghĩa các cấu trúc dữ liệu chuẩn hóa trao đổi giữa:
- Backend: Audio Processing, Edge-AI YAMNet, Decision Intelligence Engine (MCDA)
- Frontend: Streamlit Dashboard (Pre-Trip Decision Matrix & On-Trip HUD)
"""

import time
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional, Tuple


# ============================================================================
# 1. ON-TRIP EDGE SAFEGUARD CONTRACTS (GIÁM SÁT AN TOÀN TRÊN XE)
# ============================================================================

@dataclass
class DetectionPayload:
    """
    Gói dữ liệu cảnh báo âm thanh thời gian thực từ YAMNet & DSP Filter.
    Được sinh ra mỗi chu kỳ suy luận (250ms) hoặc khi có xung áp sát Looming (50ms).
    """
    timestamp: float        # Thời gian epoch ghi nhận (time.time())
    db: float               # Cường độ âm thanh Decibel SPL tương đối (dBA)
    is_danger: bool         # True nếu phát hiện mối nguy hiểm vượt ngưỡng kép
    danger_type: str        # 'SAFE' | 'VEHICLE_HORN' | 'EMERGENCY_SIREN' | 'TRUCK_APPROACH'
    label: str              # Tên nhãn chi tiết từ mô hình YAMNet (ví dụ: 'Air horn', 'Siren')
    confidence: float       # Độ tin cậy dự đoán (0.0 -> 1.0)
    latency_ms: float       # Độ trễ toàn chu trình suy luận của khung âm thanh (ms)
    direction: str = "UNKNOWN"  # Hướng âm thanh: 'LEFT' | 'RIGHT' | 'CENTER' | 'UNKNOWN'
    is_looming: bool = False    # True nếu phát hiện biến thiên dE/dt áp sát nguy cấp

    def to_dict(self) -> Dict:
        return asdict(self)


# ============================================================================
# 2. PRE-TRIP DECISION INTELLIGENCE CONTRACTS (HỖ TRỢ RA QUYẾT ĐỊNH LỘ TRÌNH)
# ============================================================================

@dataclass
class UserPreferenceProfile:
    """
    Hồ sơ sở thích an toàn và thính lực cá nhân của người dùng.
    Quy định vector trọng số W = [w_time, w_ari, w_uncertainty] với tổng = 1.0
    và ngưỡng cắt an toàn cứng tau_cutoff.
    """
    profile_name: str       # 'SAFE_FIRST' | 'BALANCED' | 'FAST_FIRST' | 'CUSTOM'
    display_title: str      # Tên hiển thị tiếng Việt (ví dụ: 'Ưu tiên An toàn tối đa')
    w_time: float           # Trọng số thời gian (0.0 -> 1.0)
    w_ari: float            # Trọng số chỉ số rủi ro âm thanh ARI (0.0 -> 1.0)
    w_uncertainty: float    # Trọng số phạt bất định dữ liệu Bayesian (0.0 -> 1.0)
    tau_cutoff: float = 9.0 # Ngưỡng cắt rủi ro cứng (loại bỏ tuyến có ARI_max > tau_cutoff)

    def __post_init__(self):
        # Chuẩn hóa vector trọng số sao cho tổng w_i = 1.0
        total = self.w_time + self.w_ari + self.w_uncertainty
        if total > 0 and abs(total - 1.0) > 1e-4:
            self.w_time = round(self.w_time / total, 3)
            self.w_ari = round(self.w_ari / total, 3)
            self.w_uncertainty = round(1.0 - self.w_time - self.w_ari, 3)

    @classmethod
    def get_presets(cls) -> Dict[str, "UserPreferenceProfile"]:
        """Danh mục 3 bộ cấu hình chuẩn cho người khiếm thính."""
        return {
            "SAFE_FIRST": cls(
                profile_name="SAFE_FIRST",
                display_title="🛡️ Ưu tiên An toàn Tối đa (Safe-First)",
                w_time=0.15,
                w_ari=0.70,
                w_uncertainty=0.15,
                tau_cutoff=8.5
            ),
            "BALANCED": cls(
                profile_name="BALANCED",
                display_title="⚖️ Cân bằng Thực tế (Khuyên dùng)",
                w_time=0.40,
                w_ari=0.45,
                w_uncertainty=0.15,
                tau_cutoff=9.0
            ),
            "FAST_FIRST": cls(
                profile_name="FAST_FIRST",
                display_title="⚡ Nhanh nhất (Tối ưu Thời gian)",
                w_time=0.75,
                w_ari=0.15,
                w_uncertainty=0.10,
                tau_cutoff=9.8
            )
        }

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RouteSegment:
    """
    Thông tin phân đoạn đường nhỏ (segment s) phục vụ tính toán không gian.
    """
    segment_id: str
    name: str                   # Tên đoạn đường (ví dụ: 'Đường Điện Biên Phủ')
    length_m: float             # Chiều dài đoạn đường (mét)
    avg_db: float               # Mức áp suất âm trung bình (dBA)
    truck_freq: float           # Tần suất xe tải nặng / xe ben (lượt/phút)
    horn_freq: float            # Tần suất còi xe giao thông (lượt/phút)
    is_blackspot: bool          # Có phải điểm đen tai nạn / nút giao hỗn loạn
    ari_score: float            # Chỉ số rủi ro âm thanh tính toán ARI(s) [0.0 - 10.0]
    uncertainty: float          # Độ bất định dữ liệu Bayesian U(s) [0.0 - 1.0]

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class RouteScenario:
    """
    Một phương án lộ trình di chuyển hoàn chỉnh cùng các chỉ số đánh đổi định lượng.
    """
    scenario_id: str            # 'SCENARIO_A' | 'SCENARIO_B' | 'SCENARIO_C'
    title: str                  # Tiêu đề ngắn (ví dụ: 'Tuyến Nhanh Nhất (Baseline)')
    route_summary: str          # Tóm tắt hành trình qua các trục đường chính
    duration_min: float         # Thời gian di chuyển dự kiến (phút)
    distance_km: float          # Tổng chiều dài lộ trình (km)
    
    # Các chỉ số cốt lõi của Decision Intelligence
    avg_ari: float              # Mức rủi ro trung bình theo chiều dài (0.0 -> 10.0)
    ari_p90: float              # Ngưỡng rủi ro bách phân vị 90 (0.0 -> 10.0)
    composite_ari_eval: float   # Rủi ro đánh giá: 0.6 * avg_ari + 0.4 * ari_p90
    uncertainty_penalty: float  # Độ bất định trung bình toàn tuyến U(P) (0.0 -> 1.0)
    truck_exposure_count: int   # Số lượt phơi nhiễm xe tải trọng lớn dự kiến
    
    # Kết quả xếp hạng đa mục tiêu MCDA
    mcda_cost: float            # Điểm chi phí tổng hợp C(P) (càng thấp càng tối ưu)
    is_pareto_optimal: bool     # True nếu thuộc tập tối ưu Pareto (Non-dominated)
    is_recommended: bool        # True nếu là tuyến được thuật toán khuyên dùng
    
    # Giải thích minh bạch (Explainable AI - XAI)
    xai_explanation: str        # Lời giải thích trực quan bằng ngôn ngữ tự nhiên
    
    # Danh sách phân đoạn chi tiết và tọa độ hiển thị bản đồ
    segments: List[RouteSegment] = field(default_factory=list)
    waypoints: List[Tuple[float, float]] = field(default_factory=list)  # (lat, lon)

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class DecisionResponse:
    """
    Gói dữ liệu phản hồi hoàn chỉnh từ DecisionEngine gửi đến Giao diện Streamlit.
    """
    origin: str                             # Điểm xuất phát (ví dụ: 'ĐH Bách Khoa CS1')
    destination: str                        # Điểm đến (ví dụ: 'Bến xe Miền Đông mới')
    timestamp: float                        # Thời điểm tính toán
    active_profile: UserPreferenceProfile   # Profile sở thích đang được áp dụng
    scenarios: List[RouteScenario]          # Danh sách các kịch bản tuyến đường ứng viên
    recommended_scenario_id: str            # ID của kịch bản tối ưu được khuyên dùng
    pareto_count: int                       # Số lượng tuyến nằm trên đường biên Pareto

    def get_recommended_scenario(self) -> Optional[RouteScenario]:
        """Lấy thông tin kịch bản được đề xuất tối ưu."""
        for s in self.scenarios:
            if s.scenario_id == self.recommended_scenario_id:
                return s
        return self.scenarios[0] if self.scenarios else None

    def get_tradeoff_matrix(self) -> List[Dict]:
        """
        Xuất danh sách bảng đánh đổi định lượng phục vụ render Streamlit DataFrame.
        """
        rows = []
        for s in self.scenarios:
            rows.append({
                "Mã Kịch bản": s.scenario_id,
                "Tên Lộ trình": s.title,
                "Thời gian": f"{s.duration_min:.0f} phút",
                "Khoảng cách": f"{s.distance_km:.1f} km",
                "Rủi ro Âm thanh (ARI)": f"{s.avg_ari:.1f} / 10",
                "Rủi ro Đỉnh (P90)": f"{s.ari_p90:.1f} / 10",
                "Lượt gặp Xe lớn": f"{s.truck_exposure_count} lượt",
                "Độ bất định (U)": f"{s.uncertainty_penalty:.2f}",
                "Điểm Chi phí MCDA": f"{s.mcda_cost:.3f}",
                "Trạng thái": "⭐ KHUYÊN DÙNG" if s.is_recommended else ("Tối ưu Pareto" if s.is_pareto_optimal else "Bị thống trị")
            })
        return rows

    def to_dict(self) -> Dict:
        return asdict(self)