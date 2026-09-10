import wave
import math
import struct

sample_rate = 16000
duration = 2
frequency = 1000

with wave.open("engine/models/test_audio/sample.wav", "w") as wav_file:
    wav_file.setnchannels(1)       # mono
    wav_file.setsampwidth(2)      # 16-bit
    wav_file.setframerate(sample_rate)

    for i in range(sample_rate * duration):
        value = int(12000 * math.sin(2 * math.pi * frequency * i / sample_rate))
        wav_file.writeframes(struct.pack("<h", value))

print("sample.wav created!")