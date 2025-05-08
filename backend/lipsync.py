# ✅ 1단계: 텍스트 → 입모양 시퀀스 분석
# 이 함수는 TTS가 시작되기 전에 호출되어야 하며,
# 프론트엔드에서 립싱크 타이밍에 맞춰 ParamMouthForm을 제어할 수 있도록
# 일정 시간 간격으로 입모양(form)을 저장한 JSON 파일을 생성합니다.

def generate_mouthform_timings(text: str, step_ms: int = 200, output_path: str = "frontend/mouthForm.json"):
    import json
    import os

    # 입을 넓게 벌려야 하는 음소/모음들
    wide_phonemes = ["ㅣ", "ㅐ", "ㅔ", "ㅖ", "i", "e"]
    narrow_phonemes = ["ㅗ", "ㅜ", "ㅡ", "o", "u"]

    # 전체 음절을 시간 간격으로 나눔 (단순하게 음절 개수로 시간 분배)
    syllables = list(text)  # 기본은 문자 단위로 분할 (한글 음소 분리 X)

    mouth_seq = []
    for idx, ch in enumerate(syllables):
        t = round(idx * step_ms / 1000, 2)  # 초 단위로 변환
        form = 0.5  # 중립값 기본
        ch_lower = ch.lower()

        if any(p in ch for p in wide_phonemes):
            form = 1.0
        elif any(p in ch for p in narrow_phonemes):
            form = 0.0

        mouth_seq.append({"time": t, "form": form})

    # JSON으로 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mouth_seq, f, ensure_ascii=False, indent=2)

    print(f"✅ mouthform.json 저장 완료 ({len(mouth_seq)}개 프레임)")
