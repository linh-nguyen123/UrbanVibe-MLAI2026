import sys
from pathlib import Path
import time
import streamlit as st

# Trỏ đường dẫn ra thư mục gốc
sys.path.append(str(Path(__file__).resolve().parent.parent))

from ui.mock_engine import generate_mock_payload

st.set_page_config(page_title="UrbanVibe Dashboard", page_icon="🚨", layout="centered")

st.title("🚨 UrbanVibe – Acoustic Safety System")
st.caption("Giao diện giám sát an toàn âm thanh thời gian thực dành cho người khiếm thính")

# Khung chứa nội dung tự làm mới
status_container = st.empty()
metrics_container = st.empty()

# Nút bật/tắt giám sát
is_running = st.toggle("Kích hoạt giám sát âm thanh", value=True)

while is_running:
    # Đọc luồng dữ liệu (hiện tại từ mock, sau này đổi sang engine thật)
    payload = generate_mock_payload()

    # Cấu hình màu sắc trạng thái
    if payload.is_danger:
        if payload.danger_type == "EMERGENCY_SIREN":
            bg_color = "#ff1744"
            status_text = "🚨 CẢNH BÁO: XE CỨU THƯƠNG / CỨU HỎA TIẾP CẬN!"
        else:
            bg_color = "#ff9100"
            status_text = "⚠️ CẢNH BÁO: TIẾNG CÒI XE VƯỢT NGƯỠNG!"
        text_color = "#ffffff"
    else:
        bg_color = "#00e676"
        status_text = "✅ MÔI TRƯỜNG AN TOÀN"
        text_color = "#003300"

    # Hiển thị thẻ cảnh báo thị giác lớn
    status_container.markdown(
        f"""
        <div style="background-color: {bg_color}; padding: 25px; border-radius: 12px; text-align: center; color: {text_color};">
            <h2 style="margin: 0; font-size: 24px;">{status_text}</h2>
            <p style="margin: 8px 0 0 0; font-size: 16px;"><b>Nhận diện:</b> {payload.label} ({payload.confidence * 100:.1f}%)</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    # Hiển thị các chỉ số kỹ thuật
    with metrics_container.container():
        col1, col2, col3 = st.columns(3)
        col1.metric("Cường độ (dB)", f"{payload.db:.1f} dB")
        col2.metric("Độ tin cậy AI", f"{payload.confidence * 100:.1f}%")
        col3.metric("Độ trễ xử lý", f"{payload.latency_ms:.1f} ms")

    time.sleep(0.5)