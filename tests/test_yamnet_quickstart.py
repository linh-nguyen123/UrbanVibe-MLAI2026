import sys
import time
from pathlib import Path
import numpy as np
import sounddevice as sd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.tflite_yamnet import YAMNetEngine

print("=" * 55)
print("URBANVIBE - MICROPHONE & ON-DEVICE YAMNET TFLITE TEST")
print("=" * 55)

# 1. Initialize local on-device model
print("\n[1/3] Loading YAMNet TFLite On-Device model (offline 3.7MB)...")
try:
    engine = YAMNetEngine()
    print(" -> Loaded YAMNet TFLite engine successfully!")
except Exception as e:
    print(f" -> Error loading model: {e}")
    sys.exit(1)

# 2. Record audio from physical microphone
SAMPLE_RATE = 16000
DURATION = 0.975  # Standard YAMNet input window (15600 samples)

print(f"\n[2/3] Opening microphone to record {DURATION} seconds...")
print(" -> Make sound (whistle, clap, talk)...")
try:
    recording = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        channels=1,
        dtype="float32",
    )
    sd.wait()
    waveform = np.squeeze(recording)
    print(" -> Recorded audio successfully!")
except Exception as e:
    print(f" -> Microphone unavailable or permission denied: {e}")
    sys.exit(1)

# 3. Analyze audio and run AI inference
print("\n[3/3] Analyzing audio with Dual-Threshold Gate...")
start_time = time.time()
payload = engine.process_audio(waveform)
latency = (time.time() - start_time) * 1000

print("\n" + "-" * 50)
print("             AUDIO ANALYSIS RESULT             ")
print("-" * 50)
print(f"Sound Level: {payload.db:.1f} dB SPL")
print(f"Hazard Status: {payload.danger_type} (Danger: {payload.is_danger})")
print(f"Identified Label: {payload.label} ({payload.confidence * 100:.1f}%)")
print(f"Processing Latency: {latency:.2f} ms")
print("-" * 50)
print("Audio & Model Pipeline operational.")