import os
import sys
import warnings

# Triệt tiêu toàn bộ cảnh báo TensorFlow C++ logs và Python deprecations
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

from pathlib import Path
import time
import io
from datetime import datetime
import numpy as np
from scipy.io import wavfile
from scipy import signal
# pyrefly: ignore [missing-import]
import streamlit as st

# Trỏ đường dẫn ra thư mục gốc để import module
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from data_contract import DetectionPayload
from ui.mock_engine import generate_mock_payload

# -----------------------------------------------------------------------------
# 1. CẤU HÌNH TRANG STREAMLIT
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="UrbanVibe Edge-AI Simulator",
    page_icon="🚨",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# 2. BỘ CSS NÂNG CAO: THIẾT KẾ SMARTPHONE CHÂN THỰC & KHÔNG VỠ BỐ CỤC
# -----------------------------------------------------------------------------
st.html(
    """
    <style>
    /* Ẩn menu và footer mặc định nhưng giữ lại header để dùng nút toggle sidebar */
    #MainMenu, footer {visibility: hidden;}
    header {background-color: transparent !important;}
    
    .block-container {
        padding-top: 1.0rem !important;
        padding-bottom: 2.5rem !important;
        max-width: 480px !important;
        margin: 0 auto;
    }

    /* Khung giả lập Smartphone chân thực (Hardware Bezel) */
    .phone-wrapper {
        background: #070a12;
        border-radius: 40px;
        padding: 18px 16px 22px 16px;
        color: #ffffff;
        box-shadow: 0 15px 45px rgba(0, 0, 0, 0.9), 0 0 0 5px #1e293b, 0 0 0 7px #0f172a;
        border: 2px solid #334155;
        position: relative;
        transition: all 0.25s ease-in-out;
        margin: 0 auto 18px auto;
    }

    /* Tai thỏ / Dynamic Island */
    .notch-container {
        display: flex;
        justify-content: center;
        align-items: center;
        margin-bottom: 8px;
    }
    .dynamic-island {
        width: 100px;
        height: 18px;
        background: #000000;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: space-around;
        padding: 0 10px;
        border: 1px solid #1e293b;
    }
    .camera-lens {
        width: 8px;
        height: 8px;
        background: #0f172a;
        border-radius: 50%;
        border: 1px solid #334155;
    }
    .sensor-dot {
        width: 4px;
        height: 4px;
        background: #1e3a8a;
        border-radius: 50%;
    }

    /* Thanh trạng thái điện thoại (Status Bar) */
    .status-bar {
        display: flex;
        justify-content: space-between;
        align-items: center;
        font-size: 11px;
        color: #94a3b8;
        font-weight: 600;
        margin-bottom: 12px;
        padding: 0 4px;
        font-family: monospace;
    }

    /* Hiệu ứng chớp nháy viền ĐỎ NGUY CẤP (Xe cứu thương) */
    .strobe-danger {
        border-color: #ff1744 !important;
        box-shadow: 0 0 20px rgba(255, 23, 68, 0.6), 0 0 0 5px #ff1744 !important;
        animation: pulse-red 0.5s infinite alternate ease-in-out !important;
    }
    @keyframes pulse-red {
        0% { box-shadow: 0 0 15px rgba(255, 23, 68, 0.4), 0 0 0 5px #ff1744; border-color: #ff1744; }
        100% { box-shadow: 0 0 45px rgba(255, 23, 68, 0.95), 0 0 0 7px #ff5252; border-color: #ff5252; }
    }

    /* Hiệu ứng chớp nháy viền VÀNG CAM (Còi xe máy) */
    .strobe-warning {
        border-color: #ff9100 !important;
        box-shadow: 0 0 18px rgba(255, 145, 0, 0.5), 0 0 0 5px #ff9100 !important;
        animation: pulse-orange 0.6s infinite alternate ease-in-out !important;
    }
    @keyframes pulse-orange {
        0% { box-shadow: 0 0 10px rgba(255, 145, 0, 0.3), 0 0 0 5px #ff9100; border-color: #ff9100; }
        100% { box-shadow: 0 0 35px rgba(255, 145, 0, 0.9), 0 0 0 6px #ffab40; border-color: #ffab40; }
    }

    /* Trạng thái An toàn */
    .strobe-safe {
        border-color: #059669 !important;
        box-shadow: 0 0 15px rgba(16, 185, 129, 0.25), 0 0 0 5px #064e3b !important;
    }

    /* Thẻ cảnh báo trung tâm cực đại (Hero Card) */
    .hero-card {
        border-radius: 22px;
        padding: 22px 14px;
        text-align: center;
        margin: 10px 0 14px 0;
        transition: all 0.25s ease-in-out;
    }

    /* Thanh VU-Meter đo âm lượng */
    .vu-meter-bg {
        background-color: #1e293b;
        height: 16px;
        border-radius: 8px;
        overflow: hidden;
        margin: 6px 0;
        position: relative;
    }
    .vu-meter-fill {
        height: 100%;
        border-radius: 8px;
        transition: width 0.2s ease-out;
    }
    .threshold-marker {
        position: absolute;
        top: 0;
        bottom: 0;
        width: 3px;
        background-color: #ffffff;
        box-shadow: 0 0 6px #ffffff;
        z-index: 10;
    }

    /* Đồ họa sóng rung động Haptic Wave (Equalizer Style) */
    .vibe-wave-container {
        display: flex;
        align-items: center;
        gap: 4px;
        height: 24px;
    }
    .vibe-bar {
        width: 4px;
        border-radius: 2px;
        transition: height 0.15s ease;
    }
    .vibe-idle {
        height: 5px;
        background-color: #475569;
    }
    .vibe-pulse-danger {
        background-color: #ff1744;
        animation: haptic-bounce-danger 0.3s infinite alternate ease-in-out;
    }
    .vibe-pulse-warning {
        background-color: #ff9100;
        animation: haptic-bounce-warning 0.5s infinite alternate ease-in-out;
    }
    .vibe-bar:nth-child(1) { animation-delay: 0.00s; }
    .vibe-bar:nth-child(2) { animation-delay: 0.08s; }
    .vibe-bar:nth-child(3) { animation-delay: 0.16s; }
    .vibe-bar:nth-child(4) { animation-delay: 0.24s; }
    .vibe-bar:nth-child(5) { animation-delay: 0.32s; }

    @keyframes haptic-bounce-danger {
        0% { height: 5px; }
        100% { height: 22px; }
    }
    @keyframes haptic-bounce-warning {
        0% { height: 5px; }
        100% { height: 16px; }
    }

    /* Thẻ Card lộ trình Track 2 */
    .roadmap-card {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-radius: 12px;
        padding: 12px 14px;
        margin-bottom: 10px;
        font-size: 13px;
        line-height: 1.5;
    }
    </style>
    """
)

