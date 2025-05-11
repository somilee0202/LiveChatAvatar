import pyaudio
from google.cloud import speech
import queue
import time

# 마이크 설정
RATE = 16000
CHUNK = int(RATE / 10)
buff = queue.Queue()

last_audio_time = None  # 마지막 오디오가 들어온 시간 (말 끝났다고 가정)
final_transcript_time = None  # STT 최종 결과 도착 시점

def callback(in_data, frame_count, time_info, status):
    global last_audio_time
    buff.put(in_data)
    last_audio_time = time.time()  # 오디오가 들어올 때마다 최신 시간 갱신
    return None, pyaudio.paContinue

def stream_stt_until_final():
    global last_audio_time, final_transcript_time

    # 마이크 스트림 열기
    p = pyaudio.PyAudio()
    stream = p.open(
        format=pyaudio.paInt16,
        channels=1,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK,
        stream_callback=callback
    )

    client = speech.SpeechClient()

    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=RATE,
        language_code="ko-KR"
    )
    streaming_config = speech.StreamingRecognitionConfig(
        config=config,
        interim_results=True
    )

    def audio_generator():
        while True:
            data = [buff.get()]
            while not buff.empty():
                data.append(buff.get())
            yield b''.join(data)

    requests = (speech.StreamingRecognizeRequest(audio_content=chunk) for chunk in audio_generator())
    responses = client.streaming_recognize(streaming_config, requests)


    try:
        print("< 🎤 음성 인식 중... >")
        for response in responses:
            if not response.results:
                continue
            result = response.results[0]
            if not result.alternatives:
                continue
            transcript = result.alternatives[0].transcript.strip()
            
            if result.is_final:
                final_transcript_time = time.time()
                print(f"\n최종 인식: {transcript}\n")
                return transcript, final_transcript_time
            else:
                print(f"중간 인식: {transcript}", end="\r")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()