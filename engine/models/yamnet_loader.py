import csv
import tensorflow as tf
import tensorflow_hub as hub

# BƯỚC 1: Nạp model
YAMNET_MODEL_URL = "https://tfhub.dev/google/yamnet/1"
yamnet_model = hub.load(YAMNET_MODEL_URL)

print("YAMNet loaded successfully!")


# BƯỚC 2: Chuẩn bị audio để chạy inference
AUDIO_FILE = "engine/models/test_audio/sample.wav"

audio_binary = tf.io.read_file(AUDIO_FILE)

waveform, sample_rate = tf.audio.decode_wav(audio_binary)

waveform = tf.reduce_mean(waveform, axis=1)

print("Audio loaded successfully!")
print("Sample rate:", sample_rate.numpy())


# Chạy inference
scores, embeddings, spectrogram = yamnet_model(waveform)

print("Inference completed!")
print("Scores shape:", scores.shape)

# BƯỚC 3: Xử lý scores

# Lấy trung bình score của các frame
mean_scores = tf.reduce_mean(scores, axis=0)

# Tìm confidence cao nhất
top_confidence = tf.reduce_max(mean_scores)

# Tìm ID của class có confidence cao nhất
top_class_id = tf.argmax(mean_scores)

print("Top confidence:", top_confidence.numpy())
print("Top class ID:", top_class_id.numpy())

# BƯỚC 4: Ánh xạ ID sang tên nhãn

CLASS_MAP_FILE = "engine/models/yamnet_class_map.csv"

class_names = []

with open(CLASS_MAP_FILE, newline="", encoding="utf-8") as csvfile:
    reader = csv.DictReader(csvfile)

    for row in reader:
        class_names.append(row["display_name"])

top_label = class_names[top_class_id.numpy()]

print("Top label:", top_label)

# BƯỚC 5: Gom nhóm các nhãn cảnh báo

WARNING_LABELS = [
    "Vehicle horn, car horn, honking",
    "Siren",
    "Bicycle bell"
]

# Tìm ID của các nhãn cảnh báo
warning_ids = []

for label in WARNING_LABELS:
    if label in class_names:
        warning_ids.append(class_names.index(label))

# Lấy confidence của từng nhãn cảnh báo
warning_scores = []

for class_id in warning_ids:
    score = mean_scores[class_id]
    warning_scores.append(score)

print("Warning IDs:", warning_ids)
print("Warning scores:", [score.numpy() for score in warning_scores])

# Chọn nhãn cảnh báo có confidence cao nhất
best_warning_index = tf.argmax(warning_scores).numpy()

warning_class_id = warning_ids[best_warning_index]
warning_label = class_names[warning_class_id]
warning_confidence = warning_scores[best_warning_index].numpy()

print("Warning label:", warning_label)
print("Warning confidence:", warning_confidence)