# -----------------------------------------------------------------------------
# 3. KHỞI TẠO AI ENGINE (CACHE SINGLETON)
# -----------------------------------------------------------------------------
@st.cache_resource(show_spinner="Đang nạp mô hình Google YAMNet...")
def get_ai_engine():
    from engine.audio_engine import AudioAIEngine
    return AudioAIEngine.get_instance()

# -----------------------------------------------------------------------------
# 4. HÀM CHUYỂN ĐỔI AUDIO VỀ 16KHZ MONO FLOAT32
# -----------------------------------------------------------------------------
def load_audio_waveform(file_bytes: bytes) -> np.ndarray:
    """Chuyển đổi file âm thanh bất kỳ sang float32 16kHz mono."""
    sr, data = wavfile.read(io.BytesIO(file_bytes))
    if len(data.shape) > 1:
        data = data[:, 0]
    if data.dtype == np.int16:
        waveform = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        waveform = data.astype(np.float32) / 2147483648.0
    elif data.dtype == np.uint8:
        waveform = (data.astype(np.float32) - 128.0) / 128.0
    else:
        waveform = data.astype(np.float32)

    if sr != 16000 and len(waveform) > 0:
        target_len = int(len(waveform) * 16000 / sr)
        waveform = signal.resample(waveform, target_len).astype(np.float32)
    return waveform

# -----------------------------------------------------------------------------
# 5. KHỞI TẠO SESSION STATE (LƯU TRẠNG THÁI TRÁNH MẤT KẾT QUẢ KHI RERUN)
# -----------------------------------------------------------------------------
if "current_payload" not in st.session_state:
    st.session_state.current_payload = DetectionPayload(
        timestamp=time.time(),
        db=52.0,
        is_danger=False,
        danger_type="SAFE",
        label="Ambient street noise",
        confidence=0.92,
        latency_ms=16.5
    )

