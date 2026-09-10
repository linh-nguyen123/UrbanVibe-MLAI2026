"""
URBANVIBE - MAIN ENGINE (ORCHESTRATOR & FACADE)
Trung tâm điều phối kết nối toàn bộ hệ thống Edge-AI:
- Thu nhận âm thanh thời gian thực (AudioStreamWorker)
- Phân tích tín hiệu số & cổng lọc vật lý (DSPAnalyzer)
- Suy luận nơ-ron âm học on-device (YAMNetEngine - TensorFlow Lite)
- Bộ điều khiển rung đa phương thức (SerialHapticDriver & Web Vibration)
- Đóng gói dữ liệu chuẩn hóa (DetectionPayload)
"""

import logging
import threading
import time
from pathlib import Path
from typing import Callable, Optional

import numpy as np
from scipy import signal

from data_contract import DetectionPayload
from engine.audio_stream import AudioStreamWorker
from engine.dsp_filter import DSPAnalyzer
from engine.haptic_controller import SerialHapticDriver, get_vibration_js
from engine.model_inference import YAMNetEngine

logger = logging.getLogger("UrbanVibe.MainEngine")


class MainEngine:
    """
    Main Engine (Facade & Pipeline Orchestrator) cho UrbanVibe.
    Hỗ trợ cả chế độ xử lý mảng âm thanh đơn lẻ (Offline / Upload / Test)
    và luồng streaming liên tục từ Microphone thời gian thực.
    """

    _instance: Optional["MainEngine"] = None
    _lock = threading.Lock()

    def __init__(
        self,
        model_dir: Optional[str] = None,
        db_threshold: float = 75.0,
        delta_threshold: float = 12.0,
        serial_port: Optional[str] = None,
        enable_bandpass: bool = True,
    ):
        self.window_size = 15600  # 0.975 giây ở 16,000 Hz
        self.sample_rate = 16000
        self.db_threshold = db_threshold
        self.delta_threshold = delta_threshold

        logger.info("[MainEngine] Đang khởi tạo các module thành phần...")

        # 1. Module AI Suy luận YAMNet TFLite
        self.ai_engine = YAMNetEngine(
            model_dir=model_dir,
            db_threshold=db_threshold,
            delta_threshold=delta_threshold,
            window_size=self.window_size,
        )

        # 2. Module Phân tích DSP (dùng chung instance cấu hình với AI engine)
        self.dsp = self.ai_engine.dsp

        # 3. Module Thu âm Microphone Đa luồng (Khởi tạo sẵn sàng)
        self.stream_worker = AudioStreamWorker(
            sample_rate=self.sample_rate,
            window_duration=0.975,
        )

        # 4. Module Điều khiển Rung Xúc giác Phần cứng (HAL)
        self.haptic_driver = SerialHapticDriver(port=serial_port)

        # Trạng thái luồng streaming nền
        self._stream_thread: Optional[threading.Thread] = None
        self._stream_running = False
        self._latest_payload: Optional[DetectionPayload] = None
        self._stream_callback: Optional[Callable[[DetectionPayload], None]] = None

        # 5. Warm-up trước khi nhận âm thanh; hiệu năng cần đo trên máy đích.
        self._warmup()
        logger.info("[MainEngine] Khởi tạo hoàn tất. Sẵn sàng vận hành thời gian thực!")

    @classmethod
    def get_instance(
        cls,
        model_dir: Optional[str] = None,
        db_threshold: float = 75.0,
        delta_threshold: float = 12.0,
        serial_port: Optional[str] = None,
    ) -> "MainEngine":
        """Singleton pattern đảm bảo mô hình chỉ nạp 1 lần vào bộ nhớ RAM."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls(
                    model_dir=model_dir,
                    db_threshold=db_threshold,
                    delta_threshold=delta_threshold,
                    serial_port=serial_port,
                )
            return cls._instance

    def _warmup(self):
        """Khởi động đồ thị tính toán và cấp phát tensor trước khi đón nhận luồng dữ liệu thật."""
        dummy_audio = np.zeros(self.window_size, dtype=np.float32)
        _ = self.infer(dummy_audio, trigger_haptic=False)

    def preprocess_audio(
        self, waveform: np.ndarray, sample_rate: int = 16000
    ) -> np.ndarray:
        """
        Chuẩn hóa âm thanh đầu vào về định dạng chuẩn của YAMNet:
        - Chuyển đa kênh (Stereo) sang Mono
        - Chuyển int16 / int32 về float32 [-1.0, 1.0]
        - Resample về 16,000 Hz nếu khác tần số chuẩn
        - Cắt / đệm về kích thước cửa sổ chuẩn (15,600 samples = 0.975s)
        """
        if waveform is None or len(waveform) == 0:
            return np.zeros(self.window_size, dtype=np.float32)

        # 1. Chuyển đa kênh sang Mono
        if waveform.ndim > 1:
            waveform = waveform[:, 0]

        # 2. Chuẩn hóa kiểu dữ liệu sang float32 [-1.0, 1.0]
        if waveform.dtype == np.int16:
            waveform = waveform.astype(np.float32) / 32768.0
        elif waveform.dtype == np.int32:
            waveform = waveform.astype(np.float32) / 2147483648.0
        elif waveform.dtype == np.uint8:
            waveform = (waveform.astype(np.float32) - 128.0) / 128.0
        elif waveform.dtype != np.float32:
            waveform = waveform.astype(np.float32)

        # 3. Resample nếu tần số lấy mẫu khác 16kHz
        if sample_rate != 16000 and len(waveform) > 0:
            target_len = int(len(waveform) * 16000 / sample_rate)
            waveform = signal.resample(waveform, target_len).astype(np.float32)

        # 4. Chuẩn hóa biên độ nếu có giá trị vượt ngưỡng [-1.0, 1.0]
        max_abs = np.max(np.abs(waveform)) if len(waveform) > 0 else 0.0
        if max_abs > 1.0:
            waveform = waveform / max_abs

        # 5. Cắt cửa sổ dài; model_inference đo RMS trước khi đệm cửa sổ ngắn.
        if len(waveform) > self.window_size:
            waveform = waveform[: self.window_size]

        return waveform

    def infer(
        self,
        waveform: np.ndarray,
        sample_rate: int = 16000,
        db_threshold: Optional[float] = None,
        conf_threshold: Optional[float] = None,
        trigger_haptic: bool = True,
    ) -> DetectionPayload:
        """
        Thực thi pipeline suy luận trọn vẹn:
        Chuẩn hóa âm thanh -> Phân tích DSP & Cổng vật lý -> YAMNet TFLite -> Phân định Cổng kép -> Kích hoạt Rung -> DetectionPayload.
        
        Đo lường thời gian suy luận chính xác tuyệt đối bằng time.perf_counter().
        """
        start_time = time.perf_counter()

        # 1. Chuẩn hóa đầu vào
        proc_waveform = self.preprocess_audio(waveform, sample_rate=sample_rate)

        # 2. Suy luận qua YAMNet Engine
        payload = self.ai_engine.process_audio(proc_waveform)

        # 3. Cho phép ghi đè ngưỡng động (Dynamic Thresholds) nếu UI yêu cầu
        is_danger = payload.is_danger
        danger_type = payload.danger_type

        if db_threshold is not None or conf_threshold is not None:
            active_db_th = db_threshold if db_threshold is not None else self.db_threshold
            active_conf_th = conf_threshold if conf_threshold is not None else 0.60

            if danger_type != "SAFE":
                if payload.db <= active_db_th or payload.confidence <= active_conf_th:
                    is_danger = False
                    danger_type = "SAFE"
                else:
                    is_danger = True

        # 4. Kích hoạt phản hồi xúc giác phần cứng (Haptic Feedback)
        if trigger_haptic and is_danger:
            self.haptic_driver.trigger(danger_type)

        # 5. Cập nhật độ trễ chuẩn xác (tính toàn bộ thời gian end-to-end của infer)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        final_payload = DetectionPayload(
            timestamp=time.time(),
            db=payload.db,
            is_danger=is_danger,
            danger_type=danger_type,
            label=payload.label,
            confidence=payload.confidence,
            latency_ms=elapsed_ms,
        )

        self._latest_payload = final_payload
        return final_payload

    def infer_frame(self, waveform: np.ndarray, **kwargs) -> DetectionPayload:
        """Alias tương thích cho hàm infer."""
        return self.infer(waveform, **kwargs)

    # -------------------------------------------------------------------------
    # LUỒNG GIÁM SÁT MICROPHONE THỜI GIAN THỰC (REALTIME STREAMING PIPELINE)
    # -------------------------------------------------------------------------
    def start_live_stream(
        self,
        device: Optional[int] = None,
        poll_interval: float = 0.25,
        callback: Optional[Callable[[DetectionPayload], None]] = None,
    ):
        """Khởi động luồng thu âm nền liên tục từ Microphone với cửa sổ trượt."""
        if self._stream_running:
            return

        self._stream_callback = callback
        self.stream_worker.start(device=device)
        self._stream_running = True

        def _loop():
            while self._stream_running:
                window = self.stream_worker.get_latest_window()
                payload = self.infer(window, sample_rate=16000, trigger_haptic=True)
                if self._stream_callback is not None:
                    try:
                        self._stream_callback(payload)
                    except Exception as e:
                        logger.error(f"[MainEngine] Lỗi trong stream callback: {e}")
                time.sleep(poll_interval)

        self._stream_thread = threading.Thread(target=_loop, daemon=True)
        self._stream_thread.start()
        logger.info("[MainEngine] Đã bật luồng giám sát âm thanh Micro thời gian thực.")

    def get_latest_payload(self) -> DetectionPayload:
        """Lấy kết quả phát hiện mới nhất từ luồng stream thời gian thực."""
        if self._latest_payload is None:
            return DetectionPayload(
                timestamp=time.time(),
                db=45.0,
                is_danger=False,
                danger_type="SAFE",
                label="Initializing...",
                confidence=0.0,
                latency_ms=0.0,
            )
        return self._latest_payload

    def stop_live_stream(self):
        """Dừng thu âm từ Microphone và giải phóng tài nguyên."""
        self._stream_running = False
        if self.stream_worker:
            self.stream_worker.stop()
        if self._stream_thread and self._stream_thread.is_alive():
            self._stream_thread.join(timeout=1.0)
        self._stream_thread = None
        logger.info("[MainEngine] Đã tắt luồng thu âm Microphone.")

    @staticmethod
    def get_vibration_js(danger_type: str) -> str:
        """Tạo mã JavaScript Web Vibration API để kích hoạt rung trên trình duyệt điện thoại."""
        return get_vibration_js(danger_type)


# Alias tương thích ngược cho các module frontend đang gọi AudioAIEngine
AudioAIEngine = MainEngine
