import numpy as np
from scipy import signal

class DSPAnalyzer:
    """
    DSP Analyzer for UrbanVibe Audio Engine.
    Handles RMS computation, relative dB SPL calibration, bandpass filtering,
    adaptive ambient noise floor tracking, and the Physical Gate arbitration.
    """
    def __init__(
        self,
        db_threshold: float = 75.0,
        delta_threshold: float = 12.0,
        alpha: float = 0.05,
        enable_bandpass: bool = False,
        sample_rate: int = 16000
    ):
        """
        :param db_threshold: Absolute dB SPL threshold for loud hazards (default 75.0 dB)
        :param delta_threshold: Relative sudden jump threshold over ambient floor (+12.0 dB)
        :param alpha: Smoothing factor (EMA) for tracking ambient noise floor
        :param enable_bandpass: Whether to apply a 500Hz-4000Hz bandpass filter
        :param sample_rate: Audio sample rate (standard 16000 Hz)
        """
        self.db_threshold = db_threshold
        self.delta_threshold = delta_threshold
        self.alpha = alpha
        self.enable_bandpass = enable_bandpass
        self.sample_rate = sample_rate
        self.ambient_noise_floor = 55.0  # Initial assumed baseline (dBA)

        # Precompute bandpass SOS filter if enabled
        if self.enable_bandpass:
            self.sos = signal.butter(
                N=4,
                Wn=[500.0, 4000.0],
                btype='bandpass',
                fs=self.sample_rate,
                output='sos'
            )
        else:
            self.sos = None

    def apply_filter(self, waveform: np.ndarray) -> np.ndarray:
        """Apply bandpass filter to highlight horn/siren frequencies (500Hz - 4kHz)."""
        if self.sos is not None and len(waveform) > 0:
            return signal.sosfilt(self.sos, waveform).astype(np.float32)
        return waveform

    @staticmethod
    def calculate_rms(waveform: np.ndarray) -> float:
        """Calculate Root Mean Square (RMS) energy of the audio chunk."""
        if len(waveform) == 0:
            return 0.0
        return float(np.sqrt(np.mean(waveform ** 2)))

    @staticmethod
    def calculate_db_spl(rms: float) -> float:
        """
        Convert RMS to relative Decibel SPL scale.
        Normalized to align standard conversational noise at 50-60 dB
        and nearby horns/sirens at 75-95 dB.
        """
        db = 20.0 * np.log10(rms + 1e-6) + 100.0
        return float(np.clip(db, 30.0, 120.0))

    def update_and_check_gate(self, db: float) -> tuple[bool, float]:
        """
        Evaluate Physical Gate:
        - Check if absolute dB >= db_threshold (75 dB)
        - OR if relative jump Delta dB >= delta_threshold (+12 dB)
        Updates dynamic ambient baseline when sound is non-hazardous (< 68 dB).
        """
        delta_db = db - self.ambient_noise_floor

        # Dynamically track background noise floor during quiet periods
        if db < 68.0:
            self.ambient_noise_floor = (
                (1.0 - self.alpha) * self.ambient_noise_floor + self.alpha * db
            )

        is_physical_danger = (db >= self.db_threshold) or (delta_db >= self.delta_threshold)
        return is_physical_danger, delta_db

    def analyze(self, waveform: np.ndarray) -> tuple[float, float, bool, float]:
        """
        End-to-end DSP analysis pipeline for an audio window.
        Returns:
            (rms, db, is_physical_danger, delta_db)
        """
        filtered = self.apply_filter(waveform)
        rms = self.calculate_rms(filtered)
        db = self.calculate_db_spl(rms)
        is_physical_danger, delta_db = self.update_and_check_gate(db)
        return rms, db, is_physical_danger, delta_db


def compute_rms(waveform: np.ndarray) -> float:
    """Tính toán giá trị hiệu dụng (Root Mean Square - RMS) của sóng âm thanh."""
    if len(waveform) == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(waveform))))


def compute_db(waveform: np.ndarray, db_offset: float = 100.0) -> float:
    """Ước lượng cường độ âm thanh Decibel SPL từ waveform float32 [-1.0, 1.0]."""
    rms = compute_rms(waveform)
    if rms < 1e-7:
        return 30.0
    db = 20.0 * np.log10(rms) + db_offset
    return float(np.clip(db, 30.0, 110.0))


def apply_highpass_filter(
    waveform: np.ndarray, sample_rate: int = 16000, cutoff: float = 300.0, order: int = 4
) -> np.ndarray:
    """Bộ lọc thông cao loại bỏ tần số dưới 300Hz chống gió rít."""
    nyquist = 0.5 * sample_rate
    normalized_cutoff = cutoff / nyquist
    if normalized_cutoff >= 1.0 or normalized_cutoff <= 0.0:
        return waveform
    b, a = signal.butter(order, normalized_cutoff, btype="highpass")
    filtered = signal.filtfilt(b, a, waveform)
    return filtered.astype(np.float32)


def apply_bandpass_filter(
    waveform: np.ndarray,
    sample_rate: int = 16000,
    lowcut: float = 1500.0,
    highcut: float = 4500.0,
    order: int = 4,
) -> np.ndarray:
    """Bộ lọc thông dải 1.5kHz - 4.5kHz tập trung vào còi xe."""
    nyquist = 0.5 * sample_rate
    low = lowcut / nyquist
    high = highcut / nyquist
    if low <= 0.0 or high >= 1.0 or low >= high:
        return waveform
    b, a = signal.butter(order, [low, high], btype="bandpass")
    filtered = signal.filtfilt(b, a, waveform)
    return filtered.astype(np.float32)