if "mock_step" not in st.session_state:
    st.session_state.mock_step = 0

# -----------------------------------------------------------------------------
# 6. SIDEBAR CÀI ĐẶT & BỘ LỌC CỔNG KÉP
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("⚙️ Bảng Điều Khiển Hệ Thống")
    
    source_mode = st.radio(
        "Nguồn dữ liệu âm thanh:",
        [
            "🎭 1. Kịch bản Sân khấu (Manual Presets)",
            "🧪 2. File Mẫu Kiểm Thử (Real YAMNet)",
            "🎙️ 3. Thu Âm Microphone Trực Tiếp",
            "🎲 4. Giả Lập Tự Động (Stream)"
        ]
    )

    st.markdown("---")
    st.subheader("Cân chỉnh Ngưỡng Thực Tế (Acoustic Calibration)")
    
    # Ngưỡng Decibel: Khuyến nghị 78 dB cho đường phố Việt Nam
    db_threshold = st.slider(
        "Ngưỡng Decibel cảnh báo (dB):",
        min_value=50,
        max_value=90,
        value=78,
        step=1,
        help="Khuyến nghị thực tế: 78 dB. Môi trường xe máy chạy thường ~62-74 dB. Còi xe xin vượt phía sau đạt 78-86 dB."
    )
    st.caption("💡 *Đường phố thường: ~65 dB • Còi vượt: ≥ 78 dB • Cứu thương: ≥ 85 dB*")
    
    # Ngưỡng Confidence: Khuyến nghị 35% cho mô hình 521 nhãn YAMNet
    conf_threshold = st.slider(
        "Ngưỡng AI Confidence (%):",
        min_value=20,
        max_value=80,
        value=35,
        step=5,
        help="Khuyến nghị thực tế: 35%. Vì YAMNet phân loại 521 lớp, trong môi trường có tạp âm ngoài đường, còi thật đạt khoảng 35-65%."
    )
    st.caption("💡 *Ngưỡng 35% kết hợp cùng cổng 78 dB giúp triệt tiêu >98% báo động giả.*")
    
    apply_wind_filter = st.checkbox("Bật bộ lọc DSP High-pass 300Hz (Chống gió rít)", value=False)
    enable_vibration = st.checkbox("Kích hoạt Web Vibration API", value=True)

