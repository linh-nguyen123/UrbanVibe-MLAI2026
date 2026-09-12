import time
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional

@dataclass
class DetectionPayload:
    timestamp: float        # Thời gian epoch ghi nhận
    db: float               # Cường độ âm thanh Decibel SPL
    is_danger: bool         # True nếu có nguy cơ vượt ngưỡng
    danger_type: str        # 'SAFE' | 'VEHICLE_HORN' | 'EMERGENCY_SIREN'
    label: str              # Nhãn nhận diện chi tiết từ mô hình YAMNet
    confidence: float       # Độ tin cậy (0.0 -> 1.0)
    latency_ms: float       # Độ trễ suy luận của frame (ms)

    def to_dict(self):
        return asdict(self)


@dataclass
class RouteScenario:
    """
    Kịch bản lộ trình giao thông cho hệ thống hỗ trợ ra quyết định (Pre-Trip MCDA).
    """
    route_id: str                      # Mã nhận diện tuyến (vd: 'ROUTE_A', 'ROUTE_B')
    name: str                          # Tên mô tả lộ trình (vd: 'Tuyến A - Trục Đại Lộ')
    time_min: float                    # Thời gian di chuyển ước tính (T, phút)
    distance_km: float                 # Khoảng cách lộ trình (D, km)
    ari_mean: float                    # Rủi ro âm thanh trung bình (ARI_bar, thang 0..10)
    ari_p90: float                     # Rủi ro bách phân vị thứ 90 theo độ dài (ARI_P90, thang 0..10)
    uncertainty: float                 # Độ bất định Bayesian (U, thang 0..1)
    truck_density: float               # Mật độ xe tải (0.0 -> 1.0)
    xai_explanation: str = ""          # Diễn giải minh bạch lý do đánh đổi (XAI)
    is_recommended: bool = False       # Cờ đánh dấu tuyến tối ưu đề xuất
    ari_max: float = 0.0               # Rủi ro đỉnh phân đoạn lớn nhất (dùng cho ràng buộc cứng tau_cutoff)
    n_trips: int = 0                   # Số chuyến đi thực tế đã ghi nhận trên tuyến
    mcda_score: float = 0.0            # Điểm hàm chi phí tổng hợp C(P)

    @property
    def duration_min(self) -> float:
        return self.time_min

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class UserPreferenceProfile:
    """
    Cấu hình sở thích và vector trọng số người dùng: W = [w_time, w_ari, w_uncert].
    Ràng buộc toán học: w_time, w_ari, w_uncert >= 0 và w_time + w_ari + w_uncert = 1.0.
    """
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
    """
    Kết quả phản hồi từ Decision Engine cho Pre-Trip Planning.
    """
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