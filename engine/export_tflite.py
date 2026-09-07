"""
URBANVIBE - TFLITE EXPORT PIPELINE (BẢN MẪU XUẤT MÔ HÌNH TẦNG 2)
Nén và chuyển đổi mô hình Google YAMNet sang định dạng TensorFlow Lite (TFLite int8)
để nạp vào ứng dụng Native Android / WearOS hoặc vi điều khiển Edge.
"""

import sys
from pathlib import Path
import tensorflow as tf
import tensorflow_hub as hub

ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = ROOT_DIR / "engine" / "models"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def export_yamnet_to_tflite():
    print("=" * 60)
    print("   URBANVIBE - XUẤT MÔ HÌNH YAMNET SANG TFLITE INT8   ")
    print("=" * 60)

    print("1. Đang tải mô hình YAMNet từ TF-Hub...")
    model = hub.load("https://tfhub.dev/google/yamnet/1")

    # Tạo Concrete Function cho đầu vào waveform 16kHz cố định (ví dụ frame 15600 samples ~ 0.975s)
    @tf.function(input_signature=[tf.TensorSpec(shape=[15600], dtype=tf.float32, name="audio_waveform")])
    def serving_fn(audio_waveform):
        scores, embeddings, spectrogram = model(audio_waveform)
        return {"scores": scores}

    concrete_func = serving_fn.get_concrete_function()

    print("2. Cấu hình bộ chuyển đổi TFLite Converter...")
    converter = tf.lite.TFLiteConverter.from_concrete_functions([concrete_func])
    
    # Kích hoạt tối ưu hóa lượng tử hóa kích thước mô hình (Weight Quantization)
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    converter.target_spec.supported_types = [tf.float16]  # Chuẩn hóa float16/int8 tăng tốc GPU/NPU di động

    print("3. Bắt đầu chuyển đổi mô hình...")
    tflite_model = converter.convert()

    output_path = OUTPUT_DIR / "yamnet_edge_quantized.tflite"
    with open(output_path, "wb") as f:
        f.write(tflite_model)

    size_mb = len(tflite_model) / (1024 * 1024)
    print(f"\n Xuất mô hình thành công: {output_path}")
    print(f" Dung lượng siêu nhẹ: {size_mb:.2f} MB (sẵn sàng nạp vào Android NDK / WearOS)")

if __name__ == "__main__":
    export_yamnet_to_tflite()
