import collections
import threading
import numpy as np
import sounddevice as sd

class AudioStreamWorker:
    """
    Background audio capture worker using sounddevice.
    Maintains a thread-safe sliding ring buffer for YAMNet inference.
    """
    def __init__(self, sample_rate: int = 16000, window_duration: float = 0.975):
        self.sample_rate = sample_rate
        self.window_size = int(window_duration * sample_rate)  # 15600 samples
        self.buffer = collections.deque(maxlen=self.window_size)
        self.lock = threading.Lock()
        self.stream = None
        self.is_running = False

    def _audio_callback(self, indata, frames, time_info, status):
        """Audio callback triggered by OS sound driver."""
        if status:
            pass
        mono_data = indata[:, 0]
        with self.lock:
            self.buffer.extend(mono_data)

    def start(self, device: int | None = None):
        """Start microphone stream in a background thread."""
        if self.is_running:
            return
        self.is_running = True
        self.stream = sd.InputStream(
            device=device,
            samplerate=self.sample_rate,
            channels=1,
            dtype="float32",
            callback=self._audio_callback,
            blocksize=int(self.sample_rate * 0.05),  # 50ms block chunks
        )
        self.stream.start()

    def get_latest_window(self) -> np.ndarray:
        """
        Retrieve latest 15,600 samples as float32 array.
        Zero-pads if buffer is not yet full during initial startup.
        """
        with self.lock:
            buf_len = len(self.buffer)
            if buf_len < self.window_size:
                data = np.zeros(self.window_size, dtype=np.float32)
                if buf_len > 0:
                    data[-buf_len:] = list(self.buffer)
                return data
            return np.array(self.buffer, dtype=np.float32)

    def stop(self):
        """Stop capture stream and release microphone."""
        self.is_running = False
        if self.stream is not None:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None
