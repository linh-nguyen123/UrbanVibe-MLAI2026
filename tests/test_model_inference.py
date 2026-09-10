"""Run with python -m pytest tests/test_model_inference.py -v."""
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from scipy.io import wavfile
from scipy.signal import resample_poly

from engine.model_inference import YAMNetEngine, is_dangerous

SAMPLES = Path(__file__).parent / "test_samples"


def read_audio(filename):
    rate, audio = wavfile.read(SAMPLES / filename)
    if np.issubdtype(audio.dtype, np.signedinteger):
        audio = audio.astype(np.float32) / (2 ** (np.iinfo(audio.dtype).bits - 1))
    elif audio.dtype == np.uint8:
        audio = (audio.astype(np.float32) - 128) / 128
    else:
        audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if rate != 16000:
        divisor = int(np.gcd(rate, 16000))
        audio = resample_poly(audio, 16000 // divisor, rate // divisor)
    return audio.astype(np.float32)


@pytest.fixture(scope="module")
def engine():
    # A network request during model construction or inference must fail the test.
    with patch("socket.socket.connect", side_effect=AssertionError("Offline inference required")):
        yield YAMNetEngine()


@pytest.mark.parametrize("label,confidence,db,expected", [
    ("Siren", 0.82, 81.4, True),
    ("Ambulance (siren)", 0.82, 81.4, True),
    ("Alarm", 0.75, 93.35, True),
    ("Alarm", 0.60, 93.35, False),
    ("Alarm", 0.75, 75, False),
    ("Vehicle horn, car horn, honking", 0.82, 81.4, True),
    ("Siren", 0.60, 90, False),
    ("Siren", 0.61, 75, False),
    ("Siren", 0.99, 74, False),
    ("Speech", 0.99, 90, False),
    ("Siren", float("nan"), 90, False),
])
def test_strict_gate(label, confidence, db, expected):
    assert is_dangerous(label, confidence, db) is expected


@pytest.mark.parametrize("filename", ["horn_sample.wav", "ambulance_siren.wav"])
def test_real_hazards(engine, filename):
    audio = read_audio(filename)
    results = [engine.infer(audio[start:start + engine.window_size])
               for start in range(0, len(audio), 7800)]
    assert any(r["is_danger"] for r in results), results
    for result in results:
        assert set(result) == {"is_danger", "label", "confidence", "db"}
        if result["is_danger"]:
            assert result["db"] > 75 and result["confidence"] > 0.60


@pytest.mark.parametrize("filename", ["ambient_traffic.wav", "ambient_street.wav"])
def test_real_quiet_background(engine, filename):
    audio = read_audio(filename)
    results = [engine.infer(audio[start:start + engine.window_size])
               for start in range(0, len(audio), engine.window_size)]
    assert all(r["db"] < 75 for r in results), results
    assert all(not r["is_danger"] for r in results), results


def test_quiet_siren_cannot_bypass_db_gate(engine):
    audio = read_audio("ambulance_siren.wav")[:engine.window_size] * 0.001
    result = engine.infer(audio)
    assert result["db"] < 75
    assert result["is_danger"] is False


@pytest.mark.parametrize("label", ["Siren", "Ambulance (siren)"])
def test_pipeline_with_controlled_scores(engine, label):
    # Isolate decision logic from the model's accuracy on a particular recording.
    scores = np.zeros(len(engine.class_names), dtype=np.float32)
    scores[engine.class_names.index(label)] = 0.82
    audio = read_audio("ambulance_siren.wav")[:engine.window_size]
    with patch.object(engine, "_predict", return_value=scores):
        assert engine.infer(audio)["is_danger"] is True
        assert engine.infer(audio * 0.001)["is_danger"] is False


@pytest.mark.parametrize("audio", [np.ones((10, 2)), np.array([np.nan]),
                                   np.array([1.1]), np.ones(10, dtype=np.int16)])
def test_invalid_audio(engine, audio):
    with pytest.raises(ValueError):
        engine.infer(audio)
