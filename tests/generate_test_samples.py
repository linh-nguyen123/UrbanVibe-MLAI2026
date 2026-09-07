import sys
import numpy as np
from scipy.io import wavfile
from scipy import signal
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

SAMPLE_RATE = 16000
OUTPUT_DIR = Path(__file__).resolve().parent / "test_samples"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_horn_sample(duration: float = 1.5) -> np.ndarray:
    """Sinh âm thanh mô phỏng còi xe máy/ô tô chuẩn xác (sóng răng cưa 430Hz + 480Hz)."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    
    # 2 tần số còi xe cơ giới đặc trưng (370Hz + 440Hz)
    f1, f2 = 370.0, 440.0
    sig = 0.6 * signal.sawtooth(2 * np.pi * f1 * t) + 0.4 * signal.sawtooth(2 * np.pi * f2 * t)
    sig = np.clip(sig * 1.5, -1.0, 1.0)
    
    # Envelope ADSR: Bấm còi dứt khoát
    envelope = np.ones_like(t)
    attack = int(SAMPLE_RATE * 0.05)
    release = int(SAMPLE_RATE * 0.08)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    
    waveform = sig * envelope
    # Chuẩn hóa biên độ đạt mức âm lượng cao (~81 dB SPL)
    waveform = (waveform / np.max(np.abs(waveform))) * 0.22
    return waveform.astype(np.float32)

def generate_ambulance_siren(duration: float = 2.5) -> np.ndarray:
    """Sinh âm thanh mô phỏng còi hụ xe cứu thương (tần số quét tuần hoàn 650Hz <-> 1350Hz)."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    
    # Tần số quét (Wail siren) chu kỳ 1.2s
    sweep_rate = 1.2
    f_center = 1000.0
    f_dev = 350.0
    instantaneous_freq = f_center + f_dev * np.sin(2 * np.pi * sweep_rate * t)
    phase = 2 * np.pi * np.cumsum(instantaneous_freq) / SAMPLE_RATE
    
    signal = 0.7 * np.sin(phase) + 0.3 * np.sin(2 * phase)
    
    envelope = np.ones_like(t)
    attack = int(SAMPLE_RATE * 0.1)
    release = int(SAMPLE_RATE * 0.1)
    envelope[:attack] = np.linspace(0, 1, attack)
    envelope[-release:] = np.linspace(1, 0, release)
    
    waveform = signal * envelope
    # Chuẩn hóa biên độ đạt mức rất lớn (~90 dB SPL)
    waveform = (waveform / np.max(np.abs(waveform))) * 0.35
    return waveform.astype(np.float32)

def generate_traffic_ambient(duration: float = 2.0) -> np.ndarray:
    """Sinh âm thanh mô phỏng tiếng ồn nền đường phố an toàn (tiếng động cơ trầm, không còi)."""
    t = np.linspace(0, duration, int(SAMPLE_RATE * duration), endpoint=False)
    
    # Tiếng ồn ngẫu nhiên có lọc thông thấp (tiếng lốp xe, gió thoảng)
    noise = np.random.normal(0, 1, len(t))
    # Tích lũy để tạo Brown noise (tiếng trầm)
    brown_noise = np.cumsum(noise)
    brown_noise = brown_noise / np.max(np.abs(brown_noise))
    
    # Âm thanh máy nổ xe máy rền nhẹ 80Hz - 160Hz
    engine_hum = 0.3 * np.sin(2 * np.pi * 95 * t) + 0.2 * np.sin(2 * np.pi * 190 * t)
    
    combined = 0.6 * brown_noise + 0.4 * engine_hum
    # Âm lượng vừa phải (~55 dB SPL)
    waveform = (combined / np.max(np.abs(combined))) * 0.015
    return waveform.astype(np.float32)

def main():
    print(f"Bắt đầu tạo dữ liệu âm thanh mẫu tại: {OUTPUT_DIR}")
    
    # 1. Còi xe máy / ô tô
    horn = generate_horn_sample()
    wavfile.write(OUTPUT_DIR / "horn_sample.wav", SAMPLE_RATE, (horn * 32767).astype(np.int16))
    print(" -> Tạo thành công: horn_sample.wav")
    
    # 2. Còi xe cứu thương
    siren = generate_ambulance_siren()
    wavfile.write(OUTPUT_DIR / "ambulance_siren.wav", SAMPLE_RATE, (siren * 32767).astype(np.int16))
    print(" -> Tạo thành công: ambulance_siren.wav")
    
    # 3. Môi trường an toàn
    traffic = generate_traffic_ambient()
    wavfile.write(OUTPUT_DIR / "ambient_traffic.wav", SAMPLE_RATE, (traffic * 32767).astype(np.int16))
    print(" -> Tạo thành công: ambient_traffic.wav")
    
    print("Hoàn tất tạo bộ dữ liệu kiểm thử!")

if __name__ == "__main__":
    main()
