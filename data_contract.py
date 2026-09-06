import time
from dataclasses import dataclass, asdict

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