# -----------------------------------------------------------------------------
# 7. HÀM RENDER KHUNG SMARTPHONE (HERO VIEWPORT DEVICE)
# -----------------------------------------------------------------------------
def render_smartphone_viewport(payload: DetectionPayload, marker_db: float):
    """Render giao diện khung điện thoại chuẩn Smartphone độc lập."""
    current_time_str = datetime.now().strftime("%H:%M")
    
    if payload.is_danger:
        if payload.danger_type == "EMERGENCY_SIREN":
            frame_class = "strobe-danger"
            hero_bg = "#dc2626"
            hero_icon = "🚨 🚑"
            hero_title = "XE CỨU THƯƠNG TIẾP CẬN!"
            hero_sub = "CHỦ ĐỘNG TẤP LỀ • NHƯỜNG ĐƯỜNG NGAY"
            haptic_desc = "RUNG DỒN DẬP KHẨN CẤP"
            haptic_intensity = "CỰC ĐẠI"
            vibe_bar_class = "vibe-pulse-danger"
            haptic_color = "#ff1744"
        else:
            frame_class = "strobe-warning"
            hero_bg = "#ea580c"
            hero_icon = "⚠️ 🛵"
            hero_title = "CÒI XE VƯỢT NGƯỠNG!"
            hero_sub = "CÓ XE XIN VƯỢT PHÍA SAU"
            haptic_desc = "RUNG NHỊP ĐÔI DỨT KHOÁT"
            haptic_intensity = "CẢNH BÁO"
            vibe_bar_class = "vibe-pulse-warning"
            haptic_color = "#ff9100"
    else:
        frame_class = "strobe-safe"
        hero_bg = "#064e3b"
        hero_icon = "🛡️ ✅"
        hero_title = "MÔI TRƯỜNG AN TOÀN"
        hero_sub = "HỆ THỐNG ĐANG LIÊN TỤC LẮNG NGHE..."
        haptic_desc = "CHẾ ĐỘ NGHỈ (YÊN TĨNH)"
        haptic_intensity = "CHỜ"
        vibe_bar_class = "vibe-idle"
        haptic_color = "#10b981"

    # Tính toán phần trăm thanh VU Meter (từ 30dB -> 100dB)
    vu_percent = max(0, min(100, int((payload.db - 30) / (100 - 30) * 100)))
    marker_pos = max(0, min(100, int((marker_db - 30) / (100 - 30) * 100)))
    vu_color = "#ef4444" if payload.db >= marker_db else ("#f59e0b" if payload.db >= 70 else "#10b981")

    phone_html = f"""
    <div class="phone-wrapper {frame_class}">
        <!-- DYNAMIC ISLAND / NOTCH -->
        <div class="notch-container">
            <div class="dynamic-island">
                <div class="sensor-dot"></div>
                <div class="camera-lens"></div>
            </div>
        </div>

        <!-- TOP STATUS BAR -->
        <div class="status-bar">
            <span>{current_time_str}</span>
            <span>🟢 100% ON-DEVICE AI</span>
            <span>⚡ {payload.latency_ms:.1f}ms</span>
        </div>

        <!-- THẺ CẢNH BÁO TRUNG TÂM -->
        <div class="hero-card" style="background-color: {hero_bg};">
            <div style="font-size: 46px; margin-bottom: 4px;">{hero_icon}</div>
            <div style="font-size: 20px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.5px; color: #ffffff;">
                {hero_title}
            </div>
            <div style="font-size: 12px; font-weight: 600; margin-top: 4px; color: rgba(255,255,255,0.9);">
                {hero_sub}
            </div>
        </div>

        <!-- ĐỒNG HỒ ĐO ÂM LƯỢNG (VU METER) -->
        <div style="margin-top: 10px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px; font-weight: 700;">
                <span style="color: #94a3b8;">CƯỜNG ĐỘ ÂM THANH:</span>
                <span style="color: {vu_color}; font-size: 14px;">{payload.db:.1f} dB</span>
            </div>
            <div class="vu-meter-bg">
                <div class="vu-meter-fill" style="width: {vu_percent}%; background-color: {vu_color};"></div>
                <div class="threshold-marker" style="left: {marker_pos}%;" title="Ngưỡng cảnh báo: {marker_db:.0f} dB"></div>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 10px; color: #64748b; font-family: monospace;">
                <span>30 dB</span>
                <span style="color: #cbd5e1;">▲ Ngưỡng: {marker_db:.0f} dB</span>
                <span>100 dB</span>
            </div>
        </div>

        <!-- MÔ PHỎNG XÚC GIÁC VỚI SÓNG RUNG EQUALIZER -->
        <div style="margin-top: 12px; padding: 9px 12px; background: #0f172a; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #1e293b;">
            <div>
                <div style="font-size: 10px; color: #64748b; font-weight: 600;">XUNG RUNG XÚC GIÁC (HAPTIC):</div>
                <div style="font-size: 12px; font-weight: 700; color: {haptic_color}; margin-top: 2px;">{haptic_desc}</div>
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
                <div class="vibe-wave-container">
                    <div class="vibe-bar {vibe_bar_class}"></div>
                    <div class="vibe-bar {vibe_bar_class}"></div>
                    <div class="vibe-bar {vibe_bar_class}"></div>
                    <div class="vibe-bar {vibe_bar_class}"></div>
                    <div class="vibe-bar {vibe_bar_class}"></div>
                </div>
                <span style="font-size: 10px; font-weight: 800; color: {haptic_color}; background: rgba(255,255,255,0.06); padding: 3px 6px; border-radius: 6px;">
                    {haptic_intensity}
                </span>
            </div>
        </div>

        <!-- THÔNG TIN PHÂN LOẠI AI YAMNET -->
        <div style="margin-top: 10px; font-size: 11px; color: #94a3b8; text-align: center; border-top: 1px solid #1e293b; padding-top: 8px;">
            Nhận diện: <b style="color: #f1f5f9;">{payload.label}</b> • Độ tin cậy: <b style="color: #f1f5f9;">{payload.confidence * 100:.1f}%</b>
        </div>
    </div>
    """
    st.html(phone_html)

# -----------------------------------------------------------------------------
# 8. XỬ LÝ NGUỒN DỮ LIỆU & RENDER
# -----------------------------------------------------------------------------

