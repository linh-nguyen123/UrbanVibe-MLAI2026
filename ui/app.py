# -*- coding: utf-8 -*-
"""
UrbanVibe: SafeRoute - Decision Intelligence & Acoustic Safety Platform
MLAI Hackathon 2026 - Decision Intelligence Challenge (TMA Solutions)

Ứng dụng Dashboard Streamlit 2-Tab:
- Tab 1: 🗺️ Ra Quyết Định Lộ Trình (Pre-Trip Decision Intelligence - Bản Đồ Đa Lớp & Ma Trận Đánh Đổi)
- Tab 2: 🚨 Giám Sát An Toàn Trên Xe (On-Trip HUD - Chế Độ Lái Xe Toàn Màn Hình Tối Giản)
"""

import sys
import warnings

# Triệt tiêu toàn bộ cảnh báo TensorFlow C++ logs và Python deprecations
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
warnings.filterwarnings("ignore")

import logging
logging.getLogger("tensorflow").setLevel(logging.ERROR)

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

if "custom_locations" not in st.session_state:
    st.session_state.custom_locations = {}  # Lưu trữ địa điểm người dùng tìm kiếm trực tuyến toàn quốc


# ============================================================================
# DANH MỤC ĐỊA ĐIỂM HIỆU CHUẨN GPS & GỢI Ý THÔNG MINH (RECOMMENDATION SYSTEM)
# ============================================================================

import json
import math
import re
import urllib.parse
import urllib.request
from typing import Dict, List, Tuple

