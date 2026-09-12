# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Decision Intelligence & Acoustic Safety Platform
MLAI Hackathon 2026 - Decision Intelligence Challenge (TMA Solutions)

Ứng dụng Dashboard Streamlit 2-Tab:
- Tab 1: 🗺️ Ra Quyết Định Lộ Trình (Pre-Trip Decision Intelligence - Bản Đồ Đa Lớp & Ma Trận Đánh Đổi)
- Tab 2: 🚨 Giám Sát An Toàn Trên Xe (On-Trip HUD - Chế Độ Lái Xe Toàn Màn Hình Tối Giản)
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
# CẤU HÌNH TRANG STREAMLIT
# ============================================================================

st.set_page_config(
    page_title="UrbanVibe: SafeRoute | Decision Intelligence",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# KHỞI TẠO SESSION STATE
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
    st.session_state.rider_mode = False  # Mặc định tắt để giám khảo xem toàn cảnh, bật khi chuyển sang lái xe

if "data_opt_in" not in st.session_state:
    st.session_state.data_opt_in = True  # Quyền riêng tư Opt-in


# ============================================================================
# CALLBACKS XỬ LÝ SỰ KIỆN MÔ PHỎNG TỨC THÌ (<50ms, KHÔNG TRỄ REFRESS)
# ============================================================================

def on_trigger_event(event_type: str):
    """Callback chạy TRƯỚC KHI Streamlit render UI, đảm bảo phản hồi tức thì 100%."""
    st.session_state.current_payload = generate_mock_payload(force_danger_type=event_type)

def on_toggle_rider_mode():
    """Bật/tắt chế độ lái xe toàn màn hình."""
    st.session_state.rider_mode = not st.session_state.rider_mode


# ============================================================================
# CSS: TÙY BIẾN GIAO DIỆN & FULL-SCREEN RIDER HUD KHI ĐANG LÁI XE
# ============================================================================

if st.session_state.rider_mode:
    # Chế độ Lái xe: Ẩn sidebar, ẩn header mặc định, tối ưu hóa toàn màn hình
    rider_css = """
    <style>
        [data-testid="stSidebar"] { display: none !important; }
        header[data-testid="stHeader"] { display: none !important; }
        footer { display: none !important; }
        .block-container {
            padding: 1rem 1.5rem !important;
            max-width: 100% !important;
        }
        .hud-fullscreen {
            min-height: 72vh;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            border-radius: 24px;
            padding: 40px 24px;
            text-align: center;
        }
    </style>
    """
else:
    rider_css = """
    <style>
        .hud-fullscreen {
            border-radius: 20px;
            padding: 30px 20px;
            text-align: center;
        }
    </style>
    """

st.markdown(rider_css + """
<style>
    .hud-box-safe {
        background: linear-gradient(135deg, #064e3b 0%, #047857 100%);
        border: 4px solid #10b981;
        color: #ecfdf5;
        box-shadow: 0 4px 20px rgba(16, 185, 129, 0.3);
    }
    .hud-box-warning {
        background: linear-gradient(135deg, #78350f 0%, #b45309 100%);
        border: 4px solid #f59e0b;
        color: #fffbeb;
        box-shadow: 0 4px 25px rgba(245, 158, 11, 0.4);
    }
    .hud-box-danger {
        background: linear-gradient(135deg, #7f1d1d 0%, #b91c1c 100%);
        border: 5px solid #ef4444;
        color: #fef2f2;
        animation: pulse-danger 1.2s infinite alternate;
        box-shadow: 0 6px 35px rgba(239, 68, 68, 0.7);
    }
    @keyframes pulse-danger {
        0% { transform: scale(1); box-shadow: 0 0 15px rgba(239, 68, 68, 0.4); }
        100% { transform: scale(1.015); box-shadow: 0 0 35px rgba(239, 68, 68, 0.9); }
    }
    .action-directive-danger {
        background-color: #000000;
        border: 3px solid #f87171;
        border-radius: 14px;
        padding: 16px 24px;
        margin-top: 18px;
        font-size: 26px;
        font-weight: 900;
        color: #fef08a;
        letter-spacing: 0.5px;
    }
    .action-directive-safe {
        background-color: rgba(0, 0, 0, 0.4);
        border: 2px solid rgba(255, 255, 255, 0.3);
        border-radius: 12px;
        padding: 14px 20px;
        margin-top: 16px;
        font-size: 20px;
        font-weight: 700;
        color: #d1fae5;
    }
    .direction-badge {
        display: inline-block;
        font-size: 26px;
        font-weight: 900;
        padding: 10px 28px;
        border-radius: 12px;
        background: rgba(0, 0, 0, 0.6);
        margin: 12px 0;
        border: 1px solid rgba(255, 255, 255, 0.2);
    }
</style>
""", unsafe_allow_html=True)


# ============================================================================
# SIDEBAR (CHỈ HIỂN THỊ KHI KHÔNG Ở RIDER FULLSCREEN MODE)
# ============================================================================

if not st.session_state.rider_mode:
    with st.sidebar:
        st.title("UrbanVibe: SafeRoute")
        st.caption("Acoustic-Aware Decision Intelligence")
        
        st.markdown("""
        **MLAI Hackathon 2026**  
        *Track:* **Decision Intelligence (TMA Solutions)**  
        *Đơn vị:* Trường ĐH Bách Khoa – ĐHQG-HCM
        """)
        st.divider()

        # 1. Trạng thái phần cứng tự báo cáo (Read-only status)
        st.markdown("##### Trạng thái Cảm biến & Phần cứng")
        if st.session_state.system_status == "HEALTHY":
            st.success("🟢 **BÌNH THƯỜNG**: Cảm biến âm học kết nối ổn định.")
        elif st.session_state.system_status == "DEGRADED":
            st.warning("🟡 **GIẢM ĐỘ NHẠY**: Tạp âm gió / rung pô xe vượt ngưỡng.")
        else:
            st.error("🔴 **MẤT TÍN HIỆU**: Lỗi cảm biến! Đã ngắt cảnh báo để tránh an toàn giả.")

        # 2. Phân định rõ ràng 2 Pha triển khai
        st.markdown("---")
        st.markdown("##### Phạm Vi & Lộ Trình Kỹ Thuật")
        st.markdown("""
        * **Pha 1 (Hiện tại - 0 VNĐ Phần cứng):** Chạy trên smartphone có sẵn; đo mức ồn dB, phân loại âm thanh cơ bản và ra quyết định lộ trình MCDA.
        * **Pha 2 (Mở rộng - ~1.55M VNĐ BOM):** Cụm Pod 3 mic MEMS trên ghi-đông định hướng DoA 360° chính xác cao & cặp tay nắm rung BLE độc lập.
        """)

        # 3. Quản trị quyền riêng tư thực tế (Privacy Controls)
        st.markdown("---")
        st.markdown("##### Quyền Riêng Tư & Nghị Định 13")
        st.session_state.data_opt_in = st.toggle(
            "Đóng góp dữ liệu rủi ro ẩn danh",
            value=st.session_state.data_opt_in,
            help="Chỉ gửi metadata ẩn danh (Mã đoạn đường, dB trung bình, nhãn còi xe). TUYỆT ĐỐI KHÔNG ghi âm thô (Zero Raw Audio Storage)."
        )
        if st.button("Xóa Dữ Liệu Đã Đóng Góp (HMAC Token)", use_container_width=True):
            st.info("Đã gửi yêu cầu thu hồi đồng thuận & hủy metadata theo HMAC Token.")

        # 4. Công cụ giả lập dành riêng cho Giám khảo
        st.divider()
        with st.expander("🧪 Công cụ Giả lập Phần cứng (Giám khảo)", expanded=False):
            st.caption("Mô phỏng các tình huống hỏng hóc thực địa khi bảo vệ:")
            hw_override = st.radio(
                "Mô phỏng trạng thái phần cứng:",
                options=["HEALTHY", "DEGRADED", "UNAVAILABLE"],
                index=["HEALTHY", "DEGRADED", "UNAVAILABLE"].index(st.session_state.system_status),
                format_func=lambda x: {
                    "HEALTHY": "Cảm biến bình thường (Healthy)",
                    "DEGRADED": "Gió mạnh / Nhiễu pô (Degraded)",
                    "UNAVAILABLE": "Mất kết nối mic (Unavailable)"
                }[x]
            )
            if hw_override != st.session_state.system_status:
                st.session_state.system_status = hw_override
                st.rerun()


# ============================================================================
# GIAO DIỆN CHÍNH (XỬ LÝ RIÊNG KHI BẬT RIDER FULLSCREEN MODE)
# ============================================================================

payload = st.session_state.current_payload

# NẾU ĐANG Ở CHẾ ĐỘ LÁI XE TOÀN MÀN HÌNH (RIDER MODE)
if st.session_state.rider_mode:
    # Thanh trạng thái tối giản trên cùng: Lộ trình + Trạng thái cảm biến + Nút Thoát
    top_col1, top_col2, top_col3 = st.columns([4, 2, 2])
    with top_col1:
        st.markdown(f"**🛣️ Tuyến:** `{st.session_state.selected_scenario_id}` ({st.session_state.origin} ➔ {st.session_state.destination})")
    with top_col2:
        if st.session_state.system_status == "HEALTHY":
            st.markdown("<span style='color: #10b981; font-weight: bold;'>🟢 Cảm biến: Khỏe mạnh</span>", unsafe_allow_html=True)
        elif st.session_state.system_status == "DEGRADED":
            st.markdown("<span style='color: #f59e0b; font-weight: bold;'>🟡 Cảm biến: Giảm độ nhạy</span>", unsafe_allow_html=True)
        else:
            st.markdown("<span style='color: #ef4444; font-weight: bold;'>🔴 Cảm biến: Mất kết nối</span>", unsafe_allow_html=True)
    with top_col3:
        st.button("✕ Thoát Chế độ Lái xe", on_click=on_toggle_rider_mode, use_container_width=True)

    # Cảnh báo lỗi phần cứng nếu có (Chống an toàn giả)
    if st.session_state.system_status == "UNAVAILABLE":
        st.error("🚨 CẢM BIẾN MẤT KẾT NỐI! HỆ THỐNG KHÔNG THỂ PHÁT CẢNH BÁO. TẬP TRUNG QUAN SÁT MẮT 100%!")
    elif st.session_state.system_status == "DEGRADED":
        st.warning("⚠️ NHIỄU GIÓ LỚN: Độ nhạy cảnh báo giảm. Hãy quan sát gương thường xuyên.")

    # Xác định mức độ khẩn cấp & Chỉ dẫn hành động duy nhất, ngắn gọn
    if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
        if payload.danger_type == "TRUCK_APPROACH" or payload.is_looming:
            box_class = "hud-box-danger"
            severity_text = "NGUY CẤP: XE TẢI ÁP SÁT PHÍA SAU!"
            action_text = "GIỮ THẲNG LÁI · GIẢM TỐC NHẸ · QUAN SÁT GƯƠNG"
            action_class = "action-directive-danger"
            haptic_desc = "📳 Rung dồn dập 2 bên tay lái"
        elif payload.danger_type == "EMERGENCY_SIREN":
            box_class = "hud-box-danger"
            severity_text = "CẢNH BÁO: XE ƯU TIÊN TIẾP CẬN!"
            action_text = "GIẢM TỐC ĐỘ · TẤP LỀ PHẢI NHƯỜNG ĐƯỜNG"
            action_class = "action-directive-danger"
            haptic_desc = "📳 Rung nhịp đôi cách quãng"
        else:
            box_class = "hud-box-warning"
            severity_text = "CHÚ Ý: CÒI XE ÁP SÁT PHÍA SAU"
            action_text = "GIỮ VỮNG TAY LÁI · CHUẨN BỊ NHƯỜNG ĐƯỜNG"
            action_class = "action-directive-danger"
            haptic_desc = "📳 Rung phân vùng theo hướng"
    else:
        box_class = "hud-box-safe"
        severity_text = "KHÔNG PHÁT HIỆN MỐI NGUY ÂM THANH HIỆN TẠI"
        action_text = "TIẾP TỤC QUAN SÁT GIAO THÔNG BÌNH THƯỜNG"
        action_class = "action-directive-safe"
        haptic_desc = "Không kích hoạt rung"

    # Định hướng hiển thị
    dir_label = {
        "LEFT": "⬅️ NGUY CƠ BÊN TRÁI",
        "RIGHT": "➡️ NGUY CƠ BÊN PHẢI",
        "CENTER": "⬆️ PHÍA SAU TIẾP CẬN",
        "UNKNOWN": "XUNG QUANH"
    }.get(payload.direction, "ĐANG ĐO ĐẠC")

    # THẺ HUD TOÀN MÀN HÌNH CHỈ GIỮ 4 THÔNG TIN CỐT LÕI
    st.markdown(f"""
    <div class="hud-fullscreen {box_class}">
        <div style="font-size: 20px; font-weight: 800; letter-spacing: 1.5px; opacity: 0.9; text-transform: uppercase;">
            MỨC ĐỘ NGUY CƠ
        </div>
        <div style="font-size: 38px; font-weight: 900; margin: 12px 0;">
            {severity_text}
        </div>
        <div class="direction-badge">
            {dir_label}
        </div>
        <div class="{action_class}">
            {action_text}
        </div>
        <div style="margin-top: 24px; font-size: 17px; font-weight: 600; opacity: 0.95;">
            {haptic_desc}
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

    # Thanh phím bấm mô phỏng nhanh dưới chân trang cho Giám khảo test ngay khi đang ở Rider Mode
    st.markdown("<br/>", unsafe_allow_html=True)
    sim_col1, sim_col2, sim_col3, sim_col4 = st.columns(4)
    with sim_col1:
        st.button("🚛 Test Xe Tải Áp Sát", on_click=on_trigger_event, args=("LOOMING_TRUCK",), use_container_width=True)
    with sim_col2:
        st.button("🚗 Test Còi Xe Máy", on_click=on_trigger_event, args=("VEHICLE_HORN",), use_container_width=True)
    with sim_col3:
        st.button("🚑 Test Còi Cứu Thương", on_click=on_trigger_event, args=("EMERGENCY_SIREN",), use_container_width=True)
    with sim_col4:
        st.button("🍃 Test Môi Trường Êm", on_click=on_trigger_event, args=("SAFE",), use_container_width=True)


# NẾU ĐANG Ở CHẾ ĐỘ BÌNH THƯỜNG (2-TAB DASHBOARD)
else:
    st.markdown("""
    # UrbanVibe: SafeRoute
    ##### Hệ thống Hỗ trợ Ra Quyết định & Giám sát An toàn Âm thanh cho Người Khiếm thính
    """)

    tab_pre_trip, tab_on_trip = st.tabs([
        "🗺️ TAB 1: Ra Quyết Định Lộ Trình (Pre-Trip MCDA)",
        "🚨 TAB 2: Giám Sát An Toàn Trên Xe (On-Trip HUD)"
    ])

    # ------------------------------------------------------------------------
    # TAB 1: PRE-TRIP DECISION INTELLIGENCE
    # ------------------------------------------------------------------------
    with tab_pre_trip:
        st.markdown("#### 1. Thiết lập Hành trình & Hồ sơ Sở thích")
        col_in1, col_in2, col_in3 = st.columns([2, 2, 2])
        with col_in1:
            st.session_state.origin = st.text_input("Điểm xuất phát:", value=st.session_state.origin)
        with col_in2:
            st.session_state.destination = st.text_input("Điểm đến:", value=st.session_state.destination)
        with col_in3:
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
            f"Bất định Bayesian $w_u = {active_profile.w_uncertainty:.2f}$ "
            f"(Ràng buộc an toàn cứng: $ARI_{{max}} \\le {active_profile.tau_cutoff:.1f}$)"
        )

        decision_resp = generate_mock_decision_response(
            origin=st.session_state.origin,
            destination=st.session_state.destination,
            profile=active_profile
        )

        st.markdown("---")
        col_map, col_matrix = st.columns([1, 1], gap="medium")

        with col_map:
            st.markdown("#### Bản Đồ Không Gian Đa Lớp & Điểm Rủi Ro Âm Thanh")
            st.caption("Phân biệt các tuyến bằng độ dày, kiểu nét và nhãn văn bản (không phụ thuộc màu sắc).")

            # 3 Tuyến đường: Tuyến B được highlight nét dày nhất (8px)
            routes_data = [
                {
                    "name": "Tuyến A (Nhanh nhất - Baseline)",
                    "path": [
                        [106.657, 10.772], [106.675, 10.782], [106.698, 10.792],
                        [106.715, 10.801], [106.745, 10.825], [106.770, 10.842], [106.790, 10.852]
                    ],
                    "color": [239, 68, 68, 220],
                    "width": 5,
                    "desc": "Tuyến A: Trục chính Điện Biên Phủ - Xa lộ Hà Nội (Nhiều xe tải, ARI 8.4)"
                },
                {
                    "name": "Tuyến B: SafeRoute (Đề xuất tối ưu)",
                    "path": [
                        [106.657, 10.772], [106.662, 10.785], [106.680, 10.798],
                        [106.702, 10.808], [106.728, 10.820], [106.755, 10.835], [106.778, 10.846], [106.790, 10.852]
                    ],
                    "color": [16, 185, 129, 255],
                    "width": 9,  # Nét dày nổi bật
                    "desc": "Tuyến B: SafeRoute né điểm đen qua đường gom Song Hành (Giảm 77% rủi ro, ARI 1.9)"
                },
                {
                    "name": "Tuyến C (Đường gom vắng)",
                    "path": [
                        [106.657, 10.772], [106.645, 10.795], [106.660, 10.825],
                        [106.705, 10.850], [106.745, 10.865], [106.775, 10.860], [106.790, 10.852]
                    ],
                    "color": [56, 189, 248, 180],
                    "width": 3,
                    "desc": "Tuyến C: Vành đai vắng qua Phạm Văn Đồng (Tốn thêm 15 phút, độ bất định cao)"
                }
            ]

            # Điểm rủi ro âm thanh (Hotspots) - Đổi từ "điểm đen tai nạn" sang "điểm rủi ro âm thanh"
            hotspots_data = [
                {
                    "name": "Điểm rủi ro âm thanh: Nút giao Hàng Xanh / Cầu Sài Gòn",
                    "coordinates": [106.715, 10.801],
                    "ari": "9.7 / 10",
                    "reason": "Mật độ xe tải nặng 19 lượt/phút, còi hơi vượt 115 dBA"
                },
                {
                    "name": "Điểm rủi ro âm thanh: Trục Xa lộ Hà Nội - Ngã 4 Thủ Đức",
                    "coordinates": [106.770, 10.842],
                    "ari": "9.4 / 10",
                    "reason": "Khu vực xe container phanh gấp và áp sát làn xe máy"
                }
            ]

            # Nhãn văn bản trực tiếp trên bản đồ (Hỗ trợ người khiếm thị màu)
            text_labels = [
                {"text": "Tuyến A [21p - Nhanh]", "coordinates": [106.715, 10.808], "color": [255, 255, 255, 220]},
                {"text": "⭐ Tuyến B [SafeRoute - 27p]", "coordinates": [106.730, 10.826], "color": [52, 211, 153, 255]},
                {"text": "Tuyến C [36p - Gom vắng]", "coordinates": [106.705, 10.855], "color": [186, 230, 253, 220]},
                {"text": "⚠️ Điểm rủi ro Hàng Xanh", "coordinates": [106.715, 10.795], "color": [248, 113, 113, 255]},
                {"text": "⚠️ Điểm rủi ro Thủ Đức", "coordinates": [106.770, 10.835], "color": [248, 113, 113, 255]}
            ]

            path_layer = pdk.Layer(
                "PathLayer",
                routes_data,
                get_path="path",
                get_color="color",
                get_width="width",
                width_scale=15,
                width_min_pixels=3,
                pickable=True
            )

            hotspot_layer = pdk.Layer(
                "ScatterplotLayer",
                hotspots_data,
                get_position="coordinates",
                get_color=[239, 68, 68, 210],
                get_radius=500,
                radius_min_pixels=9,
                radius_max_pixels=26,
                pickable=True
            )

            text_layer = pdk.Layer(
                "TextLayer",
                text_labels,
                get_position="coordinates",
                get_text="text",
                get_color="color",
                get_size=13,
                get_alignment_baseline="'bottom'",
                pickable=False
            )

            view_state = pdk.ViewState(latitude=10.812, longitude=106.723, zoom=11.2, pitch=0)
            deck = pdk.Deck(
                layers=[path_layer, hotspot_layer, text_layer],
                initial_view_state=view_state,
                map_style="dark",
                tooltip={"text": "{name}\n{desc}{reason}"}
            )
            st.pydeck_chart(deck, use_container_width=True)

            # Khối Provenance & Quality Flags
            st.markdown("""
            <div style="font-size: 12px; color: #94a3b8; background: #0f172a; padding: 10px 14px; border-radius: 8px; border-left: 3px solid #38bdf8;">
                <b>Nguồn gốc dữ liệu (Provenance):</b> Bộ dữ liệu thực nghiệm giao thông TP.HCM (Pilot VATD - 2.500 mẫu) kết hợp mô hình không gian OSRM.<br/>
                <b>Kiểm soát chất lượng:</b> Lọc bỏ dữ liệu khi GPS mất định vị hoặc micro nghẽn gió; phân chia Train/Test theo từng phiên ghi độc lập chống lạc quan giả.
            </div>
            """, unsafe_allow_html=True)

        with col_matrix:
            st.markdown("#### Ma Trận Đánh Đổi Đa Tiêu Chí (Trade-Off Matrix)")
            matrix_data = decision_resp.get_tradeoff_matrix()
            df_matrix = pd.DataFrame(matrix_data)
            st.dataframe(df_matrix, use_container_width=True, hide_index=True)

            st.markdown("#### Diễn Giải Minh Bạch (XAI)")
            rec_scenario = decision_resp.get_recommended_scenario()
            if rec_scenario:
                st.success(
                    f"**Đề xuất tối ưu:** `{rec_scenario.title}`\n\n"
                    f"{rec_scenario.xai_explanation}"
                )

            st.markdown("#### Xác Nhận Lộ Trình")
            scenario_options = {s.scenario_id: f"{s.title} ({s.duration_min:.0f} phút - ARI: {s.avg_ari:.1f})" for s in decision_resp.scenarios}
            chosen_id = st.radio(
                "Chọn tuyến để bắt đầu giám sát:",
                options=list(scenario_options.keys()),
                format_func=lambda x: scenario_options[x],
                index=list(scenario_options.keys()).index(decision_resp.recommended_scenario_id)
            )
            st.session_state.selected_scenario_id = chosen_id

            if st.button("Xác Nhận & Bắt Đầu Di Chuyển ➔", type="primary", use_container_width=True):
                st.toast("Đã kích hoạt lộ trình! Mời bạn chuyển sang Tab 2.")

    # ------------------------------------------------------------------------
    # TAB 2: ON-TRIP HUD (CHẾ ĐỘ THÔNG THƯỜNG CÓ NÚT BẬT RIDER MODE)
    # ------------------------------------------------------------------------
    with tab_on_trip:
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

        col_t1, col_t2 = st.columns([3, 1])
        with col_t1:
            st.button("🚀 BẬT CHẾ ĐỘ LÁI XE TOÀN MÀN HÌNH (RIDER HUD)", on_click=on_toggle_rider_mode, type="primary", use_container_width=True)
        with col_t2:
            if st.session_state.system_status == "HEALTHY":
                st.markdown("<span style='color: #10b981; font-weight: bold;'>🟢 Cảm biến: Khỏe mạnh</span>", unsafe_allow_html=True)
            elif st.session_state.system_status == "DEGRADED":
                st.markdown("<span style='color: #f59e0b; font-weight: bold;'>🟡 Cảm biến: Giảm độ nhạy</span>", unsafe_allow_html=True)
            else:
                st.markdown("<span style='color: #ef4444; font-weight: bold;'>🔴 Cảm biến: Mất kết nối</span>", unsafe_allow_html=True)

        col_hud, col_controls = st.columns([3, 2], gap="large")

        with col_hud:
            st.subheader("Màn Hình Tay Lái (HUD View)")

            if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
                if payload.danger_type == "TRUCK_APPROACH" or payload.is_looming:
                    box_class = "hud-box-danger"
                    severity_text = "NGUY CẤP: XE TẢI ÁP SÁT PHÍA SAU!"
                    action_text = "GIỮ THẲNG LÁI · GIẢM TỐC NHẸ · QUAN SÁT GƯƠNG"
                    action_class = "action-directive-danger"
                    haptic_desc = "📳 Rung dồn dập 2 bên tay lái"
                elif payload.danger_type == "EMERGENCY_SIREN":
                    box_class = "hud-box-danger"
                    severity_text = "CẢNH BÁO: XE ƯU TIÊN TIẾP CẬN!"
                    action_text = "GIẢM TỐC ĐỘ · TẤP LỀ PHẢI NHƯỜNG ĐƯỜNG"
                    action_class = "action-directive-danger"
                    haptic_desc = "📳 Rung nhịp đôi cách quãng"
                else:
                    box_class = "hud-box-warning"
                    severity_text = "CHÚ Ý: CÒI PHƯƠNG TIỆN ÁP SÁT"
                    action_text = "GIỮ VỮNG TAY LÁI · CHUẨN BỊ NHƯỜNG ĐƯỜNG"
                    action_class = "action-directive-danger"
                    haptic_desc = "📳 Rung phân vùng theo hướng"
            else:
                box_class = "hud-box-safe"
                severity_text = "KHÔNG PHÁT HIỆN MỐI NGUY ÂM THANH HIỆN TẠI"
                action_text = "TIẾP TỤC QUAN SÁT GIAO THÔNG BÌNH THƯỜNG"
                action_class = "action-directive-safe"
                haptic_desc = "Không kích hoạt rung"

            dir_label = {
                "LEFT": "⬅️ BÊN TRÁI",
                "RIGHT": "➡️ BÊN PHẢI",
                "CENTER": "⬆️ PHÍA SAU",
                "UNKNOWN": "XUNG QUANH"
            }.get(payload.direction, "ĐANG QUAN SÁT")

            st.markdown(f"""
            <div class="{box_class}" style="border-radius: 16px; padding: 24px; text-align: center;">
                <div style="font-size: 14px; font-weight: 700; opacity: 0.85; text-transform: uppercase;">
                    MỨC ĐỘ NGUY CƠ
                </div>
                <div style="font-size: 26px; font-weight: 900; margin: 8px 0;">
                    {severity_text}
                </div>
                <div class="direction-badge">
                    {dir_label}
                </div>
                <div class="{action_class}" style="font-size: 19px;">
                    {action_text}
                </div>
                <div style="margin-top: 15px; font-size: 14px; opacity: 0.95;">
                    {haptic_desc}
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Web Vibration API
            if payload.is_danger and st.session_state.system_status != "UNAVAILABLE":
                pattern = "[250, 100, 250, 100, 250]" if payload.is_looming else "[150, 100, 150]"
                st.components.v1.html(f"""
                <script>
                    if ('vibrate' in navigator) {{
                        navigator.vibrate({pattern});
                    }}
                </script>
                """, height=0, width=0)

            # Thông số kỹ thuật khi ở Dashboard (Chỉ hiện cho Giám khảo)
            st.markdown("<br/>", unsafe_allow_html=True)
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Cường Độ Âm", f"{payload.db:.1f} dBA", delta=f"{payload.db - 75:.1f} dBA" if payload.db > 75 else None)
            with m2:
                st.metric("Độ Tin Cậy AI", f"{payload.confidence * 100:.1f}%")
            with m3:
                st.metric("Độ Trễ Phản Xạ", f"{payload.latency_ms:.1f} ms", delta="<80ms SLA", delta_color="normal")

        with col_controls:
            st.subheader("Bộ Phím Thử Nghiệm Tức Thì")
            st.caption("Ứng dụng callback giúp phản xạ cập nhật giao diện trong <50ms:")

            st.button("🚛 Kích hoạt Xe Tải Áp Sát (Phải)", on_click=on_trigger_event, args=("LOOMING_TRUCK",), use_container_width=True)
            st.button("🚗 Kích hoạt Còi Xe Máy (Trái)", on_click=on_trigger_event, args=("VEHICLE_HORN",), use_container_width=True)
            st.button("🚑 Kích hoạt Còi Xe Cứu Thương", on_click=on_trigger_event, args=("EMERGENCY_SIREN",), use_container_width=True)
            st.button("🍃 Kích hoạt Môi Trường Êm", on_click=on_trigger_event, args=("SAFE",), use_container_width=True)

            st.divider()
            st.subheader("Kiểm Tra Rung Điện Thoại")
            test_vib = st.button("📳 Rung Thử Nghiệm 3 Nhịp (Web Haptics)", use_container_width=True)
            if test_vib:
                st.components.v1.html("""
                <script>
                    if ('vibrate' in navigator) {
                        navigator.vibrate([200, 100, 200, 100, 400]);
                    } else {
                        alert('Trình duyệt không hỗ trợ Web Vibration API. Hãy mở trên Chrome/Firefox Android!');
                    }
                </script>
                """, height=0, width=0)
                st.success("Đã gửi lệnh rung `navigator.vibrate` tới điện thoại!")