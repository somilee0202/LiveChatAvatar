import asyncio
import time
import os
import pyaudio
from pathlib import Path
from google.cloud.texttospeech_v1beta1.services.text_to_speech import TextToSpeechAsyncClient
from google.cloud.texttospeech_v1beta1.types import (
    StreamingSynthesizeRequest,
    StreamingSynthesizeConfig,
    StreamingSynthesisInput,
    StreamingAudioConfig,
    VoiceSelectionParams,
    AudioEncoding,
)

RATE = 24000

# ✅ BASE_DIR: 현재 tts.py 파일 기준 디렉토리
BASE_DIR = Path(__file__).resolve().parent

# ✅ credentials.json 경로를 절대경로로 지정하고 환경 변수 설정
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(CREDENTIALS_PATH)

# ✅ 출력 장치 자동 탐색 (macOS 포함, 다양한 이름 고려)
def find_output_device(target_keywords=("Speaker", "Output", "Built-in", "스피커")):
    pa = pyaudio.PyAudio()
    for i in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(i)
        name = info["name"]
        if any(k.lower() in name.lower() for k in target_keywords):
            print(f"🎧 출력 장치 선택됨: {i} - {name}")
            return i
    print("❌ 출력 장치를 찾지 못했습니다. 시스템 기본 장치 사용 시도")
    return None

DEFAULT_OUT = find_output_device()

class GoogleStreamTTS:
    def __init__(self,
                 language_code: str = "ko-KR",
                 voice_name: str = "ko-KR-Chirp3-HD-Aoede",
                 speaking_rate: float = 1.0):
        self.client = TextToSpeechAsyncClient()
        self.language_code = language_code
        self.voice_name    = voice_name
        self.speaking_rate = speaking_rate
        self.q: asyncio.Queue = asyncio.Queue()
        self._worker: asyncio.Task | None = None
        self.first_play_time: float | None = None
        self._first_play_recorded = False

    def reset_timing(self):
        self.first_play_time = None
        self._first_play_recorded = False

    def get_first_play_time(self):
        return self.first_play_time

    async def _worker_loop(self):
        pa = pyaudio.PyAudio()
        stream_out = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            output=True,
            output_device_index=DEFAULT_OUT  # ✅ 안전하게 선택된 장치 사용
        )
        try:
            while True:
                sentence = await self.q.get()
                if sentence is None:
                    self.q.task_done()
                    break

                try:
                    synth_cfg = StreamingSynthesizeConfig(
                        voice=VoiceSelectionParams(
                            language_code=self.language_code,
                            name=self.voice_name,
                        ),
                        streaming_audio_config=StreamingAudioConfig(
                            audio_encoding=AudioEncoding.PCM,
                            sample_rate_hertz=RATE,
                        ),
                    )

                    async def requests():
                        yield StreamingSynthesizeRequest(streaming_config=synth_cfg)
                        yield StreamingSynthesizeRequest(
                            input=StreamingSynthesisInput(text=sentence)
                        )

                    responses = await self.client.streaming_synthesize(
                        requests=requests()
                    )

                    async for resp in responses:
                        if not self._first_play_recorded and resp.audio_content:
                            self.first_play_time = time.time()
                            self._first_play_recorded = True
                        stream_out.write(resp.audio_content)

                except Exception as e:
                    print("🚨 Google Stream TTS 오류:", e)
                finally:
                    self.q.task_done()

        finally:
            stream_out.stop_stream()
            stream_out.close()
            pa.terminate()

    async def start(self):
        if not self._worker:
            self._worker = asyncio.create_task(self._worker_loop())

    async def enqueue(self, sentence: str):
        await self.q.put(sentence)

    async def finish(self):
        await self.q.put(None)
        await self.q.join()
        if self._worker:
            await self._worker