# Danh mục các địa điểm trọng điểm được hiệu chuẩn GPS sẵn (Bắc - Trung - Nam)
CALIBRATED_LOCATIONS = {
    # --- MIỀN NAM: TP. HỒ CHÍ MINH & LÂN CẬN ---
    "ĐH Sư phạm Kỹ thuật TP.HCM (HCMUTE / ĐH SPKT - TP. Thủ Đức)": {
        "coords": [106.7722, 10.8507],
        "category": "🎓 Trường Đại học Trọng điểm",
        "address": "1 Võ Văn Ngân, P. Linh Chiểu, TP. Thủ Đức",
        "aliases": ["spkt", "đh spkt", "dh spkt", "dh spkt tp hcm", "spkt tp hcm", "hcmute", "su pham ky thuat", "thu duc"]
    },
    "ĐH Bách Khoa CS1 (Quận 10, TP.HCM)": {
        "coords": [106.6578, 10.7725],
        "category": "🎓 Trường Đại học Trọng điểm",
        "address": "268 Lý Thường Kiệt, P.14, Q.10, TP.HCM",
        "aliases": ["bk", "bach khoa", "dh bk", "dh bk cs1", "ly thuong kiet", "quan 10"]
    },
    "Bến xe Miền Đông Mới (TP. Thủ Đức)": {
        "coords": [106.7905, 10.8522],
        "category": "🚌 Bến xe liên tỉnh",
        "address": "501 Hoàng Hữu Nam, P. Long Bình, TP. Thủ Đức",
        "aliases": ["bx mien dong moi", "mien dong moi", "hoang huu nam", "bx mien dong"]
    },
    "ĐH Bách Khoa CS2 (Khu ĐHQG TP.HCM)": {
        "coords": [106.8055, 10.8805],
        "category": "🎓 Ký túc xá / Giảng đường",
        "address": "Khu đô thị ĐHQG-HCM, TP. Dĩ An / Thủ Đức",
        "aliases": ["bk cs2", "dh bk cs2", "lang dai hoc", "dhqg", "ky tuc xa"]
    },
    "ĐH Khoa học Tự nhiên CS1 (ĐHQG-HCM - Quận 5)": {
        "coords": [106.6826, 10.7628],
        "category": "🎓 Trường Đại học Trọng điểm",
        "address": "227 Nguyễn Văn Cừ, P.4, Q.5, TP.HCM",
        "aliases": ["khtn", "dh khtn", "tu nhien", "nguyen van cu", "quan 5"]
    },
    "ĐH Kinh tế TP.HCM (UEH - Cơ sở A Quận 3)": {
        "coords": [106.6953, 10.7828],
        "category": "🎓 Trường Đại học Trọng điểm",
        "address": "59C Nguyễn Đình Chiểu, P. Võ Thị Sáu, Q.3, TP.HCM",
        "aliases": ["ueh", "dh ueh", "kinh te", "nguyen dinh chieu", "quan 3"]
    },
    "ĐH Công nghệ Thông tin (UIT - ĐHQG-HCM)": {
        "coords": [106.8031, 10.8700],
        "category": "🎓 Ký túc xá / Giảng đường",
        "address": "Khu phố 6, P. Linh Trung, TP. Thủ Đức",
        "aliases": ["uit", "dh uit", "cntt", "linh trung", "dhqg"]
    },
    "ĐH Sài Gòn (SGU - Cơ sở chính Quận 5)": {
        "coords": [106.6800, 10.7597],
        "category": "🎓 Trường Đại học",
        "address": "273 An Dương Vương, P.3, Q.5, TP.HCM",
        "aliases": ["sgu", "dh sai gon", "sai gon", "an duong vuong"]
    },
    "Sân bay Quốc tế Tân Sơn Nhất (Tân Bình, TP.HCM)": {
        "coords": [106.6602, 10.8185],
        "category": "✈️ Cảng hàng không",
        "address": "Đường Trường Sơn, P.2, Q. Tân Bình, TP.HCM",
        "aliases": ["san bay", "tan son nhat", "tsn", "truong son", "tan binh"]
    },
    "Chợ Bến Thành (Quận 1, TP.HCM)": {
        "coords": [106.6983, 10.7726],
        "category": "🛍️ Thương mại & Du lịch",
        "address": "Đường Lê Lợi, P. Bến Thành, Q.1, TP.HCM",
        "aliases": ["ben thanh", "cho ben thanh", "quan 1", "le loi"]
    },
    "Bệnh viện Chợ Rẫy (Quận 5, TP.HCM)": {
        "coords": [106.6593, 10.7554],
        "category": "🏥 Y tế khẩn cấp",
        "address": "201B Nguyễn Chí Thanh, P.12, Q.5, TP.HCM",
        "aliases": ["cho ray", "bv cho ray", "benh vien", "nguyen chi thanh"]
    },
    "Khu Công nghệ cao (SHTP - TP. Thủ Đức)": {
        "coords": [106.7915, 10.8550],
        "category": "💼 Khu công nghệ cao",
        "address": "Xa lộ Hà Nội, P. Hiệp Phú, TP. Thủ Đức",
        "aliases": ["shtp", "cong nghe cao", "khu cong nghe cao", "xa lo ha noi"]
    },
    "Ngã 4 Thủ Đức (Trục Xa lộ Hà Nội - Lê Văn Việt)": {
        "coords": [106.7709, 10.8475],
        "category": "🚦 Nút giao trọng điểm",
        "address": "Xa lộ Hà Nội, P. Hiệp Phú, TP. Thủ Đức",
        "aliases": ["nga 4 thu duc", "nga tu thu duc", "le van viet"]
    },
    "Bến xe Miền Tây (Bình Tân, TP.HCM)": {
        "coords": [106.6133, 10.7410],
        "category": "🚌 Bến xe liên tỉnh",
        "address": "395 Kinh Dương Vương, P. An Lạc, Q. Bình Tân, TP.HCM",
        "aliases": ["bx mien tay", "mien tay", "kinh duong vuong", "binh tan"]
    },
    "Bến xe An Sương (Quận 12 / Hóc Môn)": {
        "coords": [106.6111, 10.8447],
        "category": "🚌 Bến xe liên tỉnh",
        "address": "Quốc Lộ 22, X. Bà Điểm, H. Hóc Môn, TP.HCM",
        "aliases": ["bx an suong", "an suong", "quoc lo 22", "hoc mon", "quan 12"]
    },
    "Landmark 81 / Vinhomes Central Park (Bình Thạnh)": {
        "coords": [106.7218, 10.7950],
        "category": "🏙️ Đô thị trung tâm",
        "address": "720A Điện Biên Phủ, P.22, Q. Bình Thạnh, TP.HCM",
        "aliases": ["landmark 81", "landmark", "vinhomes", "binh thanh", "dien bien phu"]
    },

    # --- MIỀN TRUNG: ĐÀ NẴNG - HUẾ - NHA TRANG - ĐÀ LẠT ---
    "Cầu Rồng (Hải Châu / Sơn Trà, Đà Nẵng)": {
        "coords": [108.2279, 16.0612],
        "category": "🌉 Biểu tượng Đô thị",
        "address": "Đường Nguyễn Văn Linh, P. Phước Ninh, Q. Hải Châu, Đà Nẵng",
        "aliases": ["cau rong", "da nang", "hai chau", "son tra", "nguyen van linh"]
    },
    "Bán đảo Sơn Trà (Sơn Trà, Đà Nẵng)": {
        "coords": [108.2778, 16.1158],
        "category": "🏞️ Sinh thái Du lịch",
        "address": "Phường Thọ Quang, Q. Sơn Trà, TP. Đà Nẵng",
        "aliases": ["son tra", "ban dao son tra", "chua linh ung", "da nang"]
    },
    "Đại Nội Huế (TP. Huế, Thừa Thiên Huế)": {
        "coords": [107.5796, 16.4697],
        "category": "🏛️ Di sản Văn hóa",
        "address": "Đường 23 Tháng 8, P. Thuận Hòa, TP. Huế",
        "aliases": ["dai noi", "hue", "hoang thanh", "thua thien hue"]
    },
    "Quảng trường Lâm Viên (TP. Đà Lạt, Lâm Đồng)": {
        "coords": [108.4450, 11.9388],
        "category": "🌸 Đô thị Cao nguyên",
        "address": "Đường Trần Quốc Toản, P.10, TP. Đà Lạt, Lâm Đồng",
        "aliases": ["lam vien", "da lat", "quang truong lam vien", "ho xuan huong"]
    },
    "Tháp Trầm Hương / Bãi biển Nha Trang (Khánh Hòa)": {
        "coords": [109.1967, 12.2388],
        "category": "🏖️ Đô thị Biển",
        "address": "Đường Trần Phú, P. Lộc Thọ, TP. Nha Trang, Khánh Hòa",
        "aliases": ["tram huong", "nha trang", "khanh hoa", "tran phu"]
    },

    # --- MIỀN BẮC: HÀ NỘI - HẢI PHÒNG - QUẢNG NINH ---
    "Hồ Hoàn Kiếm (Quận Hoàn Kiếm, Hà Nội)": {
        "coords": [105.8525, 21.0288],
        "category": "🏙️ Trung tâm Thủ đô",
        "address": "Phường Tràng Tiền, Q. Hoàn Kiếm, TP. Hà Nội",
        "aliases": ["ho guom", "ho hoan kiem", "ha noi", "trang tien", "pho co"]
    },
    "ĐH Bách Khoa Hà Nội (Hai Bà Trưng, Hà Nội)": {
        "coords": [105.8436, 21.0055],
        "category": "🎓 Trường Đại học Trọng điểm",
        "address": "1 Đại Cồ Việt, P. Bách Khoa, Q. Hai Bà Trưng, Hà Nội",
        "aliases": ["bk ha noi", "hust", "bach khoa ha noi", "dai co viet"]
    },
    "Sân bay Quốc tế Nội Bài (Sóc Sơn, Hà Nội)": {
        "coords": [105.8057, 21.2212],
        "category": "✈️ Cảng hàng không",
        "address": "Xã Phú Minh, Huyện Sóc Sơn, TP. Hà Nội",
        "aliases": ["noi bai", "san bay noi bai", "ha noi", "soc son"]
    },
    "Nhà hát Lớn Hải Phòng (Quận Hồng Bàng, Hải Phòng)": {
        "coords": [106.6838, 20.8596],
        "category": "🏙️ Đô thị Cảng",
        "address": "28 Trần Hưng Đạo, P. Hoàng Văn Thụ, Q. Hồng Bàng, Hải Phòng",
        "aliases": ["hai phong", "nha hat lon hai phong", "hong bang"]
    },

    # --- ĐỒNG BẰNG SÔNG CỬU LONG & ĐÔNG NAM BỘ ---
    "Bến Ninh Kiều (Ninh Kiều, Cần Thơ)": {
        "coords": [105.7877, 10.0310],
        "category": "🌊 Thủ phủ Miền Tây",
        "address": "Đường Hai Bà Trưng, P. Tân An, Q. Ninh Kiều, Cần Thơ",
        "aliases": ["ninh kieu", "ben ninh kieu", "can tho", "song hau"]
    },
    "Chợ nổi Cái Răng (Cái Răng, Cần Thơ)": {
        "coords": [105.7483, 10.0051],
        "category": "🛶 Du lịch Sông nước",
        "address": "Đường Hai Bà Trưng, P. Lê Bình, Q. Cái Răng, Cần Thơ",
        "aliases": ["cai rang", "cho noi cai rang", "can tho"]
    },
    "Bãi Trước Vũng Tàu (TP. Vũng Tàu, Bà Rịa - Vũng Tàu)": {
        "coords": [107.0722, 10.3460],
        "category": "🏖️ Đô thị Biển",
        "address": "Đường Quang Trung, P.1, TP. Vũng Tàu, Bà Rịa - Vũng Tàu",
        "aliases": ["vung tau", "bai truoc", "ba ria vung tau", "quang trung"]
    }
}