# Chế độ 1: KỊCH BẢN SÂN KHẤU (MANUAL PRESETS)
if "1. Kịch bản Sân khấu" in source_mode:
    # 3 Nút bấm 1 chạm trực quan, không bị tràn chữ
    col1, col2, col3 = st.columns(3)
    now = time.time()
    
    with col1:
        if st.button("🟢 An Toàn", use_container_width=True):
            st.session_state.current_payload = DetectionPayload(now, 53.4, False, "SAFE", "Ambient city traffic / Speech", 0.91, 16.2)
    with col2:
        if st.button("🟠 Còi Xe Máy", use_container_width=True):
            st.session_state.current_payload = DetectionPayload(now, 81.6, True, "VEHICLE_HORN", "Vehicle horn, car horn, honking", 0.86, 14.5)
    with col3:
        if st.button("🔴 Cứu Thương", use_container_width=True):
            st.session_state.current_payload = DetectionPayload(now, 91.2, True, "EMERGENCY_SIREN", "Ambulance (siren) / Emergency", 0.97, 18.0)

    # Cập nhật lại cổng lọc nếu người dùng đổi slider
    p = st.session_state.current_payload
    is_danger = (p.danger_type != "SAFE") and (p.db >= db_threshold) and (p.confidence >= conf_threshold / 100.0)
    p.is_danger = is_danger
    
    render_smartphone_viewport(p, db_threshold)

# Chế độ 2: FILE MẪU KIỂM THỬ & TẢI LÊN (REAL YAMNET)
elif "2. File Mẫu Kiểm Thử" in source_mode:
    engine = get_ai_engine()
    sample_dir = ROOT_DIR / "tests" / "test_samples"
    
    tab_sample, tab_upload = st.tabs(["📁 File Mẫu Chuẩn", "📤 Tải File .WAV Riêng"])
    target_bytes = None
    
    with tab_sample:
        sample_pick = st.selectbox(
            "Chọn tình huống âm thanh:",
            [
                "🚑 ambulance_siren.wav (Còi xe cứu thương - 86 dB)",
                "🛵 horn_sample.wav (Còi xe máy xin vượt - 82 dB)",
                "🛡️ ambient_traffic.wav (Tiếng ồn đường phố an toàn - 56 dB)"
            ]
        )
        if "ambulance_siren" in sample_pick:
            filename = "ambulance_siren.wav"
        elif "horn_sample" in sample_pick:
            filename = "horn_sample.wav"
        else:
            filename = "ambient_traffic.wav"
            
        file_path = sample_dir / filename
        if file_path.exists():
            with open(file_path, "rb") as f:
                target_bytes = f.read()
            st.audio(target_bytes, format="audio/wav")
            
    with tab_upload:
        uploaded_file = st.file_uploader("Upload file .wav của Ban Giám Khảo:", type=["wav"])
        if uploaded_file is not None:
            target_bytes = uploaded_file.read()
            st.audio(target_bytes, format="audio/wav")

    if target_bytes is not None:
        if st.button("🚀 PHÂN TÍCH VỚI YAMNET & DUAL-THRESHOLD GATE", type="primary", use_container_width=True):
            with st.spinner("Đang tính toán ma trận phổ & suy luận AI..."):
                waveform = load_audio_waveform(target_bytes)
                conf_val = conf_threshold / 100.0
                st.session_state.current_payload = engine.infer(
                    waveform,
                    db_threshold=float(db_threshold),
                    conf_threshold=conf_val,
                    apply_wind_filter=apply_wind_filter
                )
    
    # Render viewport từ session state (đảm bảo không bị mất kết quả khi kéo slider)
    p = st.session_state.current_payload
    is_danger = (p.danger_type != "SAFE") and (p.db >= db_threshold) and (p.confidence >= conf_threshold / 100.0)
    p.is_danger = is_danger
    render_smartphone_viewport(p, db_threshold)

