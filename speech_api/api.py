import pyaudio
import audioop
import wave
import time
from openai import OpenAI

client = OpenAI()

def record_wav(output_filename = "output.wav"):
    # 设置音频参数
    chunk = 1024
    format = pyaudio.paInt16
    channels = 1
    rate = 44100
    threshold = 500  # 音量阈值
    over_threshold = False  # 标记是否开始录音
    over_time = time.time() + 1  # 录音时间
    wait_interval = 1  # 等待时间
    

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

def speech_recognition(filename = "output.mp3"):
    audio_file = open(filename, "rb")
    transcript = client.audio.transcriptions.create(
    model="whisper-1", 
    file=audio_file, 
    response_format="text"
    )
    return transcript

def text_to_speech(text, output_filename = "output.mp3"):
    speech_file_path = output_filename
    response = client.audio.speech.create(
    model="tts-1",
    voice="alloy",
    input=text
    )

    response.stream_to_file(speech_file_path)