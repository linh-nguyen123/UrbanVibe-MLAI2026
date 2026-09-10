"""
Audio AI Engine sử dụng Google YAMNet TFLite & DSP Dual-Threshold Gate.
Được tối ưu hoá hoàn toàn cho Edge-AI On-Device (TFLite XNNPACK).
Độ trễ và RAM được đo bằng tests/benchmark_model_inference.py.
"""

import os
import sys
import warnings
from pathlib import Path
import numpy as np

# Triệt tiêu log không cần thiết
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from data_contract import DetectionPayload
from engine.main_engine import MainEngine


class AudioAIEngine:
    """
    Audio AI Engine sử dụng Google YAMNet TFLite On-Device.
    Được ánh xạ trực tiếp tới MainEngine Facade để đảm bảo hiệu năng cao nhất.
    """

    _instance = None

    def __init__(self):
        print("[UrbanVibe Engine] Dang khoi tao YAMNet TFLite on-device...")
        self.engine = MainEngine.get_instance()
        print(
            f"[UrbanVibe Engine] YAMNet TFLite khoi tao thanh cong voi {len(self.engine.ai_engine.class_names)} nhan am thanh."
        )

    @classmethod
    def get_instance(cls):
        """Singleton pattern đảm bảo mô hình chỉ load 1 lần vào bộ nhớ RAM."""
        if cls._instance is None:
            cls._instance = AudioAIEngine()
        return cls._instance

    def infer(
        self,
        waveform_16k: np.ndarray,
        db_threshold: float = 75.0,
        conf_threshold: float = 0.60,
        apply_wind_filter: bool = False,
    ) -> DetectionPayload:
        """Thực thi suy luận thông qua TFLite Engine siêu tốc."""
        return self.engine.infer(
            waveform=waveform_16k,
            sample_rate=16000,
            db_threshold=db_threshold,
            conf_threshold=conf_threshold,
            trigger_haptic=False,
        )
