"""Load engine components only when requested by callers."""

from importlib import import_module

__all__ = [
    "AudioStreamWorker",
    "DSPAnalyzer",
    "SerialHapticDriver",
    "YAMNetEngine",
    "MainEngine",
    "AudioAIEngine",
    "get_vibration_js",
]

_MODULES = {
    "AudioStreamWorker": "engine.audio_stream",
    "DSPAnalyzer": "engine.dsp_filter",
    "SerialHapticDriver": "engine.haptic_controller",
    "get_vibration_js": "engine.haptic_controller",
    "YAMNetEngine": "engine.model_inference",
    "MainEngine": "engine.main_engine",
    "AudioAIEngine": "engine.main_engine",
}


def __getattr__(name):
    if name not in _MODULES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    value = getattr(import_module(_MODULES[name]), name)
    globals()[name] = value
    return value
