import sys
import time
from pathlib import Path
import unittest
import numpy as np
from scipy.io import wavfile

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))

from data_contract import UserPreferenceProfile, RouteScenario
from engine.decision_engine import DecisionEngine
from engine.main_engine import MainEngine
from engine.haptic_controller import get_vibration_js


class TestEndToEndSystemIntegration(unittest.TestCase):
    def setUp(self):
        self.decision_engine = DecisionEngine(tau_cutoff=9.0, lambda_ari=0.6)
        self.samples_dir = Path(__file__).resolve().parent / "test_samples"

    def test_pre_trip_to_on_trip_flow(self):
        origin = "District 1"
        destination = "Thu Duc City"
        profile = UserPreferenceProfile.balanced()

        decision_resp = self.decision_engine.plan_trip(
            origin=origin,
            destination=destination,
            profile=profile,
            orig_coords=[106.6578, 10.7725],
            dest_coords=[106.7722, 10.8507],
        )

        self.assertIsNotNone(decision_resp)
        self.assertGreater(len(decision_resp.scenarios), 0)

        recommended = decision_resp.get_recommended_scenario()
        self.assertIsNotNone(recommended)
        self.assertTrue(recommended.is_recommended)
        self.assertTrue(len(recommended.xai_explanation) > 0)
        self.assertLessEqual(recommended.ari_max, 9.0)

        tradeoff_matrix = decision_resp.get_tradeoff_matrix()
        self.assertGreater(len(tradeoff_matrix), 0)

    def test_audio_pipeline_sample_detection(self):
        main_engine = MainEngine.get_instance()

        horn_path = self.samples_dir / "horn_sample.wav"
        if not horn_path.exists():
            horn_path = self.samples_dir / "horn_motorbike.wav"

        siren_path = self.samples_dir / "ambulance_siren.wav"
        ambient_path = self.samples_dir / "ambient_traffic.wav"
        if not ambient_path.exists():
            ambient_path = self.samples_dir / "ambient_street.wav"

        if horn_path.exists():
            sr, data = wavfile.read(str(horn_path))
            waveform = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)
            payload = main_engine.infer(waveform, sample_rate=sr, trigger_haptic=False)
            self.assertIsNotNone(payload)
            self.assertTrue(payload.is_danger)
            self.assertEqual(payload.danger_type, "VEHICLE_HORN")
            vib_js = get_vibration_js(payload.danger_type)
            self.assertIn("150, 100, 150", vib_js)

        if siren_path.exists():
            sr, data = wavfile.read(str(siren_path))
            waveform = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)
            payload = main_engine.infer(waveform, sample_rate=sr, trigger_haptic=False)
            self.assertIsNotNone(payload)
            self.assertTrue(payload.is_danger)
            self.assertEqual(payload.danger_type, "EMERGENCY_SIREN")
            vib_js = get_vibration_js(payload.danger_type)
            self.assertIn("300, 100, 300, 100, 300", vib_js)

        if ambient_path.exists():
            sr, data = wavfile.read(str(ambient_path))
            waveform = data.astype(np.float32) / (32768.0 if data.dtype == np.int16 else 1.0)
            payload = main_engine.infer(waveform, sample_rate=sr, trigger_haptic=False)
            self.assertIsNotNone(payload)
            self.assertFalse(payload.is_danger)
            self.assertEqual(payload.danger_type, "SAFE")

    def test_latency_and_cpu_benchmarks(self):
        main_engine = MainEngine.get_instance()
        dummy_audio = np.zeros(15600, dtype=np.float32)

        latencies = []
        for _ in range(10):
            t0 = time.perf_counter()
            _ = main_engine.infer(dummy_audio, sample_rate=16000, trigger_haptic=False)
            latencies.append((time.perf_counter() - t0) * 1000.0)

        avg_latency = float(np.mean(latencies[2:]))
        self.assertLess(avg_latency, 65.0)

        try:
            import psutil
            cpu_usage = psutil.cpu_percent(interval=0.1)
            self.assertLess(cpu_usage, 95.0)
        except ImportError:
            pass


if __name__ == "__main__":
    unittest.main(verbosity=2)
