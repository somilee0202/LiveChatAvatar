# 실시간 음성 대화 시스템

이 프로젝트는 Google Cloud의 STT/TTS와 Anthropic의 Claude를 활용한 실시간 음성 대화 시스템입니다.

## 사전 요구사항

1. Python 3.8 이상
2. Google Cloud 계정 및 프로젝트
3. Anthropic API 키
4. 마이크와 스피커

## 설치 방법

1. 가상환경 생성 및 활성화:
```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate
```

2. 필요한 패키지 설치:
```bash
pip install -r requirements.txt
```

3. 환경 변수 설정:
- `.env` 파일을 생성하고 다음 내용을 입력:
  ```
  GOOGLE_APPLICATION_CREDENTIALS="path/to/your/google-credentials.json"
  ANTHROPIC_API_KEY="your-anthropic-api-key"
  ```
- Google Cloud 서비스 계정 키 파일을 다운로드하여 지정된 경로에 저장

## 실행 방법

1. 가상환경이 활성화된 상태에서:
```bash
python main.py
```

2. 프로그램이 시작되면 마이크에 대고 말씀하세요.
3. '그만'이라고 말하면 프로그램이 종료됩니다.

## 주의사항

- Google Cloud 프로젝트에서 Speech-to-Text와 Text-to-Speech API가 활성화되어 있어야 합니다.
- 마이크와 스피커가 정상적으로 연결되어 있어야 합니다.
- 인터넷 연결이 필요합니다. 