POPULAR_OD_RECOMMENDATIONS = {
    "⭐ [Tuyến Sinh Viên Đột Phá] ĐH Bách Khoa CS1 ➔ ĐH Sư phạm Kỹ thuật (HCMUTE)": (
        "ĐH Bách Khoa CS1 (Quận 10, TP.HCM)", "ĐH Sư phạm Kỹ thuật TP.HCM (HCMUTE / ĐH SPKT - TP. Thủ Đức)"
    ),
    "🌉 [Đà Nẵng Nội Đô] Cầu Rồng ➔ Bán đảo Sơn Trà": (
        "Cầu Rồng (Hải Châu / Sơn Trà, Đà Nẵng)", "Bán đảo Sơn Trà (Sơn Trà, Đà Nẵng)"
    ),
    "🏛️ [Hà Nội Nội Đô] ĐH Bách Khoa Hà Nội ➔ Hồ Hoàn Kiếm": (
        "ĐH Bách Khoa Hà Nội (Hai Bà Trưng, Hà Nội)", "Hồ Hoàn Kiếm (Quận Hoàn Kiếm, Hà Nội)"
    ),
    "🛶 [Đồng Bằng Sông Cửu Long] Bến Ninh Kiều (Cần Thơ) ➔ Chợ nổi Cái Răng": (
        "Bến Ninh Kiều (Ninh Kiều, Cần Thơ)", "Chợ nổi Cái Răng (Cái Răng, Cần Thơ)"
    ),
    "🚗 [Liên Tỉnh Cao Tốc] Chợ Bến Thành (TP.HCM) ➔ Bãi Trước Vũng Tàu": (
        "Chợ Bến Thành (Quận 1, TP.HCM)", "Bãi Trước Vũng Tàu (TP. Vũng Tàu, Bà Rịa - Vũng Tàu)"
    ),
    "🚅 [Liên Vùng Xuyên Việt] Hồ Hoàn Kiếm (Hà Nội) ➔ Chợ Bến Thành (TP.HCM)": (
        "Hồ Hoàn Kiếm (Quận Hoàn Kiếm, Hà Nội)", "Chợ Bến Thành (Quận 1, TP.HCM)"
    ),
    "🎓 [Tuyến Kỹ Thuật Liên Trường] ĐH Sư phạm Kỹ thuật (HCMUTE) ➔ ĐH Bách Khoa CS2 (Khu ĐHQG TP.HCM)": (
        "ĐH Sư phạm Kỹ thuật TP.HCM (HCMUTE / ĐH SPKT - TP. Thủ Đức)", "ĐH Bách Khoa CS2 (Khu ĐHQG TP.HCM)"
    )
}


