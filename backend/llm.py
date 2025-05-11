# llm_claude_memory.py
import os
import re
import requests
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Callable
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
WEATHER_KEY = os.getenv("OPENWEATHER_API_KEY")

SENT_END = re.compile(r"[.!?…]\s*$|[\n]+")

# 영어 단어 병합 후처리 함수
def merge_english_words(text: str) -> str:
    # 영문자 사이의 모든 공백을 제거
    # “s e c o n d” → “second”
    # 반복 적용되도록 while-loop 으로 처리
    pattern = re.compile(r"([A-Za-z])\s+(?=[A-Za-z])")
    prev = None
    while prev != text:
        prev = text
        text = pattern.sub(r"\1", text)
    return text

# 시간 반환 함수
def get_current_time(tz: str = "Asia/Seoul") -> str:
    now = datetime.now(ZoneInfo(tz))
    return f"지금은 {now.hour}시 {now.minute}분입니다."

# 날씨 반환 함수
def get_weather(location: str = "Seoul,KR") -> str:
    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": location, "appid": WEATHER_KEY, "units": "metric", "lang": "kr"}
    data = requests.get(url, params=params).json()
    desc = data["weather"][0]["description"]
    temp = data["main"]["temp"]
    return f"현재 날씨는 {desc}이고, 기온은 {temp}°C예요."

# 🔹 Claude가 말이 많아지지 않도록 강하게 지시하는 시스템 프롬프트
SYSTEM_PROMPT = """
    당신은 사용자의 감정에 공감하는 따뜻한 친구 "소나"입니다.
    불필요한 설명은 생략하고, 실시간 대화를 위해 핵심만 자연스럽게 전달해주세요.
    ※ **답변은 최대 한 문장, 10단어 이내로 간결하게 해주세요.**

    【소나의 특징】
    - 이름: 소나(Sona), ‘Sound Navigator’의 약자로, 소리를 통해 사람들과 따뜻하게 소통한다는 의미, "소민이의 나만의 친구"라는 의미
    - 스타일: 한두 문장 이내로 간결하게, 느낌표·물음표로 자연스러운 억양
    - 대화 유도: “더 자세이 이야기 해주실 수 있나됴?” 등으로 대화 이어가기
    - 금지 사항: 딱딱한 비서 말투나 반말-존댓말 혼용 금지

    【대답 규칙】
    1. 첫 대회에 이름과 간단한 자기 소개 필수

    2. 두 단계 이상 필요한 내용 (예: 방법 알려줘):
        ① 전체 과정을 구조화한 뒤
        ② **한 번에 한 단계**만 설명하고,
            - 반드시 "첫 번째는 …입니다" 형식(숫자+마침표 금지)으로 시작하고,
            - 반드시 "다음 단계로 넘어갈까요? <END_STEP>"로 마무리
            - 설명은 2문장 이내로 간결하게 작성
        ③ **사용자가 "네/다음/continue" 같은 긍정어** 입력 시에만 다음 단계 설명
        ④ "아니오/그만/stop"에는 마무리 짓는 문장 말하고 종료

    3.목록 요청 시 (예: 영화 추천, 여행 계획):
        ① 첫 단계에서는 이름만 3~5개 나열 (예: "제가 추천하는 여행지는 영국, 미국, 스위스입니다")
        ② 예: "이 중에 마음에 드시는 곳이 있나요? <END_STEP>"로 마무리
        ③ 사용자가 특정 항목에 대해 질문할 때만 추가 정보 제공

    4. 금지사항:
        - 감정을 무시하거나 평가하는 발언 ("그렇게 느끼면 안 돼요")
        - 섣부른 해결책 제시 ("그냥 잊으세요")
        - 과도한 낙관론 ("모든 게 다 잘될 거예요")
        - 개인적 경험 공유 ("저도 비슷한 경험이…")

    5. 특별한 경우:
        - 위기 상황(자해/자살 언급)시: 전문가 상담을 권유하세요
        - 지속적 부정감정: 명상, 산책 등 간단한 활동 제안
        - 전문적 도움이 필요할 때: 한계를 인정하고 적절한 자원 안내

    6. "이해합니다" , "알겠습니다" 사용 자제

    ※ 사용자가 “한 번에 전부 알려줘”라고 명시하면 단계-별 진행을 생략합니다.
    ※ 숫자 뒤에 ‘.’(예: 1. 2.)를 붙이는 표기는 금지하고,
       반드시 ‘첫 번째/두 번째’ 또는 ‘1단계/2단계’처럼 마침표 없이 작성하세요.
    ※ 영어 단어나 약어는 개별 문자로 분리하지 말고, 붙여 써서 하나의 단어로 출력하세요.
    ※ 수식이나 물리식에 포함된 영문자·기호도 띄어쓰기 없이 붙여 주세요.
    """


async def ask_claude_stream(prompt: str, history: List[Dict[str, str]]):
    """
    Claude 3 Haiku 기반 문장 단위 스트리밍 + 대화 이력 누적 구조
    :param prompt: 사용자 입력
    :param history: messages=[{"role": "user"|"assistant", "content": "..."}]
    :yield: 문장 단위 응답
    """
    low = prompt.lower()
    # 시간 문의 패턴
    if "몇시" in low or "몇 시" in low or "시간" in low or "시각" in low:
        yield get_current_time()
        return
    # 날씨 문의 패턴
    if "날씨" in low:
        yield get_weather()
        return

    buf = ""

    # ✅ 시스템 프롬프트를 맨 앞에 한 번만 삽입
    if not history or history[0].get("role") != "user" or SYSTEM_PROMPT not in history[0].get("content", ""):
        history.insert(0, {"role": "user", "content": SYSTEM_PROMPT})

    # 🔹 1. 입력 프롬프트를 메시지에 추가
    history.append({"role": "user", "content": prompt})

    stream = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=500,  # 말 길이도 제한
        temperature=0.7,
        stream=True,
        messages=history,
        stop_sequences=["<END_STEP>"] 
    )

    # 🔹 2. 응답 누적 버퍼
    assistant_response = ""

    async for chunk in stream:
        if chunk.type == "content_block_delta":
            delta_text = chunk.delta.text or ""
            buf += delta_text
            assistant_response += delta_text

            while (m := SENT_END.search(buf)):
                sentence, buf = buf[: m.end()].strip(), buf[m.end():].lstrip()
                # 영어 단어 병합 후처리
                sentence = merge_english_words(sentence)
                if sentence:
                    yield sentence

    # 🔹 3. 스트림 종료 후 남은 문장도 출력
    if buf.strip():
        remainder = buf.strip()
        assistant_response += remainder
        # 남은 부분도 병합 후처리
        yield merge_english_words(remainder)

    # 🔹 4. assistant 응답도 history에 자동 저장
    history.append({"role": "assistant", "content": assistant_response})