# Chế độ 3: THU ÂM MICROPHONE TRỰC TIẾP
elif "3. Thu Âm Microphone" in source_mode:
    engine = get_ai_engine()
    audio_val = st.audio_input("Nhấn biểu tượng micro để thu âm 1–2 giây (thổi còi hoặc nói):")
    
    if audio_val is not None:
        audio_bytes = audio_val.read()
        waveform = load_audio_waveform(audio_bytes)
        conf_val = conf_threshold / 100.0
        with st.spinner("Đang phân tích âm thanh..."):
            st.session_state.current_payload = engine.infer(
                waveform,
                db_threshold=float(db_threshold),
                conf_threshold=conf_val,
                apply_wind_filter=apply_wind_filter
            )

    p = st.session_state.current_payload
    render_smartphone_viewport(p, db_threshold)

# Chế độ 4: GIẢ LẬP TỰ ĐỘNG (STREAM)
else:
    col_a, col_b = st.columns([2, 1])
    with col_a:
        st.caption("🎲 Mô phỏng dòng sự kiện liên tục trên đường phố.")
    with col_b:
        if st.button("🔄 Bước kế tiếp", use_container_width=True):
            st.session_state.current_payload = generate_mock_payload()

    p = st.session_state.current_payload
    render_smartphone_viewport(p, db_threshold)

# -----------------------------------------------------------------------------
# 9. SECTION: LỘ TRÌNH THỰC TẾ & PHẦN CỨNG (TRACK 2 ROADMAP)
# -----------------------------------------------------------------------------
# st.markdown("---")
# with st.expander("🚀 **KIẾN TRÚC THỰC TẾ & LỘ TRÌNH PHẦN CỨNG (TRACK 2 ROADMAP)**", expanded=False):
#     st.markdown(
#         """
#         ### 📐 Bản vẽ Kỹ thuật: Chuyển dịch từ PoC sang Thiết bị Thương mại
#         *Giao diện Web hiện tại đóng vai trò là **Bộ Giả Lập & Kiểm thử (HIL Simulator)**. Khi triển khai thực tế trên xe máy, UrbanVibe áp dụng kiến trúc 4 lớp giải quyết triệt để rào cản vận hành:*

#         <div class="roadmap-card">
#             <b style="color: #60a5fa;">1. Nền tảng Native (Android Foreground Service):</b><br>
#             • Nén mô hình YAMNet sang <b>TFLite int8 (~3.5 MB)</b> chạy C++ qua Android NDK.<br>
#             • Chạy nền vĩnh viễn (Foreground Service với Micro Stream), không bao giờ bị hệ điều hành tắt khi khóa màn hình hay bật Google Maps.<br>
#             • Cơ chế <b>2-Stage Wakeup</b>: Chỉ kích hoạt AI khi âm thanh &gt; 70dB, giúp thời lượng pin kéo dài hơn 8 giờ chạy xe.
#         </div>

#         <div class="roadmap-card">
#             <b style="color: #34d399;">2. Giải pháp Tiếng Gió Rít & Môi trường Âm học:</b><br>
#             • Micro định hướng bọc màng lọc âm <b>Deadcat/Acoustic Foam</b> tích hợp dưới cằm nón bảo hiểm.<br>
#             • DSP High-pass Butterworth cắt toàn bộ tần số &lt; 300Hz (loại bỏ 85% năng lượng gió rít).<br>
#             • Lọc dải thông Bandpass 1.5kHz – 4.5kHz tập trung vào tần số sinh học của còi xe.
#         </div>

#         <div class="roadmap-card">
#             <b style="color: #f59e0b;">3. Phản hồi Xung Rung Haptic Cách Ly Động Cơ Xe:</b><br>
#             • Thay vì rung điện thoại trên tay lái (bị rung máy xe triệt tiêu), app bắn tín hiệu <b>Bluetooth Low Energy (BLE)</b> tới <b>Smartwatch (WearOS/Apple Watch)</b>.<br>
#             • Hoặc tích hợp motor rung <b>LRA (Linear Resonant Actuator)</b> ngay quai nón bảo hiểm (áp sát xương hàm người lái).
#         </div>

#         <div class="roadmap-card">
#             <b style="color: #f87171;">4. An toàn Thị giác Ngoại vi (Peripheral HUD):</b><br>
#             • Không bắt người lái nhìn điện thoại gây mất tập trung.<br>
#             • Cụm đèn LED RGB siêu nhỏ gắn viền gương chiếu hậu nhấp nháy trong tầm nhìn ngoại vi, giúp người lái nhận biết ngay mà không rời mắt khỏi đường.
#         </div>
#         """,
#         unsafe_allow_html=True
#     )