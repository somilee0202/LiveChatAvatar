import asyncio
import time
import pyaudio
from google.cloud.texttospeech_v1beta1.services.text_to_speech import (
    TextToSpeechAsyncClient
)
from google.cloud.texttospeech_v1beta1.types import (
    StreamingSynthesizeRequest,
    StreamingSynthesizeConfig,
    StreamingSynthesisInput,
    StreamingAudioConfig,
    VoiceSelectionParams,
    AudioEncoding,
)

RATE = 24000
DEFAULT_OUT = next(
    i for i in range(pyaudio.PyAudio().get_device_count())
    if "스피커" in pyaudio.PyAudio().get_device_info_by_index(i)["name"]
)

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

        # 🔹 음성 재생 시점 기록용
        self.first_play_time: float | None = None
        self._first_play_recorded = False

    def reset_timing(self):
        """TTS 타이밍 초기화 (매 대화마다 호출 필요)"""
        self.first_play_time = None
        self._first_play_recorded = False

    from typing import Optional

    def get_first_play_time(self) -> Optional[float]:
        """첫 음성 재생 시각 반환"""
        return self.first_play_time

    async def _worker_loop(self):
        pa = pyaudio.PyAudio()
        stream_out = pa.open(
            format=pyaudio.paInt16,
            channels=1,
            rate=RATE,
            output=True,
            output_device_index=DEFAULT_OUT
        )
        try:
            while True:
                sentence = await self.q.get()

                # sentinel 처리
                if sentence is None:
                    self.q.task_done()
                    break

                try:
                    # 1) 스트리밍 설정 메시지 구성
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

                    # 2) 요청 제너레이터: 첫 메시지엔 config, 그 뒤엔 input만
                    async def requests():
                        yield StreamingSynthesizeRequest(streaming_config=synth_cfg)
                        yield StreamingSynthesizeRequest(
                            input=StreamingSynthesisInput(text=sentence)
                        )

                    # 3) streaming_synthesize 호출
                    responses = await self.client.streaming_synthesize(
                        requests=requests()
                    )

                    # 4) 응답 스트림을 곧바로 재생하며, 첫 음성 시각 기록
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
