"""Run: python tests/benchmark_model_inference.py

Reports full-process RSS including TensorFlow, plus incremental load RSS.
The mandatory target applies to full-process peak RSS and warm p95 latency.
"""
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import psutil


def main():
    process = psutil.Process()
    initial_rss = process.memory_info().rss
    start = time.perf_counter()
    from engine.model_inference import YAMNetEngine
    engine = YAMNetEngine()
    load_ms = (time.perf_counter() - start) * 1000
    loaded_rss = process.memory_info().rss
    timings = []
    peak_rss = loaded_rss
    waveform = np.zeros(engine.window_size, dtype=np.float32)
    for _ in range(100):
        start = time.perf_counter()
        engine.infer(waveform)
        timings.append((time.perf_counter() - start) * 1000)
        peak_rss = max(peak_rss, process.memory_info().rss)
    info = process.memory_info()
    peak_rss = max(peak_rss, getattr(info, "peak_wset", 0))
    report = dict(model_bytes=(engine.model_dir / "yamnet.tflite").stat().st_size,
                  load_ms=load_ms, process_peak_rss_mb=peak_rss / 1e6,
                  load_rss_delta_mb=(loaded_rss - initial_rss) / 1e6,
                  latency_median_ms=float(np.median(timings)),
                  latency_p95_ms=float(np.percentile(timings, 95)))
    report["passes_targets"] = (report["process_peak_rss_mb"] < 45 and
                                report["latency_p95_ms"] < 20)
    print(json.dumps(report, indent=2))
    if not report["passes_targets"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
