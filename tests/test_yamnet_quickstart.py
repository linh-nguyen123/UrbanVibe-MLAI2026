import time
import numpy as np
import sounddevice as sd
import tensorflow_hub as hub

print("=" * 55)
print("   URBANVIBE - KIỂM TRA MICRO & MÔ HÌNH YAMNET (PAIR 1)   ")
print("=" * 55)

# 1. Tải mô hình YAMNet từ TensorFlow Hub
print("\n[1/3] Đang tải mô hình YAMNet (lần đầu sẽ mất khoảng 1 phút)...")
try:
    yamnet_model = hub.load("https://tfhub.dev/google/yamnet/1")
    class_map_path = yamnet_model.class_map_path().numpy().decode("utf-8")
    class_names = [line.strip().split(",")[2] for line in open(class_map_path).readlines()[1:]]
    print(" -> Tải mô hình YAMNet thành công!")
except Exception as e:
    print(f" -> [LỖI] Không tải được mô hình: {e}")
    exit()

# 2. Thu âm trực tiếp từ micro vật lý
SAMPLE_RATE = 16000
DURATION = 0.975  # Cửa sổ đầu vào chuẩn của YAMNet (15,600 mẫu)

print(f"\n[2/3] Đang mở micro thu âm trong {DURATION} giây...")
print(" -> Hãy thử vỗ tay, huýt sáo hoặc nói vào mic...")
try:
    recording = sd.rec(int(DURATION * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype="float32")
    sd.wait()
    waveform = np.squeeze(recording)
    print(" -> Thu âm thành công!")
except Exception as e:
    print(f" -> [LỖI] Micro không hoạt động hoặc bị chặn quyền: {e}")
    exit()

# 3. Tính toán Decibel và chạy suy luận AI
print("\n[3/3] Đang phân loại phổ âm thanh...")
start_time = time.time()
scores, embeddings, spectrogram = yamnet_model(waveform)
latency = (time.time() - start_time) * 1000

# Tính năng lượng RMS và Decibel tương đối
rms = np.sqrt(np.mean(waveform**2))
db = 20 * np.log10(rms + 1e-6) + 100

# Trích xuất top 3 nhãn có xác suất cao nhất
mean_scores = np.mean(scores.numpy(), axis=0)
top_indices = np.argsort(mean_scores)[::-1][:3]

print("\n" + "-" * 50)
print("             KẾT QUẢ PHÂN TÍCH ÂM THANH             ")
print("-" * 50)
print(f"• Cường độ âm lượng: {db:.1f} dB (RMS: {rms:.4f})")
print(f"• Thời gian suy luận: {latency:.2f} ms")
print("• Top 3 nhãn nhận diện được:")
for rank, idx in enumerate(top_indices, 1):
    print(f"   {rank}. {class_names[idx]:<30} | {mean_scores[idx] * 100:.1f}%")
print("-" * 50)
print("[✓] Pipeline Audio & Model hoạt động bình thường!\n")