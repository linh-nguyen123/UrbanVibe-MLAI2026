# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Decision Intelligence & Acoustic Safety Platform
MLAI Hackathon 2026 - Decision Intelligence Challenge (TMA Solutions)

Ứng dụng Dashboard Streamlit 2-Tab:
- Tab 1: 🗺️ Ra Quyết Định Lộ Trình (Pre-Trip Decision Intelligence - Bản Đồ Trực Quan & Ma Trận Đánh Đổi)
- Tab 2: 🚨 Giám Sát An Toàn Trên Xe (On-Trip HUD - Chế Độ Lái Xe Tối Giản & Không Gây Xao Nhãng)
"""

import sys
from pathlib import Path

# Đảm bảo đường dẫn import từ thư mục gốc của repository
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

import time
import pandas as pd
import pydeck as pdk
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
    /* Kiểu dáng giao diện điều khiển */
    .hud-box-safe {
        background: linear-gradient(135deg, #0d3b1e 0%, #155724 100%);
        border: 4px solid #28a745;
        border-radius: 20px;
        padding: 30px 20px;
        text-align: center;
        color: #d4edda;
        box-shadow: 0 4px 15px rgba(40, 167, 69, 0.25);
    }
    .hud-box-warning {
        background: linear-gradient(135deg, #4a2700 0%, #854d0e 100%);
        border: 4px solid #f59e0b;
        border-radius: 20px;
        padding: 30px 20px;
        text-align: center;
        color: #fef3c7;
        box-shadow: 0 4px 20px rgba(245, 158, 11, 0.35);
    }
    .hud-box-danger {
        background: linear-gradient(135deg, #500713 0%, #991b1b 100%);
        border: 5px solid #ef4444;
        border-radius: 20px;
        padding: 30px 20px;
        text-align: center;
        color: #fee2e2;
        animation: pulse-danger 1.2s infinite alternate;
        box-shadow: 0 4px 30px rgba(239, 68, 68, 0.6);
    }
    @keyframes pulse-danger {
        0% { transform: scale(1); box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }
        100% { transform: scale(1.015); box-shadow: 0 0 35px rgba(239, 68, 68, 0.9); }
    }
    .action-directive {
        background-color: rgba(0, 0, 0, 0.55);
        border: 2px solid rgba(255, 255, 255, 0.25);
        border-radius: 12px;
        padding: 12px 18px;
        margin-top: 15px;
        font-size: 20px;
        font-weight: 800;
        letter-spacing: 0.5px;
    }
    .direction-badge {
        display: inline-block;
        font-size: 24px;
        font-weight: 900;
        padding: 8px 24px;
        border-radius: 10px;
        background: rgba(0, 0, 0, 0.5);
        margin: 10px 0;
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

if "rider_mode" not in st.session_state:
    st.session_state.rider_mode = True  # Mặc định bật chế độ lái xe tối giản


# ============================================================================
# XỬ LÝ SỰ KIỆN MÔ PHỎNG SỚM (ELIMINATE LATENCY BUG TRONG LƯỢT CLICK ĐẦU TIÊN)
# ============================================================================

# Kiểm tra nếu có action trigger từ query params hoặc state
if "trigger_event" in st.session_state and st.session_state.trigger_event:
    event_type = st.session_state.trigger_event
    st.session_state.current_payload = generate_mock_payload(force_danger_type=event_type)
    st.session_state.trigger_event = None


# ============================================================================
# SIDEBAR: TRẠNG THÁI THỰC TẾ & KHU VỰC MÔ PHỎNG GIÁM KHẢO
# ============================================================================

with st.sidebar:
    st.title("UrbanVibe: SafeRoute")
    st.caption("Acoustic Decision Intelligence Platform")
    
    st.markdown("""
    **MLAI Hackathon 2026**  
    *Phân ban:* **Decision Intelligence (TMA Solutions)**  
    *Đơn vị:* Trường ĐH Bách Khoa – ĐHQG TP.HCM
    """)
    
    st.divider()
    
    # 1. Trạng thái Production (Chỉ đọc - Do phần cứng tự báo cáo)
    st.markdown("#### Trạng thái Phần cứng (Tự báo)")
    if st.session_state.system_status == "HEALTHY":
        st.success("🟢 **HEALTHY**: Mảng mic và cảm biến kết nối tốt. Đang trực tiếp phân tích luồng âm thanh.")
    elif st.session_state.system_status == "DEGRADED":
        st.warning("🟡 **DEGRADED**: Tạp âm gió hoặc rung động cơ vượt ngưỡng bù trừ. Độ nhạy DoA giảm sút.")
    else:
        st.error("🔴 **UNAVAILABLE**: Ngắt kết nối cảm biến! Ngừng cảnh báo để tránh tạo an toàn giả.")

    # 2. Thông tin độ tin cậy và pháp lý chuẩn mực
    st.markdown("---")
    st.markdown("""
    <small>
    📱 <b>Pha 1 (MVP):</b> 0 VNĐ Phần cứng bổ sung (Chạy trên Smartphone hiện có).<br/>
    🔌 <b>Pha 2:</b> Module phần cứng chuyên dụng (~1.55M VNĐ - Lộ trình mở rộng).<br/>
    🔒 <b>Quyền riêng tư:</b> Thiết kế theo định hướng tuân thủ Nghị định 13/2023/NĐ-CP (Zero Raw Audio Storage trên RAM 0.975s).
    </small>
    """, unsafe_allow_html=True)

    # 3. Khu vực công cụ Giám khảo (Tách biệt hoàn toàn trong Expander)
    st.divider()
    with st.expander("🧪 Công cụ Mô phỏng Phần cứng (Dành cho Giám khảo)", expanded=False):
        st.caption("Dùng để thử nghiệm các tình huống đứt cáp, nhiễu gió khi thuyết trình:")
        hw_choice = st.radio(
            "Mô phỏng trạng thái phần cứng:",
            options=["HEALTHY", "DEGRADED", "UNAVAILABLE"],
            index=["HEALTHY", "DEGRADED", "UNAVAILABLE"].index(st.session_state.system_status),
            format_func=lambda x: {
                "HEALTHY": "Bình thường (Healthy)",
                "DEGRADED": "Gió lớn / Pô xe (Degraded)",
                "UNAVAILABLE": "Mất kết nối (Unavailable)"
            }[x]
        )
        if hw_choice != st.session_state.system_status:
            st.session_state.system_status = hw_choice
            st.rerun()


# ============================================================================
# HEADER CHÍNH
# ============================================================================

st.markdown("""
# UrbanVibe: SafeRoute
##### Hệ thống Hỗ trợ Ra Quyết định & Giám sát An toàn Âm thanh cho Người Khiếm thính
""")

# ============================================================================
# 2 TABS CHÍNH: PRE-TRIP DECISION VÀ ON-TRIP HUD
# ============================================================================

tab_pre_trip, tab_on_trip = st.tabs([
    "🗺️ TAB 1: Ra Quyết Định Lộ Trình (Pre-Trip MCDA)",
    "🚨 TAB 2: Giám Sát An Toàn Trên Xe (On-Trip HUD)"
])


# ----------------------------------------------------------------------------
# TAB 1: PRE-TRIP DECISION INTELLIGENCE (BẢN ĐỒ TRỰC QUAN & MA TRẬN ĐÁNH ĐỔI)
# ----------------------------------------------------------------------------

with tab_pre_trip:
    st.markdown("#### 1. Thiết lập Hành trình & Hồ sơ Sở thích")
    
    col_input1, col_input2, col_input3 = st.columns([2, 2, 2])
    
    with col_input1:
        st.session_state.origin = st.text_input("Điểm xuất phát:", value=st.session_state.origin)
        
    with col_input2:
        st.session_state.destination = st.text_input("Điểm đến:", value=st.session_state.destination)
        
    with col_input3:
        presets = UserPreferenceProfile.get_presets()
        preset_keys = list(presets.keys())
        selected_key = st.selectbox(
            "Hồ sơ Ưu tiên:",
            options=preset_keys,
            index=preset_keys.index(st.session_state.profile_key),
            format_func=lambda k: presets[k].display_title
        )
        st.session_state.profile_key = selected_key
        active_profile = presets[selected_key]

    st.caption(
        f"Vector trọng số: Thời gian $w_t = {active_profile.w_time:.2f}$ | "
        f"Rủi ro Âm thanh $w_a = {active_profile.w_ari:.2f}$ | "
        f"Bất định Bayesian $w_u = {active_profile.w_uncertainty:.2f} $ "
        f"(Ràng buộc an toàn cứng: $ARI_{{max}} \\le {active_profile.tau_cutoff:.1f}$)"
    )

    # Sinh kết quả phân tích đa mục tiêu MCDA
    decision_resp = generate_mock_decision_response(
        origin=st.session_state.origin,
        destination=st.session_state.destination,
        profile=active_profile
    )

    st.markdown("---")
    
    # Bố cục 2 Cột: Bên Trái là Bản Đồ Không Gian Pydeck, Bên Phải là Ma Trận Đánh Đổi & XAI
    col_map, col_matrix = st.columns([1, 1], gap="medium")

    with col_map:
        st.markdown("#### Bản Đồ Không Gian & Điểm Đen Rủi Ro")
        st.caption("Trực quan hóa 3 phương án lộ trình và các điểm đen giao thông bạo lực âm thanh.")

        # Dữ liệu 3 tuyến đường
        routes_geojson = [
            {
                "name": "Tuyến A: Nhanh nhất (Google Maps)",
                "path": [
                    [106.657, 10.772], [106.675, 10.782], [106.698, 10.792],
                    [106.715, 10.801], [106.745, 10.825], [106.770, 10.842], [106.790, 10.852]
                ],
                "color": [239, 68, 68, 220],
                "desc": "Tuyến A: Trục chính Điện Biên Phủ - Xa lộ Hà Nội (Nhiều xe tải, ARI 8.4/10)"
            },
            {
                "name": "Tuyến B: SafeRoute (Khuyên dùng)",
                "path": [
                    [106.657, 10.772], [106.662, 10.785], [106.680, 10.798],
                    [106.702, 10.808], [106.728, 10.820], [106.755, 10.835], [106.778, 10.846], [106.790, 10.852]
                ],
                "color": [16, 185, 129, 255],
                "desc": "Tuyến B: SafeRoute né điểm đen qua đường gom Song Hành (Giảm 77% rủi ro, ARI 1.9/10)"
            },
            {
                "name": "Tuyến C: Tuyến đường gom vắng",
                "path": [
                    [106.657, 10.772], [106.645, 10.795], [106.660, 10.825],
                    [106.705, 10.850], [106.745, 10.865], [106.775, 10.860], [106.790, 10.852]
                ],
                "color": [56, 189, 248, 180],
                "desc": "Tuyến C: Vành đai vắng qua Phạm Văn Đồng (An toàn nhưng tốn thêm 15 phút)"
            }
        ]

        # Dữ liệu điểm đen rủi ro âm thanh (Hotspots)
        hotspots_geojson = [
            {
                "name": "Điểm đen: Nút giao Hàng Xanh / Cầu Sài Gòn",
                "coordinates": [106.715, 10.801],
                "ari": "9.7 / 10",
                "reason": "19 lượt xe tải/phút, còi hơi vượt 115 dBA"
            },
            {
                "name": "Điểm đen: Trục Xa lộ Hà Nội - Ngã 4 Thủ Đức",
                "coordinates": [106.770, 10.842],
                "ari": "9.4 / 10",
                "reason": "Điểm đen xe container phanh gấp và áp sát làn xe máy"
            }
        ]

        # Điểm đầu và điểm cuối
        pins_geojson = [
            {"name": "Xuất phát: ĐH Bách Khoa CS1", "coordinates": [106.657, 10.772], "color": [34, 197, 94, 255]},
            {"name": "Đích đến: Bến xe Miền Đông mới", "coordinates": [106.790, 10.852], "color": [239, 68, 68, 255]}
        ]

        path_layer = pdk.Layer(
            "PathLayer",
            routes_geojson,
            get_path="path",
            get_color="color",
            width_scale=20,
            width_min_pixels=5,
            pickable=True
        )

        hotspot_layer = pdk.Layer(
            "ScatterplotLayer",
            hotspots_geojson,
            get_position="coordinates",
            get_color=[239, 68, 68, 200],
            get_radius=500,
            radius_min_pixels=10,
            radius_max_pixels=28,
            pickable=True
        )

        pin_layer = pdk.Layer(
            "ScatterplotLayer",
            pins_geojson,
            get_position="coordinates",
            get_color="color",
            get_radius=300,
            radius_min_pixels=8,
            radius_max_pixels=16,
            pickable=True
        )

        view_state = pdk.ViewState(latitude=10.812, longitude=106.723, zoom=11.2, pitch=0)
        deck = pdk.Deck(
            layers=[path_layer, hotspot_layer, pin_layer],
            initial_view_state=view_state,
            map_style="dark",
            tooltip={"text": "{name}\n{desc}{reason}"}
        )

        st.pydeck_chart(deck, use_container_width=True)

        # Chú thích bản đồ gọn gàng
        st.markdown("""
        <div style="font-size: 13px; color: #cbd5e1; background: #0f172a; padding: 10px 14px; border-radius: 8px;">
            <span style="color: #ef4444; font-weight: bold;">━━</span> Tuyến A: Nhanh nhất (ARI 8.4) &nbsp;|&nbsp;
            <span style="color: #10b981; font-weight: bold;">━━</span> Tuyến B: SafeRoute Khuyên dùng (ARI 1.9) &nbsp;|&nbsp;
            <span style="color: #38bdf8; font-weight: bold;">━━</span> Tuyến C: Đường gom vắng (ARI 0.8)<br/>
            <span style="color: #ef4444;">●</span> Điểm đen tai nạn âm thanh (Hotspots) mà SafeRoute chủ động né tránh
        </div>
        """, unsafe_allow_html=True)

    with col_matrix:
        st.markdown("#### Ma Trận Đánh Đổi Định Lượng (Trade-Off Matrix)")
        st.caption("Các phương án tối ưu Pareto không bị thống trị hoàn toàn:")

        matrix_data = decision_resp.get_tradeoff_matrix()
        df_matrix = pd.DataFrame(matrix_data)
        st.dataframe(df_matrix, use_container_width=True, hide_index=True)

        # Khối XAI Diễn giải Minh bạch
        st.markdown("#### Diễn Giải Minh Bạch (XAI)")
        rec_scenario = decision_resp.get_recommended_scenario()
        if rec_scenario:
            st.success(
                f"**Đề xuất tối ưu:** `{rec_scenario.title}`\n\n"
                f"{rec_scenario.xai_explanation}"
            )

        # Xác nhận lựa chọn
        st.markdown("#### Xác Nhận Lộ Trình")
        scenario_options = {s.scenario_id: f"{s.title} ({s.duration_min:.0f} phút - ARI: {s.avg_ari:.1f})" for s in decision_resp.scenarios}
        chosen_id = st.radio(
            "Chọn tuyến để bắt đầu giám sát:",
            options=list(scenario_options.keys()),
            format_func=lambda x: scenario_options[x],
            index=list(scenario_options.keys()).index(decision_resp.recommended_scenario_id),
            horizontal=False
        )
        st.session_state.selected_scenario_id = chosen_id

        if st.button("Xác Nhận & Bắt Đầu Di Chuyển ➔", type="primary", use_container_width=True):
            st.toast("Đã kích hoạt lộ trình! Chuyển sang Tab 2 để quan sát màn hình lái xe.")


# ----------------------------------------------------------------------------
# TAB 2: ON-TRIP REAL-TIME HUD (CHẾ ĐỘ LÁI XE TỐI GIẢN & KHÔNG XAO NHÃNG)
# ----------------------------------------------------------------------------

with tab_on_trip:
    # Lấy kịch bản lộ trình đang hoạt động
    active_scen = None
    for s in decision_resp.scenarios:
        if s.scenario_id == st.session_state.selected_scenario_id:
            active_scen = s
            break
    if not active_scen:
        active_scen = decision_resp.get_recommended_scenario()

    # Banner thông báo tuyến đang giám sát
    st.markdown(f"""
    <div style="background-color: #0f172a; padding: 10px 16px; border-radius: 8px; border-left: 5px solid #10b981; margin-bottom: 16px;">
        <span style="color: #94a3b8; font-size: 12px; text-transform: uppercase; font-weight: bold;">Lộ trình đang giám sát:</span><br/>
        <strong style="color: #f8fafc; font-size: 15px;">{active_scen.title} ({st.session_state.origin} ➔ {st.session_state.destination})</strong>
    </div>
    """, unsafe_allow_html=True)

    # Thanh điều hướng chuyển đổi Chế độ Lái xe Tối giản vs Chế độ Giám khảo
    col_mode1, col_mode2 = st.columns([3, 1])
    with col_mode1:
        st.session_state.rider_mode = st.toggle(
            "🛡️ Chế độ Lái xe Tối giản (Distraction-Free Rider HUD)",
            value=st.session_state.rider_mode,
            help="Ẩn mọi chỉ số kỹ thuật phức tạp, chỉ hiển thị mức khẩn cấp, hướng nguy cơ và hành động ngắn gọn cho người lái xe."
        )
    with col_mode2:
        if st.session_state.system_status == "HEALTHY":
            st.markdown("<span style='color: #22c55e; font-weight: bold;'>● Cảm biến: Khỏe mạnh</span>", unsafe_allow_html=True)
        elif st.session_state.system_status == "DEGRADED":
            st.markdown("<span style='color: #f59e0b; font-weight: bold;'>▲ Cảm biến: Giảm độ nhạy</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color: #ef4444; font-weight: bold;'>✖ Cảm biến: Mất kết nối</span>", unsafe_allow_html=True)

    payload = st.session_state.current_payload

    # CẢNH BÁO NẾU PHẦN CỨNG LỖI (CHỐNG LỖI IM LẶNG)
    if st.session_state.system_status == "UNAVAILABLE":
        st.error("🚨 CẢNH BÁO PHẦN CỨNG: CẢM BIẾN MẤT TÍN HIỆU! HỆ THỐNG KHÔNG THỂ PHÁT CẢNH BÁO ÂM THANH. HÃY DỰA HOÀN TOÀN VÀO QUAN SÁT MẮT!")
    elif st.session_state.system_status == "DEGRADED":
        st.warning("⚠️ CHÚ Ý: NHIỄU GIÓ / PÔ XE LỚN ĐANG ẢNH HƯỞNG ĐỘ NHẠY ĐO ĐẠC. HÃY TĂNG CƯỜNG QUAN SÁT GƯƠNG.")

    # ------------------------------------------------------------------------
    # HIỂN THỊ THẺ HUD TƯƠNG PHẢN CAO
    # ------------------------------------------------------------------------
    
    # Xác định mức độ khẩn cấp & hành động tương ứng
    if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
        if payload.danger_type == "TRUCK_APPROACH" or payload.is_looming:
            box_class = "hud-box-danger"
            severity_text = "NGUY CẤP: XE TẢI ÁP SÁT PHÍA SAU!"
            action_directive = "GIỮ THẲNG LÁI · GIẢM TỐC · QUAN SÁT GƯƠNG"
            haptic_desc = "Rung dồn dập 2 bên tay lái (Looming Reflex)"
        elif payload.danger_type == "EMERGENCY_SIREN":
            box_class = "hud-box-danger"
            severity_text = "CẢNH BÁO: XE ƯU TIÊN TIẾP CẬN!"
            action_directive = "GIẢM TỐC ĐỘ · TẤP LỀ PHẢI NHƯỜNG ĐƯỜNG"
            haptic_desc = "Rung nhịp đôi cách quãng"
        else:
            box_class = "hud-box-warning"
            severity_text = "CHÚ Ý: CÒI PHƯƠNG TIỆN ÁP SÁT"
            action_directive = "GIỮ VỮNG TAY LÁI · CHUẨN BỊ NHƯỜNG ĐƯỜNG"
            haptic_desc = "Rung phản xạ phân vùng theo hướng"
    else:
        box_class = "hud-box-safe"
        severity_text = "MÔI TRƯỜNG AN TOÀN"
        action_directive = "DUY TRÌ TỐC ĐỘ ỔN ĐỊNH · TIẾP TỤC HÀNH TRÌNH"
        haptic_desc = "Không kích hoạt rung"

    # Định hướng hiển thị
    dir_text = {
        "LEFT": "⬅️ BÊN TRÁI",
        "RIGHT": "➡️ BÊN PHẢI",
        "CENTER": "⬆️ PHÍA SAU",
        "UNKNOWN": "XUNG QUANH"
    }.get(payload.direction, "ĐANG QUAN SÁT")

    # RENDER HUD CARD
    st.markdown(f"""
    <div class="{box_class}">
        <div style="font-size: 16px; font-weight: bold; letter-spacing: 1px; opacity: 0.85; text-transform: uppercase;">
            MỨC ĐỘ NGUY CƠ ÂM HỌC
        </div>
        <div style="font-size: 32px; font-weight: 900; margin: 8px 0;">
            {severity_text}
        </div>
        <div class="direction-badge">
            HƯỚNG: {dir_text}
        </div>
        <div class="action-directive">
            {action_directive}
        </div>
        <div style="margin-top: 15px; font-size: 14px; opacity: 0.9;">
            📳 <b>Phản xạ Xúc giác:</b> {haptic_desc}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Web Vibration API Script (Rung máy điện thoại thực tế nếu là mobile)
    if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
        pattern = "[250, 100, 250, 100, 250]" if payload.is_looming else "[150, 100, 150]"
        st.components.v1.html(f"""
        <script>
            if ('vibrate' in navigator) {{
                navigator.vibrate({pattern});
            }}
        </script>
        """, height=0, width=0)

    # ------------------------------------------------------------------------
    # CHẾ ĐỘ KIỂM THỬ KỸ THUẬT (CHỈ HIỆN KHI TẮT RIDER MODE HOẶC CHO GIÁM KHẢO)
    # ------------------------------------------------------------------------
    if not st.session_state.rider_mode:
        st.markdown("<br/>", unsafe_allow_html=True)
        st.markdown("##### 🔬 Thông Số Kỹ Thuật Phân Tích (Chế độ Giám Khảo)")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Cường Độ Âm", f"{payload.db:.1f} dBA", delta=f"{payload.db - 75:.1f} dBA" if payload.db > 75 else None)
        with m2:
            st.metric("Độ Tin Cậy AI", f"{payload.confidence * 100:.1f}%")
        with m3:
            st.metric("Độ Trễ Phản Xạ", f"{payload.latency_ms:.1f} ms", delta="<80ms SLA", delta_color="normal")
        with m4:
            st.metric("Biến thiên dE/dt", "Áp sát (Looming)" if payload.is_looming else "Ổn định")

    # ------------------------------------------------------------------------
    # BẢNG ĐIỀU KHIỂN MÔ PHỎNG SỰ KIỆN (DÀNH CHO GIÁM KHẢO THỬ NGHIỆM TỨC THÌ)
    # ------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("##### 🧪 Thử Nghiệm Tình Huống Giao Thông (Dành cho Giám khảo)")
    st.caption("Nhấn nút dưới để kích hoạt phản hồi tức thì (<100ms) trên màn hình và rung xúc giác:")

    b_col1, b_col2, b_col3, b_col4 = st.columns(4)
    
    with b_col1:
        if st.button("🚛 Xe Tải Áp Sát (Phải)", use_container_width=True, type="secondary"):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="LOOMING_TRUCK")
            st.toast("Phát hiện Xe tải áp sát bên Phải (dE/dt cao, 98 dBA)!")
            st.rerun()

    with b_col2:
        if st.button("🚗 Còi Xe Máy (Trái)", use_container_width=True, type="secondary"):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="VEHICLE_HORN")
            st.toast("Phát hiện Còi xe máy bên Trái (82 dBA)!")
            st.rerun()

    with b_col3:
        if st.button("🚑 Xe Cứu Thương (Sau)", use_container_width=True, type="secondary"):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="EMERGENCY_SIREN")
            st.toast("Phát hiện Còi xe ưu tiên từ phía sau (92 dBA)!")
            st.rerun()

    with b_col4:
        if st.button("🍃 Yên Tĩnh (Bình thường)", use_container_width=True, type="secondary"):
            st.session_state.current_payload = generate_mock_payload(force_danger_type="SAFE")
            st.toast("Môi trường âm thanh trở lại bình thường.")
            st.rerun()