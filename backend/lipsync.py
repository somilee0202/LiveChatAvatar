from jamo import hangul_to_jamo, j2hcj  # ✅ j2hcj: 자모를 호환 자모(단순 문자)로 변환
import json
import os

def generate_mouthform_timings(text: str, step_ms: int = 200, output_path: str = "frontend/mouthForm.json"):
    wide_phonemes = ["ㅣ", "ㅐ", "ㅔ", "ㅖ", "ㅒ", "ㅑ", "ㅕ"]
    narrow_phonemes = ["ㅗ", "ㅜ", "ㅡ", "ㅓ", "ㅏ"]

    mouth_seq = []
    syllables = list(text)

    for idx, ch in enumerate(syllables):
        # ✅ 조합 자모 → 호환 자모로 변환
        jamos = j2hcj(hangul_to_jamo(ch))  # e.g., '안' → ['ㅇ', 'ㅏ', 'ㄴ']

        form = 0.5  # 기본값
        for j in jamos:
            if j in wide_phonemes:
                form = 1.0
                break
            elif j in narrow_phonemes:
                form = 0.0
                break

        t = round(idx * step_ms / 1000, 2)
        mouth_seq.append({"time": t, "form": form})

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mouth_seq, f, ensure_ascii=False, indent=2)

    print(f"✅ mouthForm.json 저장 완료 ({len(mouth_seq)}개 프레임)")

# ✅ 테스트 실행
if __name__ == "__main__":
    generate_mouthform_timings("오이 아이유 에이 아이 오이야")
