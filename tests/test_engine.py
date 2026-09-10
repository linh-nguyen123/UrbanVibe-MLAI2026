import os
import sys
import warnings

# Triệt tiêu toàn bộ cảnh báo TensorFlow
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

from pathlib import Path
import numpy as np
from scipy.io import wavfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from engine.audio_engine import AudioAIEngine

def test_samples():
    print("=" * 60)
    print("      URBANVIBE - KIỂM THỬ AUDIO AI ENGINE VỚI YAMNET       ")
    print("=" * 60)
    
    engine = AudioAIEngine.get_instance()
    sample_dir = Path(__file__).resolve().parent / "test_samples"
    
    test_files = [
        ("ambient_traffic.wav", "Môi trường bình thường (An toàn)"),
        ("horn_sample.wav", "Còi xe máy / Ô tô xin vượt"),
        ("ambulance_siren.wav", "Còi hụ xe cứu thương khẩn cấp"),
    ]
    
    for filename, desc in test_files:
        filepath = sample_dir / filename
        assert filepath.exists(), f"File không tồn tại: {filepath}"
        
        sr, data = wavfile.read(filepath)
        # Chuyển int16 sang float32 [-1.0, 1.0]
        if data.dtype == np.int16:
            waveform = data.astype(np.float32) / 32768.0
        else:
            waveform = data.astype(np.float32)
            
        payload = engine.engine.infer(waveform, sample_rate=sr, trigger_haptic=False)
        from engine.model_inference import is_dangerous
        assert payload.is_danger == is_dangerous(payload.label, payload.confidence, payload.db)
        assert (payload.danger_type != "SAFE") == payload.is_danger
        
        print(f"\n[Test File]: {filename} ({desc})")
        print(f"  ├─ Cường độ đo được (dB): {payload.db:.1f} dB")
        print(f"  ├─ Nhận diện AI (Label) : {payload.label} (Conf: {payload.confidence*100:.1f}%)")
        print(f"  ├─ Cổng lọc (is_danger) : {payload.is_danger}")
        print(f"  ├─ Phân loại nguy hiểm  : {payload.danger_type}")
        print(f"  └─ Độ trễ suy luận      : {payload.latency_ms:.1f} ms")

if __name__ == "__main__":
    test_samples()
