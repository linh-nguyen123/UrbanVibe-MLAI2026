import sys
from pathlib import Path

# Tự động trỏ đường dẫn ra thư mục gốc của dự án
sys.path.append(str(Path(__file__).resolve().parent.parent))

import random
import time
from data_contract import DetectionPayload

def generate_mock_payload() -> DetectionPayload:
    """Giả lập luồng sự kiện thời gian thực từ Audio AI Engine."""
    rand = random.random()
    now = time.time()

    if rand < 0.70:
        # 70% thời gian: Trạng thái bình thường / Giọng nói nhẹ
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(40.0, 65.0), 1),
            is_danger=False,
            danger_type="SAFE",
            label="Background noise / Speech",
            confidence=round(random.uniform(0.70, 0.95), 2),
            latency_ms=round(random.uniform(18.0, 32.0), 1)
        )
    elif rand < 0.85:
        # 15% thời gian: Phát hiện còi xe máy / ô tô
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(76.0, 84.0), 1),
            is_danger=True,
            danger_type="VEHICLE_HORN",
            label="Vehicle horn, car horn",
            confidence=round(random.uniform(0.78, 0.92), 2),
            latency_ms=round(random.uniform(22.0, 38.0), 1)
        )
    else:
        # 15% thời gian: Phát hiện còi xe cấp cứu / xe ưu tiên khẩn cấp
        return DetectionPayload(
            timestamp=now,
            db=round(random.uniform(85.0, 95.0), 1),
            is_danger=True,
            danger_type="EMERGENCY_SIREN",
            label="Ambulance (siren)",
            confidence=round(random.uniform(0.85, 0.98), 2),
            latency_ms=round(random.uniform(25.0, 42.0), 1)
        )

if __name__ == "__main__":
    print("=" * 55)
    print("   URBANVIBE - BẮT ĐẦU PHÁT DỮ LIỆU GIẢ LẬP (MOCK DATA)   ")
    print("   Nhấn Ctrl+C để dừng phát luồng dữ liệu...              ")
    print("=" * 55)
    while True:
        data = generate_mock_payload()
        status_tag = f"[{data.danger_type}]"
        print(f"{status_tag:<18} | {data.db:>5.1f} dB | Label: {data.label:<25} ({data.confidence * 100:>4.1f}%) | Danger: {data.is_danger}")
        time.sleep(0.5)