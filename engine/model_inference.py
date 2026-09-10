"""Offline YAMNet inference and strict acoustic/semantic danger gate.

Input is mono float audio at 16 kHz, normalized to [-1, 1]. The dB value
uses the project's +100 calibration offset; it is an estimate, not measured SPL.
"""

import csv
import threading
import time
from functools import lru_cache
from pathlib import Path

import numpy as np

from data_contract import DetectionPayload
from engine.dsp_filter import DSPAnalyzer

CONFIDENCE_THRESHOLD = 0.60
DECIBEL_THRESHOLD = 75.0
TARGET_CLASSES = frozenset({
    "Vehicle horn, car horn, honking", "Siren", "Bicycle bell",
    "Ambulance (siren)", "Alarm",
})


def is_dangerous(label: str, confidence: float, db: float) -> bool:
    return bool(label in TARGET_CLASSES and
                CONFIDENCE_THRESHOLD < confidence <= 1.0 and
                np.isfinite(db) and db > DECIBEL_THRESHOLD)


class YAMNetEngine:
    def __init__(self, model_dir=None, db_threshold=75.0,
                 delta_threshold=12.0, window_size=15600, num_threads=1):
        import tensorflow as tf

        self.model_dir = Path(model_dir) if model_dir else Path(__file__).parent / "models"
        self.window_size = window_size
        self.dsp = DSPAnalyzer(db_threshold=db_threshold, delta_threshold=delta_threshold)
        self._lock = threading.Lock()
        with (self.model_dir / "yamnet_class_map.csv").open(encoding="utf-8", newline="") as f:
            self.class_names = [row["display_name"] for row in csv.DictReader(f)]
        self.interpreter = tf.lite.Interpreter(
            model_path=str(self.model_dir / "yamnet.tflite"), num_threads=num_threads)
        input_info = self.interpreter.get_input_details()[0]
        self.interpreter.resize_tensor_input(input_info["index"], [window_size])
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        # Identify class scores by shape, rather than assuming output ordering.
        outputs = [d for d in self.output_details if d["shape"][-1] == len(self.class_names)]
        if len(outputs) != 1:
            raise ValueError("Expected one YAMNet class-score output")
        self._score_index = outputs[0]["index"]
        self._predict(np.zeros(window_size, dtype=np.float32))

    def _predict(self, waveform):
        with self._lock:
            self.interpreter.set_tensor(self.input_details[0]["index"], waveform)
            self.interpreter.invoke()
            scores = self.interpreter.get_tensor(self._score_index)
        return scores.mean(axis=0) if scores.ndim > 1 else scores

    def infer(self, waveform_16k: np.ndarray) -> dict:
        waveform = np.asarray(waveform_16k)
        if waveform.ndim != 1 or not np.issubdtype(waveform.dtype, np.floating):
            raise ValueError("Expected mono floating-point audio sampled at 16000 Hz")
        if not np.all(np.isfinite(waveform)) or np.any(np.abs(waveform) > 1):
            raise ValueError("Audio must be finite and normalized to [-1, 1]")
        if len(waveform) > self.window_size:
            raise ValueError(f"Pass at most {self.window_size} samples per inference window")
        # Measure the actual input before zero-padding short windows.
        db = self.dsp.calculate_db_spl(self.dsp.calculate_rms(waveform))
        padded = np.zeros(self.window_size, dtype=np.float32)
        padded[:len(waveform)] = waveform
        scores = self._predict(padded)
        index = int(np.argmax(scores))
        label, confidence = self.class_names[index], float(scores[index])
        return dict(is_danger=is_dangerous(label, confidence, db),
                    label=label, confidence=confidence, db=db)

    def process_audio(self, waveform: np.ndarray) -> DetectionPayload:
        start = time.perf_counter()
        result = self.infer(waveform)
        danger_type = "SAFE"
        if result["is_danger"]:
            danger_type = ("EMERGENCY_SIREN" if "siren" in result["label"].lower()
                           else "VEHICLE_HORN")
        return DetectionPayload(timestamp=time.time(), danger_type=danger_type,
                                latency_ms=(time.perf_counter() - start) * 1000,
                                **result)


@lru_cache(maxsize=1)
def _default_engine():
    return YAMNetEngine()


def infer(waveform_16k: np.ndarray) -> dict:
    """Reuse the local interpreter; return is_danger, label, confidence and db."""
    return _default_engine().infer(waveform_16k)
