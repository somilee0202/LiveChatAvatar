# main.py – STT → LLM(스트림) → Google TTS(실시간) 통합 드라이버
import asyncio
import time
import csv
import os
from datetime import datetime
import json

from stt import stream_stt_until_final
# from llm_gpt import ask_gpt_stream
from llm import ask_claude_stream
from tts import GoogleStreamTTS
from lipsync import generate_mouthform_timings
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "credentials.json"
from dotenv import load_dotenv

load_dotenv()  # ✅ .env 파일 로드
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
#####
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import speech

try:
    client = speech.SpeechClient()
    # print("✅ Google STT 인증 성공")
except DefaultCredentialsError as e:
    # print(f"❌ 인증 실패: {e}")
    exit()

#########
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CSV_FILE = os.path.join(BASE_DIR, "latency.csv")
FIELDNAMES = ["timestamp", "question", "run", "stt_latency", "llm_latency", "tts_latency", "total_latency"]
chat_history = []

if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()

# BASE_DIR: backend/main.py에서 두 단계 위(프로젝트 루트)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")

with open(os.path.join(FRONTEND_DIR, "mouthForm.json"), "w", encoding="utf-8") as f:
    json.dump([], f)
with open(os.path.join(FRONTEND_DIR, "volume.json"), "w", encoding="utf-8") as f:
    json.dump({"volume": 0}, f)

def recognize_speech():
    transcript, start = stream_stt_until_final()
    end = time.time()
    latency = end - start
    print(f"🟡 STT 레이턴시: {latency:.2f}초")
    return transcript, start, latency

async def generate_response(prompt):
    start = time.time()
    full_response = ""
    first_token_time = None

    async for chunk in ask_claude_stream(prompt, chat_history):
        if first_token_time is None:
            first_token_time = time.time()
        full_response += chunk

    latency = first_token_time - start if first_token_time else 0
    print(f"🟢 LLM 레이턴시 (Claude): {latency:.2f}초")
    return full_response, latency

async def speak_response(text):
    # 1. 립싱크용 타이밍 json 미리 생성
    generate_mouthform_timings(text, output_path=os.path.join(FRONTEND_DIR, "mouthForm.json"))

    # 2. TTS 실행
    tts = GoogleStreamTTS()
    tts.reset_timing() 
    await tts.start()

    start = time.time()
    await tts.enqueue(text)
    await tts.finish()

    first_play = tts.get_first_play_time()
    if first_play is None:
        first_play = time.time()
    latency = first_play - start if first_play else 0
    print(f"🔵 TTS 레이턴시: {latency:.2f}초")
    return first_play, latency

async def main():
    run = 1
    print("🌟 실시간 아바타 대화 시스템 시작 🌟")

    # ✅ [1회성 예열] 고정 문장으로 LLM → TTS 실행
    transcript = "안녕" # 예열 문장
    total_start = time.time()
    
    response, llm_latency = await generate_response(transcript)
    total_end, tts_latency = await speak_response(response)

    # ✅ 실제 대화 루프 시작
    while True:
        transcript, total_start, stt_latency = recognize_speech()

        response, llm_latency = await generate_response(transcript)
        total_end, tts_latency = await speak_response(response)

        total_latency = total_end - total_start
        print(f"🔴 총 레이턴시: {total_latency:.2f}초\n")

        with open(CSV_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writerow({
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "question": transcript,
                "run": run,
                "stt_latency": round(stt_latency, 2),
                "llm_latency": round(llm_latency, 2),
                "tts_latency": round(tts_latency, 2),
                "total_latency": round(total_latency, 2),
            })

        run += 1


if __name__ == "__main__":
    asyncio.run(main())
