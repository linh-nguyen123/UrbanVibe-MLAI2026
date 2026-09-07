"""
URBANVIBE - REALTIME STREAMING CLI DEMO (BẢN MẪU PIPELINE THỜI GIAN THỰC)
Mô phỏng luồng xử lý liên tục từ Microphone thời gian thực với cửa sổ trượt (Sliding Window).
Chạy độc lập trên Terminal mà không cần giao diện Web.
"""

import os
import sys
import warnings

# Triệt tiêu log trước khi nạp bất kỳ module deep learning nào
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

from pathlib import Path
import time
import numpy as np

# Cấu hình stdout UTF-8 cho Windows Terminal
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT_DIR = Path(__file__).resolve().parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from engine.audio_engine import AudioAIEngine

SAMPLE_RATE = 16000
WINDOW_DURATION = 0.975   # Thời lượng 1 frame chuẩn của YAMNet (giây)
WINDOW_SAMPLES = int(SAMPLE_RATE * WINDOW_DURATION)
HOP_DURATION = 0.5        # Bước trượt 0.5 giây (50% overlap)
HOP_SAMPLES = int(SAMPLE_RATE * HOP_DURATION)

def run_simulated_stream_demo():
    """Demo luồng streaming thời gian thực bằng cách giả lập luồng âm thanh liên tục."""
    print("=" * 65)
    print("   URBANVIBE - BẢN MẪU DEMO CHẠY THỜI GIAN THỰC (CLI PIPELINE)   ")
    print("   Mô phỏng luồng âm thanh liên tục 16kHz với Sliding Window     ")
    print("=" * 65)
    
    engine = AudioAIEngine.get_instance()
    
    # Nạp 3 mẫu âm thanh chuẩn để tạo thành 1 chuỗi kịch bản đường phố 10 giây
    sample_dir = ROOT_DIR / "tests" / "test_samples"
    from scipy.io import wavfile
    
    _, s_ambient = wavfile.read(sample_dir / "ambient_traffic.wav")
    _, s_horn = wavfile.read(sample_dir / "horn_sample.wav")
    _, s_siren = wavfile.read(sample_dir / "ambulance_siren.wav")
    
    def to_f32(arr):
        return (arr.astype(np.float32) / 32768.0) if arr.dtype == np.int16 else arr.astype(np.float32)
    
    # Ghép chuỗi âm thanh: 2s êm đềm -> 1.5s còi xe vượt -> 2s êm đềm -> 2.5s xe cứu thương
    full_audio = np.concatenate([
        to_f32(s_ambient),
        to_f32(s_horn),
        to_f32(s_ambient),
        to_f32(s_siren)
    ])
    
    total_len = len(full_audio)
    cursor = 0
    step = 1
    
    print("\n[BẮT ĐẦU GIÁM SÁT ÂM THANH NGOẠI TUYẾN]")
    print(f"{'BƯỚC':<6} | {'THỜI GIAN':<9} | {'CƯỜNG ĐỘ':<9} | {'TRẠNG THÁI':<16} | {'NHÃN NHẬN DIỆN':<28} | {'ĐỘ TRỄ'}")
    print("-" * 88)
    
    while cursor + WINDOW_SAMPLES <= total_len:
        # Cắt 1 cửa sổ trượt 0.975 giây
        frame = full_audio[cursor : cursor + WINDOW_SAMPLES]
        sim_time = cursor / SAMPLE_RATE
        
        # Đưa vào AI Engine
        payload = engine.infer(frame, db_threshold=75.0, conf_threshold=0.35, apply_wind_filter=False)
        
        # Định dạng hiển thị màu / ký hiệu cảnh báo
        if payload.danger_type == "EMERGENCY_SIREN":
            status_badge = "🚨 [CỨU THƯƠNG]"
        elif payload.danger_type == "VEHICLE_HORN":
            status_badge = "⚠️ [CÒI XE]"
        else:
            status_badge = "🟢 [AN TOÀN]"
            
        print(f"#{step:<5} | {sim_time:>5.1f}s - {sim_time+WINDOW_DURATION:>4.1f}s | {payload.db:>5.1f} dB  | {status_badge:<16} | {payload.label:<28} | {payload.latency_ms:>4.1f}ms")
        
        cursor += HOP_SAMPLES
        step += 1
        time.sleep(0.3)  # Giãn cách hiển thị để người xem quan sát dòng chảy sự kiện
        
    print("-" * 88)
    print("Hoàn tất buổi demo chuỗi sự kiện âm thanh đường phố!\n")

if __name__ == "__main__":
    run_simulated_stream_demo()
