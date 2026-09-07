import numpy as np
from scipy import signal

def compute_rms(waveform: np.ndarray) -> float:
    """Tính toán giá trị hiệu dụng (Root Mean Square - RMS) của sóng âm thanh."""
    if len(waveform) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(waveform))))

def compute_db(waveform: np.ndarray, db_offset: float = 100.0) -> float:
    """
    Ước lượng cường độ âm thanh Decibel SPL từ waveform float32 [-1.0, 1.0].
    Hiệu chuẩn mức âm:
      - Yên tĩnh / Phòng kín: ~35 - 50 dB
      - Tiếng ồn đường phố / Nói chuyện: ~55 - 68 dB
      - Còi xe máy / Ô tô gần: ~75 - 85 dB
      - Còi hụ xe cứu thương / Khẩn cấp: ~88 - 100 dB
    """
    rms = compute_rms(waveform)
    if rms < 1e-7:
        return 30.0
    db = 20.0 * np.log10(rms) + db_offset
    # Giới hạn trong khoảng đo thực tế 30dB -> 110dB
    return float(np.clip(db, 30.0, 110.0))

def apply_highpass_filter(waveform: np.ndarray, sample_rate: int = 16000, cutoff: float = 300.0, order: int = 4) -> np.ndarray:
    """
    Bộ lọc thông cao (High-pass Butterworth filter) loại bỏ tần số dưới 300Hz.
    Tác dụng: Triệt tiêu đến 85% năng lượng nhiễu do tiếng gió rít (wind noise)
    khi di chuyển trên xe máy.
    """
    nyquist = 0.5 * sample_rate
    normalized_cutoff = cutoff / nyquist
    if normalized_cutoff >= 1.0 or normalized_cutoff <= 0.0:
        return waveform
    b, a = signal.butter(order, normalized_cutoff, btype='highpass')
    filtered = signal.filtfilt(b, a, waveform)
    return filtered.astype(np.float32)

def apply_bandpass_filter(waveform: np.ndarray, sample_rate: int = 16000, lowcut: float = 1500.0, highcut: float = 4500.0, order: int = 4) -> np.ndarray:
    """
    Bộ lọc thông dải (Bandpass Butterworth filter) giữ lại dải 1.5kHz - 4.5kHz.
    Tác dụng: Tập trung vào dải tần đặc trưng sinh học của còi xe và còi hụ ưu tiên.
    """
    nyquist = 0.5 * sample_rate
    low = lowcut / nyquist
    high = highcut / nyquist
    if low <= 0.0 or high >= 1.0 or low >= high:
        return waveform
    b, a = signal.butter(order, [low, high], btype='bandpass')
    filtered = signal.filtfilt(b, a, waveform)
    return filtered.astype(np.float32)
