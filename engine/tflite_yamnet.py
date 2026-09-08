import time
from pathlib import Path
from typing import Optional
import numpy as np
import tensorflow as tf

from data_contract import DetectionPayload
from engine.dsp_filter import DSPAnalyzer

class YAMNetEngine:
    # Hierarchical label pooling categories matching YAMNet CSV display_name
    HORN_CLASSES = {
        "Vehicle horn, car horn, honking",
        "Air horn, truck horn",
        "Train horn",
        "Toot",
        "Beep, bleep",
        "Bicycle bell",
        "Reversing beeps",
        "Alarm",
        "Car alarm",
        "Buzzer",
    }
    SIREN_CLASSES = {
        "Siren",
        "Ambulance (siren)",
        "Fire engine, fire truck (siren)",
        "Police car (siren)",
        "Civil defense siren",
    }

    def __init__(
        self,
        model_dir: Optional[str] = None,
        db_threshold: float = 75.0,
        delta_threshold: float = 12.0,
        window_size: int = 15600,
    ):
        if model_dir is None:
            model_dir = str(Path(__file__).resolve().parent / "models")

        self.model_dir = Path(model_dir)
        self.window_size = window_size

        # Load class map
        import csv
        class_map_file = self.model_dir / "yamnet_class_map.csv"
        self.class_names = []
        with open(class_map_file, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader, None)  # Skip header row
            for row in reader:
                if len(row) >= 3:
                    self.class_names.append(row[2].strip())

        # Precompute label pooling indices to avoid repeated string checks
        self.horn_indices = np.array([
            i for i, name in enumerate(self.class_names)
            if (name in self.HORN_CLASSES or any(k in name.lower() for k in ["horn", "honk", "toot", "beep", "alarm", "buzzer", "bell"]))
        ], dtype=np.int32)
        self.siren_indices = np.array([
            i for i, name in enumerate(self.class_names)
            if (name in self.SIREN_CLASSES or any(k in name.lower() for k in ["siren", "ambulance", "police", "emergency"]))
        ], dtype=np.int32)

        # Initialize TFLite interpreter
        model_file = self.model_dir / "yamnet.tflite"
        self.interpreter = tf.lite.Interpreter(model_path=str(model_file))
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()

        # Resize input tensor once for standard audio window
        self.interpreter.resize_tensor_input(
            self.input_details[0]["index"], [self.window_size]
        )
        self.interpreter.allocate_tensors()

        # Warm-up TFLite runtime to eliminate Cold-Start latency
        dummy_tensor = np.zeros(self.window_size, dtype=np.float32)
        self.interpreter.set_tensor(self.input_details[0]["index"], dummy_tensor)
        self.interpreter.invoke()

        # DSP Analyzer for Physical Gate
        self.dsp = DSPAnalyzer(
            db_threshold=db_threshold,
            delta_threshold=delta_threshold,
            enable_bandpass=True,
        )

    def process_audio(self, waveform: np.ndarray) -> DetectionPayload:
        """
        Process audio window through DSP Physical Gate and YAMNet Semantic Gate.
        """
        start_time = time.perf_counter()
        now_epoch = time.time()

        # Ensure correct float32 format and size
        if len(waveform) != self.window_size:
            adjusted = np.zeros(self.window_size, dtype=np.float32)
            if len(waveform) > 0:
                adjusted[-min(len(waveform), self.window_size):] = waveform[
                    -self.window_size:
                ]
            waveform = adjusted
        else:
            waveform = np.asarray(waveform, dtype=np.float32)

        # 1. Physical Gate: DSP calculation
        rms = self.dsp.calculate_rms(waveform)
        db = self.dsp.calculate_db_spl(rms)
        is_physical_danger, _ = self.dsp.update_and_check_gate(db)

        # 2. Semantic Gate: TFLite Inference
        self.interpreter.set_tensor(self.input_details[0]["index"], waveform)
        self.interpreter.invoke()
        scores = self.interpreter.get_tensor(self.output_details[0]["index"])

        if scores.ndim > 1:
            mean_scores = np.mean(scores, axis=0)
        else:
            mean_scores = scores

        # 3. Hierarchical Label Pooling (Vectorized numpy sum)
        horn_score = float(np.sum(mean_scores[self.horn_indices])) if len(self.horn_indices) > 0 else 0.0
        siren_score = float(np.sum(mean_scores[self.siren_indices])) if len(self.siren_indices) > 0 else 0.0

        top_idx = int(np.argmax(mean_scores))
        top_label = self.class_names[top_idx]
        top_conf = float(mean_scores[top_idx])

        # 4. Arbitration logic (Dual-Threshold Gate)
        is_danger = False
        danger_type = "SAFE"
        label = top_label
        confidence = top_conf

        if siren_score >= 0.20 and (is_physical_danger or siren_score >= 0.35):
            danger_type = "EMERGENCY_SIREN"
            label = "Emergency Siren / Ambulance"
            confidence = min(1.0, float(siren_score))
            is_danger = True
        elif horn_score >= 0.20 and is_physical_danger:
            danger_type = "VEHICLE_HORN"
            label = "Vehicle Horn / Warning"
            confidence = min(1.0, float(horn_score))
            is_danger = True
        else:
            danger_type = "SAFE"
            label = top_label
            confidence = min(1.0, float(top_conf))
            is_danger = False

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        return DetectionPayload(
            timestamp=now_epoch,
            db=round(db, 1),
            is_danger=is_danger,
            danger_type=danger_type,
            label=label,
            confidence=round(confidence, 2),
            latency_ms=round(latency_ms, 1),
        )