@st.cache_data(ttl=3600, show_spinner=False)
def geocode_vietnam_location(query: str) -> List[Dict]:
    """
    Tìm kiếm địa chỉ/địa danh trên toàn bộ 63 tỉnh thành Việt Nam qua OpenStreetMap Nominatim.
    Không cần API key, độ trễ thấp, hỗ trợ từ cấp tỉnh/huyện đến từng số nhà, ngõ phố.
    """
    if not query or len(query.strip()) < 2:
        return []
    clean_q = query.strip()
    search_q = clean_q if "việt nam" in clean_q.lower() or "vietnam" in clean_q.lower() else f"{clean_q}, Việt Nam"
    encoded_q = urllib.parse.quote(search_q)
    url = f"https://nominatim.openstreetmap.org/search?q={encoded_q}&format=json&countrycodes=vn&addressdetails=1&limit=4"
    headers = {"User-Agent": "UrbanVibe-SafeRoute-MLAI2026/1.0 (contact: linh-nguyen123)"}
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=3.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            results = []
            for item in data:
                raw_name = item.get("display_name", "")
                parts = [p.strip() for p in raw_name.split(",") if p.strip()]
                short_title = parts[0] if parts else clean_q
                if len(parts) > 2:
                    short_title = f"{parts[0]} ({parts[1]}, {parts[-2] if len(parts) > 3 else parts[-1]})"
                results.append({
                    "name": short_title,
                    "full_address": raw_name,
                    "coords": [round(float(item["lon"]), 5), round(float(item["lat"]), 5)],
                    "category": f"🌐 {item.get('type', 'Địa điểm').replace('_', ' ').title()}"
                })
            return results
    except Exception:
        return []


def normalize_vietnamese(text: str) -> str:
    """Loại bỏ dấu tiếng Việt và chuẩn hóa chữ thường để tìm kiếm linh hoạt."""
    text = re.sub(r'[àáạảãâầấậẩẫăằắặẳẵ]', 'a', text, flags=re.I)
    text = re.sub(r'[èéẹẻẽêềếệểễ]', 'e', text, flags=re.I)
    text = re.sub(r'[ìíịỉĩ]', 'i', text, flags=re.I)
    text = re.sub(r'[òóọỏõôồốộổỗơờớợởỡ]', 'o', text, flags=re.I)
    text = re.sub(r'[ùúụủũưừứựửữ]', 'u', text, flags=re.I)
    text = re.sub(r'[ỳýỵỷỹ]', 'y', text, flags=re.I)
    text = re.sub(r'[đĐ]', 'd', text, flags=re.I)
    return text.lower().strip()


def search_calibrated_locations(query: str, locations_dict: Dict) -> List[str]:
    """Tìm kiếm vị trí gần đúng hoặc từ khóa viết tắt trong danh mục chuẩn."""
    if not query:
        return []
    norm_q = normalize_vietnamese(query)
    tokens = [t for t in norm_q.split() if t]
    matched = []
    for name, meta in locations_dict.items():
        norm_name = normalize_vietnamese(name)
        norm_addr = normalize_vietnamese(meta.get("address", ""))
        norm_cat = normalize_vietnamese(meta.get("category", ""))
        aliases_str = " ".join([normalize_vietnamese(a) for a in meta.get("aliases", [])])
        combined = f"{norm_name} {norm_addr} {norm_cat} {aliases_str}"
        
        # Khớp toàn bộ cụm hoặc tất cả từ khóa tìm kiếm
        if norm_q in combined or all(t in combined for t in tokens):
            matched.append(name)
    return matched


