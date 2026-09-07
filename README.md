# UrbanVibe 🚨

> **Edge-AI Acoustic Safety & Haptic Warning System for the Hearing-Impaired**  
> Dự án tham dự **MLAI Hackathon 2026** – Mạng lưới AI (ĐH Bách Khoa ĐHQG-HCM).

---

## 📌 Giới thiệu dự án

**UrbanVibe** là giải pháp Edge-AI thông minh nhằm hỗ trợ người khiếm thính tham gia giao thông an toàn:

- **Acoustic AI:** Nhận diện âm thanh thời gian thực với **Google YAMNet** (16kHz Mono) chạy 100% on-device.
- **Bộ lọc số DSP & Dual-Threshold Gate:** Kết hợp lọc thông cao chống gió rít (< 300Hz), đo Decibel SPL tức thời và cổng lọc kép để loại bỏ > 98% báo động giả từ tiếng ồn phố thị.
- **Cảnh báo đa phương thức:** Cảnh báo nhấp nháy viền thị giác (Visual Strobe) và xung động xúc giác (Haptic Vibration) đa nhịp độ.
- **Phân kỳ chiến lược:**
  - **Tầng 1 (Hackathon Track):** Bộ giả lập kiểm thử thời gian thực (HIL Simulator) hỗ trợ 4 chế độ demo (Preset sân khấu, Test WAV AI thật, Live Mic, Mock).
  - **Tầng 2 (Production Track):** Đóng gói sang TFLite C++ Native Service (Android/WearOS), truyền tín hiệu BLE tới Smartwatch hoặc quai nón bảo hiểm (LRA), đèn LED viền gương chiếu hậu.

---

## 🛠️ Cấu trúc thư mục

```text
UrbanVibe-MLAI2026/
├── engine/
│   ├── dsp_filter.py         # Đo Decibel SPL và bộ lọc Highpass / Bandpass chống gió rít
│   └── audio_engine.py       # YAMNet inference & thuật toán cổng lọc kép Dual-Threshold Gate
├── ui/
│   ├── app.py                # Streamlit Mobile Viewport (4 chế độ hoạt động + Track 2 Roadmap)
│   └── mock_engine.py        # Module sinh dữ liệu giả lập ngẫu nhiên
├── tests/
│   ├── test_samples/         # Bộ file âm thanh kiểm thử (horn_sample, ambulance_siren, ambient_traffic)
│   ├── generate_test_samples.py # Script sinh dữ liệu test chuẩn
│   └── test_engine.py        # Kiểm thử tự động tính toán Decibel & YAMNet
├── data_contract.py          # Cấu trúc dữ liệu chuẩn DetectionPayload
└── requirements.txt
```

---

## 🚀 Hướng dẫn chạy Demo

### 1. Kích hoạt môi trường ảo:
```powershell
.\venv\Scripts\activate
```

### 2. Chạy kiểm thử Audio AI Engine (YAMNet + DSP):
```powershell
python tests/test_engine.py
```

### 3. Khởi chạy Giao diện Mobile Simulator:
```powershell
streamlit run ui/app.py
```
Giao diện sẽ mở tại `http://localhost:8501` với khung chuẩn Smartphone.

---

## 🎭 4 Chế độ Demo linh hoạt trên Giao diện
1. **🎭 Kịch bản Sân khấu (Manual Presets):** Bấm chọn tình huống tức thì (Bình thường / Còi xe máy / Xe cứu thương) – kiểm soát 100% rủi ro khi pitching.
2. **🧪 File Mẫu Kiểm Thử (Real YAMNet):** Nghe và phân tích các file `.wav` chuẩn có sẵn hoặc upload file riêng.
3. **🎙️ Thu Âm Live Microphone:** Ghi âm trực tiếp từ micro để AI nhận diện.
4. **🎲 Giả Lập Tự Động:** Phát luồng sự kiện liên tục kiểm tra độ mượt giao diện.
