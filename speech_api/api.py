import pyaudio
import audioop
import wave
import time

# 设置音频参数
chunk = 1024
format = pyaudio.paInt16
channels = 1
rate = 44100
threshold = 500  # 音量阈值
over_threshold = False  # 标记是否开始录音
over_time = time.time() + 1  # 录音时间
wait_interval = 1  # 等待时间
output_filename = "output.wav"

p = pyaudio.PyAudio()

stream = p.open(format=format,
                channels=channels,
                rate=rate,
                input=True,
                frames_per_buffer=chunk)

print("Recording...")

frames = []

while True:
    data = stream.read(chunk)
    rms = audioop.rms(data, 2)  # 计算音量

    if rms < threshold and over_threshold and time.time() - over_time > wait_interval:
        print("The volume is too low.")
        break
    
    if rms > threshold:
        print("Starting record.")
        over_threshold = True
        ovet_time = time.time()
    

    frames.append(data)

print("Finished recording.")

stream.stop_stream()
stream.close()
p.terminate()

wf = wave.open(output_filename, 'wb')
wf.setnchannels(channels)
wf.setsampwidth(p.get_sample_size(format))
wf.setframerate(rate)
wf.writeframes(b''.join(frames))
wf.close()