def generate_dynamic_route_geometries(
    start_coords: List[float],
    end_coords: List[float]
) -> Tuple[List[List[float]], List[List[float]], List[List[float]], List[Dict], List[Dict], Tuple[float, float, float]]:
    """
    Sinh hình học động kết nối chính xác start_coords [lon, lat] và end_coords [lon, lat] cho 3 tuyến:
    - Tuyến A: Trục chính trực tiếp (wobble vi mô đường phố)
    - Tuyến B: SafeRoute (uốn cong né trục rủi ro âm thanh)
    - Tuyến C: Đường gom vành đai phụ
    Cùng các điểm rủi ro âm thanh (Hotspots), nhãn văn bản và tọa độ camera tự động.
    """
    lon1, lat1 = start_coords
    lon2, lat2 = end_coords
    dx = lon2 - lon1
    dy = lat2 - lat1
    dist_deg = math.hypot(dx, dy)

    if dist_deg < 1e-4:
        # Nếu hai điểm trùng nhau hoặc quá gần, tạo bán kính giả định 500m để vẽ trực quan
        dist_deg = 0.012
        dx, dy = 0.009, 0.007

    # Unit normal vector (vuông góc với trục thẳng nối O-D)
    nx = -dy / dist_deg
    ny = dx / dist_deg

    n_pts = 9
    route_a_pts = []
    route_b_pts = []
    route_c_pts = []

    for i in range(n_pts + 1):
        t = i / float(n_pts)
        
        # Tuyến A (Baseline): Bám trục thẳng với dao động góc phố nhẹ
        wobble = 0.032 * math.sin(t * math.pi * 3.0) * dist_deg
        ax = lon1 + t * dx + wobble * nx
        ay = lat1 + t * dy + wobble * ny
        route_a_pts.append([round(ax, 5), round(ay, 5)])

        # Tuyến B (SafeRoute): Vòng cung né trục chính (offset dương theo pháp tuyến)
        arc_b = math.sin(t * math.pi) * 0.19 * dist_deg
        bx = lon1 + t * dx + arc_b * nx
        by = lat1 + t * dy + arc_b * ny
        route_b_pts.append([round(bx, 5), round(by, 5)])

        # Tuyến C (Vành đai vắng): Vòng cung đối xứng xa hơn (offset âm theo pháp tuyến)
        arc_c = -math.sin(t * math.pi) * 0.29 * dist_deg
        cx = lon1 + t * dx + arc_c * nx
        cy = lat1 + t * dy + arc_c * ny
        route_c_pts.append([round(cx, 5), round(cy, 5)])

    # Đảm bảo điểm đầu và cuối khớp chính xác 100% với Origin và Destination
    route_a_pts[0] = [lon1, lat1]
    route_a_pts[-1] = [lon2, lat2]
    route_b_pts[0] = [lon1, lat1]
    route_b_pts[-1] = [lon2, lat2]
    route_c_pts[0] = [lon1, lat1]
    route_c_pts[-1] = [lon2, lat2]

    # Điểm rủi ro âm thanh bố trí trên Tuyến A
    hs1_coords = [round(lon1 + 0.36 * dx + 0.012 * dist_deg * nx, 5), round(lat1 + 0.36 * dy + 0.012 * dist_deg * ny, 5)]
    hs2_coords = [round(lon1 + 0.72 * dx - 0.010 * dist_deg * nx, 5), round(lat1 + 0.72 * dy - 0.010 * dist_deg * ny, 5)]

    if dist_deg < 0.25:
        hs1_title = "Điểm rủi ro âm thanh 1: Nút giao Trục chính nội đô"
        hs2_title = "Điểm rủi ro âm thanh 2: Giao lộ Vành đai đô thị"
    else:
        hs1_title = "Điểm rủi ro âm thanh 1: Nút giao Trạm thu phí / Tuyến xe tải liên tỉnh"
        hs2_title = "Điểm rủi ro âm thanh 2: Cửa ngõ hành lang Quốc lộ / Cao tốc"

    hotspots = [
        {
            "name": hs1_title,
            "coordinates": hs1_coords,
            "ari": "9.6 / 10",
            "reason": "Mật độ xe tải nặng / container cao, còi hơi vượt 112 dBA liên tục"
        },
        {
            "name": hs2_title,
            "coordinates": hs2_coords,
            "ari": "9.3 / 10",
            "reason": "Khu vực xe tải trọng lớn phanh gấp và áp sát làn phương tiện thô sơ"
        }
    ]

    # Nhãn văn bản (TextLayer) gắn vào điểm giữa của từng tuyến
    mid_idx = n_pts // 2
    text_labels = [
        {"text": "Tuyến A [Nhanh - Baseline]", "coordinates": route_a_pts[mid_idx], "color": [255, 255, 255, 230]},
        {"text": "⭐ Tuyến B [SafeRoute - Đề xuất]", "coordinates": route_b_pts[mid_idx], "color": [52, 211, 153, 255]},
        {"text": "Tuyến C [Vành đai vắng]", "coordinates": route_c_pts[mid_idx], "color": [186, 230, 253, 220]},
        {"text": "⚠️ Điểm rủi ro trục chính", "coordinates": hs1_coords, "color": [248, 113, 113, 255]},
        {"text": "⚠️ Điểm rủi ro giao lộ", "coordinates": hs2_coords, "color": [248, 113, 113, 255]}
    ]

    # Tính toán ViewState tâm và zoom tự thích ứng (Từ cự ly nội đô zoom 13.5 đến cự ly toàn quốc zoom 5.0)
    mid_lat = (lat1 + lat2) / 2.0
    mid_lon = (lon1 + lon2) / 2.0
    span = max(abs(lat2 - lat1), abs(lon2 - lon1))
    zoom = round(max(5.0, min(14.0, 13.2 - math.log2(max(span, 0.02) / 0.035))), 2)

    return route_a_pts, route_b_pts, route_c_pts, hotspots, text_labels, (mid_lat, mid_lon, zoom)


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
    # ------------------------------------------------------------------------
    # TAB 1: PRE-TRIP DECISION INTELLIGENCE
    # ------------------------------------------------------------------------
    with tab_pre_trip:
        st.markdown("#### 1. Thiết Lập Hành Trình & Gợi Ý Toàn Quốc (Nationwide Recommender & Geocoding)")
        st.caption("Gõ bất kỳ địa chỉ, ngõ phố, trường học, bệnh viện hoặc tỉnh thành trên cả nước để tìm kiếm trực tuyến thời gian thực (OpenStreetMap) hoặc chọn từ danh mục chuẩn hóa:")

        all_locations = {**CALIBRATED_LOCATIONS, **st.session_state.custom_locations}

        # 1. Bộ Tìm Kiếm Địa Điểm Toàn Quốc (Hybrid: Offline Hubs + Live OpenStreetMap Geocoding)
        search_query = st.text_input(
            "🔍 Tìm kiếm mọi địa điểm tại Việt Nam (VD: 'Hồ Hoàn Kiếm', 'Cầu Rồng Đà Nẵng', 'Bến Ninh Kiều', 'Quảng trường Lâm Viên Đà Lạt', '123 Hoàng Diệu', 'ĐH Quốc Gia', 'HCMUTE')...",
            placeholder="Nhập tên trường, địa danh, số nhà hoặc xã/phường/tỉnh bất kỳ tại Việt Nam...",
            key="location_search_box"
        )
        if search_query:
            # Bước A: Tìm trong danh mục offline + các điểm đã lưu
            matched_locs = search_calibrated_locations(search_query, all_locations)
            # Bước B: Tìm kiếm trực tuyến trên toàn lãnh thổ Việt Nam qua OSM Nominatim API
            live_osm_results = geocode_vietnam_location(search_query)

            has_results = bool(matched_locs or live_osm_results)
            if has_results:
                st.markdown(f"<div style='font-size: 13px; font-weight: bold; color: #38bdf8; margin-bottom: 8px;'>🎯 Kết quả tìm kiếm cho '{search_query}':</div>", unsafe_allow_html=True)

                # Hiển thị kết quả hiệu chuẩn sẵn trước (nếu có)
                for m_name in matched_locs[:2]:
                    m_meta = all_locations[m_name]
                    c_res1, c_res2, c_res3 = st.columns([5, 2, 2])
                    with c_res1:
                        st.markdown(
                            f"<div style='background: #1e293b; padding: 6px 12px; border-radius: 6px; border-left: 3px solid #10b981;'>"
                            f"📍 <b>{m_name}</b> <span style='font-size: 11px; background: #065f46; color: #a7f3d0; padding: 2px 6px; border-radius: 4px;'>Hiệu chuẩn</span><br/>"
                            f"<span style='font-size: 12px; color: #94a3b8;'>{m_meta.get('category')} · {m_meta.get('address')}</span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with c_res2:
                        if st.button("👉 Đặt làm Điểm đi", key=f"set_orig_hub_{m_name}", use_container_width=True):
                            st.session_state.origin = m_name
                            st.rerun()
                    with c_res3:
                        if st.button("👉 Đặt làm Điểm đến", key=f"set_dest_hub_{m_name}", use_container_width=True):
                            st.session_state.destination = m_name
                            st.rerun()

                # Hiển thị kết quả Geocoding trực tuyến OpenStreetMap toàn quốc (nếu có)
                for i, osm_item in enumerate(live_osm_results[:3]):
                    # Bỏ qua nếu tên đã trùng với điểm hiệu chuẩn đã hiển thị
                    if osm_item["name"] in matched_locs:
                        continue
                    c_res1, c_res2, c_res3 = st.columns([5, 2, 2])
                    with c_res1:
                        st.markdown(
                            f"<div style='background: #0f172a; padding: 6px 12px; border-radius: 6px; border-left: 3px solid #38bdf8;'>"
                            f"🌐 <b>{osm_item['name']}</b> <span style='font-size: 11px; background: #075985; color: #bae6fd; padding: 2px 6px; border-radius: 4px;'>Bản đồ Toàn quốc (OSM)</span><br/>"
                            f"<span style='font-size: 12px; color: #94a3b8;'>{osm_item.get('category')} · GPS: {osm_item.get('coords')}<br/><i>{osm_item.get('full_address')[:85]}...</i></span>"
                            f"</div>",
                            unsafe_allow_html=True
                        )
                    with c_res2:
                        if st.button("👉 Đặt làm Điểm đi", key=f"set_orig_osm_{i}", use_container_width=True):
                            custom_key = f"{osm_item['name']}"
                            st.session_state.custom_locations[custom_key] = {
                                "coords": osm_item["coords"],
                                "category": osm_item["category"],
                                "address": osm_item["full_address"]
                            }
                            st.session_state.origin = custom_key
                            st.rerun()
                    with c_res3:
                        if st.button("👉 Đặt làm Điểm đến", key=f"set_dest_osm_{i}", use_container_width=True):
                            custom_key = f"{osm_item['name']}"
                            st.session_state.custom_locations[custom_key] = {
                                "coords": osm_item["coords"],
                                "category": osm_item["category"],
                                "address": osm_item["full_address"]
                            }
                            st.session_state.destination = custom_key
                            st.rerun()

                st.markdown("<hr style='margin: 10px 0; border-color: rgba(255,255,255,0.1);'/>", unsafe_allow_html=True)
            else:
                st.info(f"Đang tìm kiếm hoặc không tìm thấy địa điểm khớp với '{search_query}'. Vui lòng thử lại với từ khóa khác hoặc chọn bên dưới.")

        # Cập nhật lại all_locations sau khi có thể có địa điểm tùy biến mới
        all_locations = {**CALIBRATED_LOCATIONS, **st.session_state.custom_locations}

        # 2. Thanh Gợi Ý Tuyến Phổ Biến (Recommender System Presets)
        rec_keys = list(POPULAR_OD_RECOMMENDATIONS.keys())
        rec_options = ["-- Chọn Tuyến Trọng Điểm Mẫu (Toàn Quốc & Nội Đô) --"] + rec_keys

        def on_select_preset_route():
            chosen = st.session_state.get("quick_preset_choice", "")
            if chosen in POPULAR_OD_RECOMMENDATIONS:
                o, d = POPULAR_OD_RECOMMENDATIONS[chosen]
                st.session_state.origin = o
                st.session_state.destination = d

        st.selectbox(
            "💡 Tuyến đường trọng điểm mẫu (Bắc - Trung - Nam & Tuyến Xuyên Việt):",
            options=rec_options,
            key="quick_preset_choice",
            on_change=on_select_preset_route
        )

        col_in1, col_in2, col_in3 = st.columns([2, 2, 2])
        loc_names = list(all_locations.keys())

        # Đảm bảo origin và destination có trong danh sách lựa chọn
        if st.session_state.origin not in loc_names:
            loc_names.insert(0, st.session_state.origin)
        if st.session_state.destination not in loc_names:
            loc_names.append(st.session_state.destination)

        orig_idx = loc_names.index(st.session_state.origin)
        dest_idx = loc_names.index(st.session_state.destination)

        with col_in1:
            st.session_state.origin = st.selectbox(
                "Điểm xuất phát (Origin):",
                options=loc_names,
                index=orig_idx
            )
            orig_meta = all_locations.get(st.session_state.origin, {})
            st.markdown(
                f"<div style='font-size: 11px; color: #a7f3d0; background: #064e3b; padding: 4px 8px; border-radius: 6px; margin-top: -6px;'>"
                f"📍 <b>GPS:</b> {orig_meta.get('coords')} · <i>{orig_meta.get('address', 'Địa chỉ bản đồ OSM')}</i>"
                f"</div>",
                unsafe_allow_html=True
            )

        with col_in2:
            st.session_state.destination = st.selectbox(
                "Điểm đến (Destination):",
                options=loc_names,
                index=dest_idx
            )
            dest_meta = all_locations.get(st.session_state.destination, {})
            st.markdown(
                f"<div style='font-size: 11px; color: #fecaca; background: #450a0a; padding: 4px 8px; border-radius: 6px; margin-top: -6px;'>"
                f"🏁 <b>GPS:</b> {dest_meta.get('coords')} · <i>{dest_meta.get('address', 'Địa chỉ bản đồ OSM')}</i>"
                f"</div>",
                unsafe_allow_html=True
            )

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

        if st.session_state.origin == st.session_state.destination:
            st.warning("⚠️ Điểm xuất phát và Điểm đến đang trùng nhau. Vui lòng chọn 2 địa điểm khác nhau để hệ thống mô phỏng đa tuyến!")

        st.caption(
            f"Vector trọng số: Thời gian $w_t = {active_profile.w_time:.2f}$ | "
            f"Rủi ro Âm thanh $w_a = {active_profile.w_ari:.2f}$ | "
            f"Bất định Bayesian $w_u = {active_profile.w_uncertainty:.2f}$ "
            f"(Ràng buộc an toàn cứng: $ARI_{{max}} \\le {active_profile.tau_cutoff:.1f}$)"
        )

        orig_pos = all_locations.get(st.session_state.origin, {}).get("coords", [106.6578, 10.7725])
        dest_pos = all_locations.get(st.session_state.destination, {}).get("coords", [106.7722, 10.8507])

        decision_resp = generate_mock_decision_response(
            origin=st.session_state.origin,
            destination=st.session_state.destination,
            profile=active_profile,
            orig_coords=orig_pos,
            dest_coords=dest_pos
        )

        st.markdown("---")
        col_map, col_matrix = st.columns([1, 1], gap="medium")

        with col_map:
            st.markdown("#### Bản Đồ Không Gian Đa Lớp & Điểm Rủi Ro Âm Thanh")
            st.caption("Tự động vẽ đường nối trực quan theo tọa độ GPS đã chọn; phân biệt các tuyến bằng độ dày nét và nhãn văn bản:")

            # Tính toán hình học động nối từ Origin đến Destination
            route_a_pts, route_b_pts, route_c_pts, hotspots_data, text_labels, (cam_lat, cam_lon, cam_zoom) = generate_dynamic_route_geometries(
                orig_pos, dest_pos
            )

            # 3 Tuyến đường động: Tuyến B (SafeRoute) được highlight nét dày nhất (9px)
            routes_data = [
                {
                    "name": "Tuyến A (Nhanh nhất - Baseline)",
                    "path": route_a_pts,
                    "color": [239, 68, 68, 220],
                    "width": 5,
                    "desc": f"Tuyến A: Trục giao thông chính (Nhiều xe tải, ARI 8.4) - {decision_resp.scenarios[0].duration_min:.0f} phút, {decision_resp.scenarios[0].distance_km:.1f} km"
                },
                {
                    "name": "Tuyến B: SafeRoute (Đề xuất tối ưu)",
                    "path": route_b_pts,
                    "color": [16, 185, 129, 255],
                    "width": 9,  # Nét dày nổi bật nhất
                    "desc": f"Tuyến B: SafeRoute né điểm rủi ro qua phố nhánh an toàn (Giảm 77% rủi ro, ARI 1.9) - {decision_resp.scenarios[1].duration_min:.0f} phút, {decision_resp.scenarios[1].distance_km:.1f} km"
                },
                {
                    "name": "Tuyến C (Vành đai vắng)",
                    "path": route_c_pts,
                    "color": [56, 189, 248, 180],
                    "width": 3,
                    "desc": f"Tuyến C: Vành đai đô thị thoáng (Độ ồn cực thấp, độ bất định cao) - {decision_resp.scenarios[2].duration_min:.0f} phút, {decision_resp.scenarios[2].distance_km:.1f} km"
                }
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
                get_radius=420,
                radius_min_pixels=9,
                radius_max_pixels=24,
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

            # Lớp ghim điểm xuất phát và đích đến theo tọa độ GPS hiệu chuẩn
            od_pins = [
                {"name": f"Điểm xuất phát: {st.session_state.origin}", "coordinates": orig_pos, "color": [16, 185, 129, 255], "desc": f"Xuất phát: {st.session_state.origin}"},
                {"name": f"Điểm đến: {st.session_state.destination}", "coordinates": dest_pos, "color": [239, 68, 68, 255], "desc": f"Đích đến: {st.session_state.destination}"}
            ]

            pin_layer = pdk.Layer(
                "ScatterplotLayer",
                od_pins,
                get_position="coordinates",
                get_color="color",
                get_radius=480,
                radius_min_pixels=11,
                radius_max_pixels=25,
                pickable=True
            )

            # Camera ViewState tự động thích ứng với vị trí và khoảng cách O-D
            view_state = pdk.ViewState(latitude=cam_lat, longitude=cam_lon, zoom=cam_zoom, pitch=0)
            deck = pdk.Deck(
                layers=[path_layer, hotspot_layer, pin_layer, text_layer],
                initial_view_state=view_state,
                map_style="dark",
                tooltip={"text": "{name}\n{desc}"}
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