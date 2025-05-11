# 실시간 음성 대화 시스템

이 프로젝트는 Google Cloud의 STT/TTS와 Anthropic의 Claude를 활용한 실시간 음성 대화 시스템입니다.

## 주요 기능
- 실시간 음성 인식(STT) → LLM(Claude) → 음성 합성(TTS) → Live2D 립싱크 연동
- 웹 프론트엔드에서 실시간 대화 및 아바타 립싱크 시각화
- 대화 레이턴시 기록, 종료 멘트 TTS 등 다양한 부가 기능

## 프로젝트 구조

- backend/: 파이썬 백엔드 코드(main.py, tts.py, stt.py, llm.py, lipsync.py 등)
- frontend/: 웹 프론트엔드(index.html, Live2D 리소스 등)
- server.py: Flask 웹서버 및 백엔드 프로세스 관리
- requirements.txt: 의존 패키지 목록
- .env: 환경 변수 파일

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
  GOOGLE_APPLICATION_CREDENTIALS=path/to/your/google-credentials.json
  ANTHROPIC_API_KEY=your-anthropic-api-key
  OPENWEATHER_API_KEY=your-openweather-api-key
  ```
- Google Cloud 서비스 계정 키 파일을 다운로드하여 지정된 경로에 저장

## 실행 방법

1. 가상환경이 활성화된 상태에서:
```bash
python server.py
```
2. 웹 브라우저에서 [http://localhost:8000](http://localhost:8000) 접속
3. "대화 시작" 버튼을 눌러 대화를 시작하고, "대화 종료" 버튼으로 종료

## 주의사항

- Google Cloud 프로젝트에서 Speech-to-Text와 Text-to-Speech API가 활성화되어 있어야 합니다.
- 마이크와 스피커가 정상적으로 연결되어 있어야 합니다.
- 인터넷 연결이 필요합니다. 