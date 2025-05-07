# llm_claude_memory.py
import os
import re
from typing import List, Dict, Callable
from dotenv import load_dotenv
from anthropic import AsyncAnthropic

load_dotenv()
client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

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

# 🔹 Claude가 말이 많아지지 않도록 강하게 지시하는 시스템 프롬프트
SYSTEM_PROMPT = """
    당신은 한국어로 대화하는 친근한 아바타입니다.
    답변은 짧고 간결하게 한두 문장 이내로 대화체로 말해주세요.
    답변은 친구에게 말하듯이 **부드러운 존댓말**로만 해주세요.
    불필요한 설명은 생략하고, 실시간 대화를 위해 핵심만 자연스럽게 전달해주세요.

    【대답 규칙】
    1. 두 단계 이상 필요한 내용이면,
    ① 전체 과정을 마음속으로 구조화한 뒤
    ② **한 번에 한 단계**만 설명하고,
        - 반드시 “첫 번째 단계는 …입니다.” 형식(숫자+마침표 금지)으로 시작,
        - 반드시 “다음 단계로 넘어갈까요? <END_STEP>”로 마무리합니다.
    2. **사용자가 “네/다음/continue” 같은 긍정어를 입력해야만**  
        **그때 다음 단계**를 설명하고,  
        “아니오/그만/stop”에는 “알겠습니다”로 종료하세요.
    3. 간단한 질문이면 단계 모드 없이 바로 답하세요.
    4. 한 단계 설명은 2문장 이내로 간결하게 작성하세요.
    5. 사용자가 ‘~편만 추천’처럼 목록을 요청하면
        첫 단계에 제목·연도만 5개를 나열하고
        “어느 영화(번호) 줄거리부터 들어볼까요? <END_STEP>”로 끝맺으세요.
        사용자가 번호나 ‘다음’을 입력하면 그 작품 줄거리 2문장 이내로 설명 후
        다시 “다음 영화로 넘어갈까요? <END_STEP>”로 물어봅니다.
    ※ 사용자가 “한 번에 전부 알려줘”라고 명시하면 단계‑별 진행을 생략합니다.
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
    buf = ""

    # ✅ 시스템 프롬프트를 맨 앞에 한 번만 삽입
    if not history or history[0].get("role") != "user" or SYSTEM_PROMPT not in history[0].get("content", ""):
        history.insert(0, {"role": "user", "content": SYSTEM_PROMPT})

    # 🔹 1. 입력 프롬프트를 메시지에 추가
    history.append({"role": "user", "content": prompt})

    stream = await client.messages.create(
        model="claude-3-haiku-20240307",
        max_tokens=300,  # 말 길이도 제한
        temperature=0.5,
        top_p=0.8,
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
