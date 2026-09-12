# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Decision Intelligence & Acoustic Safety Platform
MLAI Hackathon 2026 - Decision Intelligence Challenge (TMA Solutions)

Ứng dụng Dashboard Streamlit 2-Tab:
- Tab 1: 🗺️ Ra Quyết Định Lộ Trình (Pre-Trip Decision Intelligence - MCDA Pareto & XAI)
- Tab 2: 🚨 Giám Sát An Toàn Trên Xe (On-Trip Real-Time Edge Safeguard HUD)
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn import từ thư mục gốc của repository
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import time
import pandas as pd
import streamlit as st

from data_contract import (
    DetectionPayload,
    UserPreferenceProfile,
    RouteScenario,
    DecisionResponse
)
from ui.mock_engine import (
    generate_mock_payload,
    generate_mock_decision_response
)

# ============================================================================
# CẤU HÌNH TRANG STREAMLIT & CUSTOM STYLING (HIGH CONTRAST HUD)
# ============================================================================

st.set_page_config(
    page_title="UrbanVibe: SafeRoute | Decision Intelligence",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Nhúng CSS tối ưu tương phản cao cho người khiếm thính và màn hình ngoài trời
st.markdown("""
<style>
    /* Kiểu dáng chung */
    .metric-card {
        background-color: #1e222d;
        border: 1px solid #2e384d;
        border-radius: 10px;
        padding: 16px;
        text-align: center;
    }
    .hud-box-safe {
        background: linear-gradient(135deg, #0d3b1e 0%, #155724 100%);
        border: 3px solid #28a745;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        color: #d4edda;
        box-shadow: 0 4px 15px rgba(40, 167, 69, 0.2);
    }
    .hud-box-warning {
        background: linear-gradient(135deg, #4a2700 0%, #854d0e 100%);
        border: 3px solid #f59e0b;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        color: #fef3c7;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.3);
    }
    .hud-box-danger {
        background: linear-gradient(135deg, #4c0519 0%, #991b1b 100%);
        border: 4px solid #ef4444;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        color: #fee2e2;
        animation: pulse 1.5s infinite;
        box-shadow: 0 4px 25px rgba(239, 68, 68, 0.4);
    }
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0.7); }
        70% { transform: scale(1.01); box-shadow: 0 0 0 15px rgba(239, 68, 68, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(239, 68, 68, 0); }
    }
    .badge-pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 600;
        margin-right: 6px;
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# KHỞI TẠO SESSION STATE QUẢN LÝ TRẠNG THÁI TOÀN TRÌNH
# ============================================================================

if "origin" not in st.session_state:
    st.session_state.origin = "ĐH Bách Khoa CS1 (Quận 10)"

if "destination" not in st.session_state:
    st.session_state.destination = "Bến xe Miền Đông Mới (TP. Thủ Đức)"

if "profile_key" not in st.session_state:
    st.session_state.profile_key = "BALANCED"

if "selected_scenario_id" not in st.session_state:
    st.session_state.selected_scenario_id = "SCENARIO_B"

if "system_status" not in st.session_state:
    st.session_state.system_status = "HEALTHY"

if "current_payload" not in st.session_state:
    st.session_state.current_payload = generate_mock_payload(force_danger_type="SAFE")


# ============================================================================
# SIDEBAR: THÔNG TIN DỰ ÁN & CƠ CHẾ AN TOÀN FAIL-SAFE
# ============================================================================

with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/traffic-jam.png", width=64)
    st.title("🚨 UrbanVibe")
    st.caption("Acoustic Decision Intelligence & Edge Safeguard")
    
    st.markdown("""
    **MLAI Hackathon 2026**  
    *Track:* **Decision Intelligence (TMA Solutions)**  
    *Phát triển bởi:* Đội thi ĐH Bách Khoa TP.HCM
    """)
    
    st.divider()
    
    st.subheader("🛡️ Trạng Thái An Toàn Hệ Thống")
    st.caption("Cơ chế chống lỗi im lặng (Anti-Silent Failure)")
    
    status_choice = st.radio(
        "Trạng thái phần cứng & cảm biến:",
        options=["HEALTHY", "DEGRADED", "UNAVAILABLE"],
        format_func=lambda x: {
            "HEALTHY": "🟢 HEALTHY (Hoạt động tốt)",
            "DEGRADED": "🟡 DEGRADED (Gió lớn/Nhiễu pô)",
            "UNAVAILABLE": "🔴 UNAVAILABLE (Lỗi cảm biến)"
        }[x],
        index=["HEALTHY", "DEGRADED", "UNAVAILABLE"].index(st.session_state.system_status)
    )
    st.session_state.system_status = status_choice
    
    if st.session_state.system_status == "DEGRADED":
        st.warning("⚠️ Cảnh báo: Tạp âm gió hoặc rung động cơ lớn. Độ nhạy có thể giảm, hãy tăng cường quan sát mắt!")
    elif st.session_state.system_status == "UNAVAILABLE":
        st.error("🚨 NGUY HIỂM: Mất kết nối cảm biến! Hệ thống KHÔNG thể cảnh báo âm thanh. Dựa 100% vào quan sát mắt!")

    st.divider()
    st.markdown("""
    <small>
    🔒 <b>Bảo vệ Dữ liệu:</b> Tuân thủ Nghị định 13/2023/NĐ-CP (Zero Raw Audio Storage trên RAM).<br/>
    📱 <b>Tiếp cận:</b> 0 VNĐ Phần cứng cho 2.5M người khiếm thính.
    </small>
    """, unsafe_allow_html=True)


# ============================================================================
# HEADER CHÍNH CỦA ỨNG DỤNG
# ============================================================================

st.markdown("""
# 🚨 UrbanVibe: SafeRoute
### Nền tảng Trí tuệ Hỗ trợ Ra Quyết định Di chuyển An toàn Dựa trên Dữ liệu Âm thanh Đô thị
""")

# ============================================================================
# 2 TABS CHÍNH: PRE-TRIP DECISION VÀ ON-TRIP HUD
# ============================================================================

tab_pre_trip, tab_on_trip = st.tabs([
    "🗺️ TAB 1: Ra Quyết Định Lộ Trình (Pre-Trip MCDA)",
    "🚨 TAB 2: Giám Sát An Toàn Trên Xe (On-Trip HUD)"
])


# ----------------------------------------------------------------------------
# TAB 1: PRE-TRIP DECISION INTELLIGENCE
# ----------------------------------------------------------------------------

with tab_pre_trip:
    st.markdown("#### 1. Thiết lập Hành trình & Hồ sơ Thính lực Cá nhân")
    
    col_input1, col_input2, col_input3 = st.columns([2, 2, 2])
    
    with col_input1:
        origin_input = st.text_input("📍 Điểm xuất phát (Origin):", value=st.session_state.origin)
        st.session_state.origin = origin_input
        
    with col_input2:
        dest_input = st.text_input("🏁 Điểm đến (Destination):", value=st.session_state.destination)
        st.session_state.destination = dest_input
        
    with col_input3:
        presets = UserPreferenceProfile.get_presets()
        preset_keys = list(presets.keys())
        selected_key = st.selectbox(
            "🎛️ Hồ sơ Ưu tiên An toàn (Preset):",
            options=preset_keys,
            index=preset_keys.index(st.session_state.profile_key),
            format_func=lambda k: presets[k].display_title
        )
        st.session_state.profile_key = selected_key
        active_profile = presets[selected_key]

    # Hiển thị vector trọng số đang áp dụng
    st.info(
        f"**Vector Trọng số Đang Áp dụng:** Thời gian $w_t = {active_profile.w_time:.2f}$ | "
        f"Rủi ro Âm thanh $w_a = {active_profile.w_ari:.2f}$ | "
        f"Bất định Bayesian $w_u = {active_profile.w_uncertainty:.2f}$ "
        f"*(Ràng buộc cắt an toàn cứng: $ARI_{{max}} \\le {active_profile.tau_cutoff:.1f}$)*"
    )

    st.markdown("---")
    st.markdown("#### 2. Ma Trận Đánh Đổi Đa Tiêu Chí Định Lượng (Trade-Off Matrix)")
    st.caption("Thuật toán Pareto Frontier lọc bỏ các tuyến bị thống trị hoàn toàn, kết hợp hàm chi phí MCDA $C(P)$.")

    # Sinh dữ liệu phân tích lộ trình từ Mock Engine (hoặc Engine thật khi Thiện hoàn thành)
    decision_resp = generate_mock_decision_response(
        origin=st.session_state.origin,
        destination=st.session_state.destination,
        profile=active_profile
    )

    # Hiển thị bảng so sánh Trade-Off Matrix
    matrix_data = decision_resp.get_tradeoff_matrix()
    df_matrix = pd.DataFrame(matrix_data)
    
    st.dataframe(
        df_matrix,
        use_container_width=True,
        hide_index=True
    )

    # Thẻ XAI giải thích lý do đánh đổi minh bạch
    st.markdown("#### 3. Diễn Giải Quyết Định Minh Bạch (Explainable AI - XAI)")
    
    rec_scenario = decision_resp.get_recommended_scenario()
    
    if rec_scenario:
        st.success(
            f"### ⭐ Kịch Bản Khuyên Dùng: {rec_scenario.title}\n\n"
            f"{rec_scenario.xai_explanation}\n\n"
            f"* **Lộ trình:** `{rec_scenario.route_summary}`\n"
            f"* **Thời gian:** `{rec_scenario.duration_min:.0f} phút` (So với tuyến nhanh nhất: `+{rec_scenario.duration_min - 21.0:.0f} phút`)\n"
            f"* **Chỉ số Rủi ro Âm thanh ($ARI$):** `{rec_scenario.avg_ari:.1f}/10` (Giảm 77.4%)\n"
            f"* **Ngưỡng đỉnh rủi ro ($ARI_{{P90}}$):** `{rec_scenario.ari_p90:.1f}/10` (Kiểm soát an toàn)"
        )

    # Bộ chọn và Xác nhận Lộ trình của Người Dùng (Human-in-the-Loop)
    st.markdown("#### 4. Quyền Quyết Định Tối Hậu Thuộc Về Con Người (Human Decision)")
    
    scenario_options = {s.scenario_id: f"{s.title} ({s.duration_min:.0f} phút - ARI: {s.avg_ari:.1f})" for s in decision_resp.scenarios}
    chosen_id = st.radio(
        "Chọn phương án lộ trình bạn muốn kích hoạt:",
        options=list(scenario_options.keys()),
        format_func=lambda x: scenario_options[x],
        index=list(scenario_options.keys()).index(decision_resp.recommended_scenario_id)
    )
    st.session_state.selected_scenario_id = chosen_id

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        if st.button("🚀 XÁC NHẬN CHỌN LỘ TRÌNH NÀY & BẮT ĐẦU CHUYẾN ĐI", type="primary", use_container_width=True):
            st.balloons()
            st.toast("✅ Đã kích hoạt tuyến đường! Mời bạn chuyển sang TAB 2 để xem màn hình giám sát thời gian thực.")


# ----------------------------------------------------------------------------
# TAB 2: ON-TRIP REAL-TIME EDGE SAFEGUARD HUD
# ----------------------------------------------------------------------------

with tab_on_trip:
    # Lấy thông tin lộ trình đã chọn từ Tab 1
    selected_scen = None
    for s in decision_resp.scenarios:
        if s.scenario_id == st.session_state.selected_scenario_id:
            selected_scen = s
            break
    if not selected_scen:
        selected_scen = decision_resp.get_recommended_scenario()

    st.markdown(f"""
    <div style="background-color: #1e293b; padding: 12px 18px; border-radius: 8px; border-left: 5px solid #38bdf8; margin-bottom: 20px;">
        <span style="color: #94a3b8; font-size: 13px;">LỘ TRÌNH ĐANG GIÁM SÁT THỜI GIAN THỰC:</span><br/>
        <strong style="color: #f8fafc; font-size: 16px;">🛣️ {selected_scen.title} ({st.session_state.origin} ➔ {st.session_state.destination})</strong>
    </div>
    """, unsafe_allow_html=True)

    # Hiển thị cảnh báo nếu hệ thống không Healthy
    if st.session_state.system_status == "UNAVAILABLE":
        st.error("🚨 HỆ THỐNG ĐANG Ở TRẠNG THÁI UNAVAILABLE (LỖI PHẦN CỨNG). CẢNH BÁO TẠM NGỪNG ĐỂ TRÁNH AN TOÀN GIẢ!")
    elif st.session_state.system_status == "DEGRADED":
        st.warning("⚠️ TRẠNG THÁI DEGRADED: NHIỄU GIÓ HOẶC PÔ XE LỚN. ĐỘ NHẠY CẢNH BÁO GIẢM SÚT.")

    # Cột hiển thị HUD trung tâm (Mô phỏng Mobile Viewport gắn trên Ghi-đông)
    col_hud, col_controls = st.columns([3, 2])

    with col_hud:
        st.subheader("📱 Màn Hình Ghi-Đông Xe Máy (Mobile HUD Viewport)")
        
        payload = st.session_state.current_payload
        
        # Xác định kiểu hiển thị theo mối nguy
        if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
            if payload.danger_type == "TRUCK_APPROACH" or payload.is_looming:
                box_class = "hud-box-danger"
                icon = "🚨 🚛"
                title = "NGUY HIỂM: XE TẢI NẶNG ÁP SÁT GẤP!"
                haptic_text = "⚡ ĐANG RUNG DỒN DẬP TAY LÁI (WEB HAPTICS)"
            elif payload.danger_type == "EMERGENCY_SIREN":
                box_class = "hud-box-danger"
                icon = "🚑 🚨"
                title = "CẢNH BÁO: XE CỨU THƯƠNG / CỨU HỎA!"
                haptic_text = "⚡ ĐANG RUNG ĐỀU ĐẶN 2 BÊN TAY LÁI"
            else:
                box_class = "hud-box-warning"
                icon = "⚠️ 🚗"
                title = "CHÚ Ý: CÒI XE VƯỢT NGƯỠNG AN TOÀN!"
                haptic_text = "⚡ ĐANG RUNG PHẢN XẠ PHÂN VÙNG"
        else:
            box_class = "hud-box-safe"
            icon = "✅ 🛡️"
            title = "MÔI TRƯỜNG ÂM THANH AN TOÀN"
            haptic_text = "Không kích hoạt rung"

        # Hiển thị hướng tiếp cận
        dir_display = {
            "LEFT": "⬅️ PHÍA SAU BÊN TRÁI",
            "RIGHT": "➡️ PHÍA SAU BÊN PHẢI",
            "CENTER": "⬆️ CHÍNH DIỆN / PHÍA SAU",
            "UNKNOWN": "🔄 KHÔNG GIAN XUNG QUANH"
        }.get(payload.direction, "🔄 ĐANG ĐO ĐẠC")

        st.markdown(f"""
        <div class="{box_class}">
            <h1 style="font-size: 40px; margin: 0;">{icon}</h1>
            <h2 style="margin: 10px 0 5px 0; font-size: 22px;">{title}</h2>
            <div style="font-size: 18px; font-weight: bold; margin: 10px 0; color: #f8fafc;">
                ĐỊNH HƯỚNG MỐI NGUY: <span style="background: rgba(0,0,0,0.4); padding: 4px 12px; border-radius: 8px;">{dir_display}</span>
            </div>
            <p style="margin: 6px 0; font-size: 15px;"><b>Phát hiện:</b> {payload.label} (Tin cậy: {payload.confidence*100:.1f}%)</p>
            <div style="margin-top: 12px; font-weight: bold; font-size: 14px; opacity: 0.9;">
                {haptic_text}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Web Vibration API Script (Nếu mở trên trình duyệt điện thoại Android, máy sẽ rung thực tế!)
        if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
            pattern = "[250, 100, 250, 100, 250]" if payload.is_looming else "[150, 100, 150]"
            st.components.v1.html(f"""
            <script>
                if ('vibrate' in navigator) {{
                    navigator.vibrate({pattern});
                }}
            </script>
            """, height=0, width=0)

        # Các chỉ số kỹ thuật đo đạc
        st.markdown("<br/>", unsafe_allow_html=True)
        m_col1, m_col2, m_col3 = st.columns(3)
        with m_col1:
            st.metric("Cường Độ Âm Thanh", f"{payload.db:.1f} dBA", delta=f"{payload.db - 75:.1f} vs Ngưỡng" if payload.db > 75 else None)
        with m_col2:
            st.metric("Độ Tin Cậy AI", f"{payload.confidence * 100:.1f}%")
        with m_col3:
            st.metric("Độ Trễ Phản Xạ", f"{payload.latency_ms:.1f} ms", delta="Đạt SLA <80ms", delta_color="normal")

    with col_controls:
        st.subheader("🧪 Bảng Điều Khiển Giả Lập Âm Thanh")
        st.caption("Dành cho Ban Giám khảo TMA Solutions thử nghiệm các tình huống giao thông:")

        if st.button("🚛 Kích hoạt Xe Tải Nặng Áp Sát (Looming Hazard)", use_container_width=True):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="LOOMING_TRUCK")
            st.rerun()

        if st.button("🚗 Kích hoạt Còi Xe Máy / Ô Tô (Bên Trái)", use_container_width=True):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="VEHICLE_HORN")
            st.rerun()

        if st.button("🚑 Kích hoạt Còi Xe Cứu Thương / Cứu Hỏa", use_container_width=True):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="EMERGENCY_SIREN")
            st.rerun()

        if st.button("🍃 Kích hoạt Âm Thanh Môi Trường Bình Thường", use_container_width=True):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="SAFE")
            st.rerun()

        st.divider()
        st.subheader("📲 Thử Nghiệm Web Vibration API")
        st.caption("Nếu bạn đang truy cập bằng điện thoại (Chrome/Firefox trên Android), bấm nút dưới để kiểm tra bộ rung máy:")
        
        test_vib = st.button("📳 Rung Thử Nghiệm 3 Nhịp Ngay Lập Tức", use_container_width=True)
        if test_vib:
            st.components.v1.html("""
            <script>
                if ('vibrate' in navigator) {
                    navigator.vibrate([200, 100, 200, 100, 400]);
                } else {
                    alert('Trình duyệt này không hỗ trợ Web Vibration API. Vui lòng mở trên Google Chrome trên điện thoại Android!');
                }
            </script>
            """, height=0, width=0)
            st.success("Đã gửi lệnh rung `navigator.vibrate([200, 100, 200, 100, 400])` tới thiết bị!")