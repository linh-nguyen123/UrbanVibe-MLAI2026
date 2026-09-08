import csv
import logging
import os
import sys
import time
import warnings
from pathlib import Path
import numpy as np

# Triệt tiêu toàn bộ cảnh báo oneDNN, Deprecated và log C++ của TensorFlow
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

logging.getLogger("tensorflow").setLevel(logging.ERROR)

# Thêm thư mục gốc vào path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from data_contract import DetectionPayload
from engine.dsp_filter import apply_highpass_filter, compute_db

# Danh mục phân loại nguy hiểm
HORN_KEYWORDS = {
    "vehicle horn, car horn, honking",
    "air horn, truck horn",
    "train horn",
    "honk",
    "toot",
    "beep, bleep",
    "bicycle bell",
    "alarm",
    "car alarm",
    "buzzer",
}

SIREN_KEYWORDS = {
    "ambulance (siren)",
    "police car (siren)",
    "fire engine, fire truck (siren)",
    "emergency vehicle",
    "siren",
    "civil defense siren",
}


class AudioAIEngine:
    """Audio AI Engine sử dụng Google YAMNet & DSP Dual-Threshold Gate."""

    _instance = None

    def __init__(self):
        import tensorflow as tf
        import tensorflow_hub as hub

        self.tf = tf
        print("[UrbanVibe Engine] Dang khoi tao YAMNet tu cache...")
        self.model = hub.load("https://tfhub.dev/google/yamnet/1")

        # Đọc class map từ YAMNet
        class_map_path = self.model.class_map_path().numpy().decode("utf-8")
        self.class_names = []
        with open(class_map_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.class_names.append(row["display_name"])
        print(
            f"[UrbanVibe Engine] YAMNet khoi tao thanh cong voi {len(self.class_names)} nhan am thanh."
        )

        # [WARM-UP] Thực hiện suy luận khởi động 1 frame số 0 để biên dịch trước đồ thị tính toán
        # Triệt tiêu hoàn toàn Cold-Start Latency, đưa latency về mức < 20ms ngay từ frame đầu tiên
        dummy_tensor = self.tf.zeros([15600], dtype=self.tf.float32)
        _ = self.model(dummy_tensor)

    @classmethod
    def get_instance(cls):
        """Singleton pattern đảm bảo mô hình chỉ load 1 lần vào bộ nhớ."""
        if cls._instance is None:
            cls._instance = AudioAIEngine()
        return cls._instance

    def infer(
        self,
        waveform_16k: np.ndarray,
        db_threshold: float = 78.0,
        conf_threshold: float = 0.35,
        apply_wind_filter: bool = False,
    ) -> DetectionPayload:
        """
        Thực thi suy luận phân loại âm thanh và cổng lọc kép Dual-Threshold Gate.

        :param waveform_16k: Mảng numpy 1D float32 trong khoảng [-1.0, 1.0], tần số lấy mẫu 16000Hz.
        :param db_threshold: Ngưỡng cường độ Decibel để kích hoạt nguy hiểm.
        :param conf_threshold: Ngưỡng độ tin cậy AI (0.0 -> 1.0).
        :param apply_wind_filter: Bật bộ lọc DSP High-pass 300Hz chống gió rít.
        """
        start_time = time.perf_counter()
        now = time.time()

        # Đảm bảo waveform đúng định dạng float32
        if waveform_16k.dtype != np.float32:
            waveform_16k = waveform_16k.astype(np.float32)

        # Chuẩn hóa nếu âm lượng vượt ngưỡng [-1.0, 1.0]
        max_abs = np.max(np.abs(waveform_16k)) if len(waveform_16k) > 0 else 0.0
        if max_abs > 1.0:
            waveform_16k = waveform_16k / max_abs

        # 1. Tính toán Decibel bằng module DSP
        db = compute_db(waveform_16k)

        # 2. Áp dụng bộ lọc DSP chống tiếng gió rít nếu cần
        proc_waveform = waveform_16k
        if apply_wind_filter and len(waveform_16k) > 128:
            try:
                proc_waveform = apply_highpass_filter(
                    waveform_16k, sample_rate=16000, cutoff=300.0
                )
            except Exception:
                proc_waveform = waveform_16k

        # 3. Chạy suy luận qua mô hình YAMNet
        waveform_tensor = self.tf.convert_to_tensor(
            proc_waveform, dtype=self.tf.float32
        )
        scores, embeddings, spectrogram = self.model(waveform_tensor)
        scores_np = scores.numpy()

        # Tổng hợp điểm số qua các khung thời gian: Kết hợp Max (bắt đỉnh sự kiện) & Mean
        max_scores = (
            np.max(scores_np, axis=0) if len(scores_np.shape) > 1 else scores_np
        )
        mean_scores = (
            np.mean(scores_np, axis=0) if len(scores_np.shape) > 1 else scores_np
        )
        event_scores = 0.7 * max_scores + 0.3 * mean_scores

        top_idx = int(np.argmax(event_scores))
        top_label = self.class_names[top_idx]
        confidence = float(event_scores[top_idx])

        # 4. Phân loại loại âm thanh (Candidate Type)
        lower_label = top_label.lower()
        candidate_type = "SAFE"
        if any(kw in lower_label for kw in SIREN_KEYWORDS):
            candidate_type = "EMERGENCY_SIREN"
        elif any(kw in lower_label for kw in HORN_KEYWORDS):
            candidate_type = "VEHICLE_HORN"

        # Kiểm tra thêm top 5 nhãn sự kiện phòng trường hợp nhãn chính là 'Vehicle' nhưng có còi xe đi kèm
        if candidate_type == "SAFE":
            top_5_indices = np.argsort(event_scores)[-5:][::-1]
            for idx in top_5_indices:
                sub_label = self.class_names[idx].lower()
                sub_conf = float(event_scores[idx])
                if sub_conf >= 0.20:
                    if any(kw in sub_label for kw in SIREN_KEYWORDS):
                        candidate_type = "EMERGENCY_SIREN"
                        top_label = self.class_names[idx]
                        confidence = sub_conf
                        break
                    elif any(kw in sub_label for kw in HORN_KEYWORDS):
                        candidate_type = "VEHICLE_HORN"
                        top_label = self.class_names[idx]
                        confidence = sub_conf
                        break

        # 5. Bộ lọc cổng kép (Dual-Threshold Gate)
        # Chỉ báo động khi: Đạt ngưỡng Decibel VÀ Đạt độ tin cậy AI VÀ Là âm thanh nguy hiểm
        is_danger = (
            candidate_type != "SAFE"
            and db >= db_threshold
            and confidence >= conf_threshold
        )
        danger_type = candidate_type if is_danger else "SAFE"

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return DetectionPayload(
            timestamp=now,
            db=round(db, 1),
            is_danger=is_danger,
            danger_type=danger_type,
            label=top_label,
            confidence=round(confidence, 2),
            latency_ms=round(latency_ms, 1),
        )
