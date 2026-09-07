import sys
import time
from pathlib import Path
import numpy as np
from scipy.io import wavfile

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine import AudioStreamWorker, DSPAnalyzer, SerialHapticDriver, YAMNetEngine

def test_dsp_analyzer():
    print("[1/4] Testing DSP Analyzer...")
    dsp = DSPAnalyzer(db_threshold=75.0, delta_threshold=12.0, enable_bandpass=True)

    quiet_sample = np.random.normal(0, 0.001, 15600).astype(np.float32)
    rms_q, db_q, danger_q, delta_q = dsp.analyze(quiet_sample)
    assert not danger_q, "Quiet sound must not trigger danger"

    loud_sample = np.random.normal(0, 0.15, 15600).astype(np.float32)
    rms_l, db_l, danger_l, delta_l = dsp.analyze(loud_sample)
    assert danger_l, "Loud sound must trigger physical gate"
    print("   DSP Analyzer tests passed successfully.")

def test_tflite_yamnet_engine():
    print("[2/4] Testing YAMNet TFLite Engine...")
    engine = YAMNetEngine()

    sample_dir = ROOT_DIR / "tests" / "test_samples"
    for wav_name in ["ambient_street.wav", "horn_motorbike.wav", "ambulance_siren.wav"]:
        wav_path = sample_dir / wav_name
        if not wav_path.exists():
            continue
        sr, data = wavfile.read(str(wav_path))
        waveform = (data.astype(np.float32) / 32767.0)[:15600]

        start_t = time.time()
        payload = engine.process_audio(waveform)
        elapsed = (time.time() - start_t) * 1000

        print(f"   Sample: {wav_name:<22} -> dB: {payload.db:>4.1f} | Danger: {str(payload.is_danger):<5} | Type: {payload.danger_type:<15} | Latency: {payload.latency_ms:.1f}ms")
        assert payload.latency_ms < 30.0, f"Latency {payload.latency_ms}ms exceeds 30ms limit"

    print("   YAMNet Engine benchmarks passed successfully.")

def test_audio_stream_worker():
    print("[3/4] Testing AudioStreamWorker...")
    worker = AudioStreamWorker()
    buf = worker.get_latest_window()
    assert len(buf) == 15600, "Window buffer size must be 15600"
    print("   AudioStreamWorker buffer initialization passed.")

def test_haptic_driver():
    print("[4/4] Testing Haptic Abstraction Layer...")
    driver = SerialHapticDriver(port=None)
    res = driver.trigger("VEHICLE_HORN")
    assert not res, "Unconnected serial should return False safely without error"
    print("   Haptic driver safe fallback passed.")

if __name__ == "__main__":
    print("=" * 60)
    print("URBANVIBE ENGINE FULL PIPELINE TEST")
    print("=" * 60)
    test_dsp_analyzer()
    test_tflite_yamnet_engine()
    test_audio_stream_worker()
    test_haptic_driver()
    print("=" * 60)
    print("ALL TESTS PASSED SUCCESSFULLY")
    print("=" * 60)
