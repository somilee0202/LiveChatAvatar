from flask import Flask, jsonify, request, send_from_directory
import subprocess
import os
import signal
import time
import threading
import atexit
from backend.tts import GoogleStreamTTS
import asyncio
import logging

logging.getLogger('werkzeug').setLevel(logging.ERROR)
# 프로젝트 구조에 맞게 frontend 폴더 경로 설정
frontend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend')
app = Flask(__name__, static_folder=frontend_dir)

# 백엔드 프로세스를 추적하기 위한 전역 변수
backend_process = None
process_lock = threading.Lock()

@app.route('/')
def index():
    return send_from_directory(frontend_dir, 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory(frontend_dir, path)

@app.route('/start-backend', methods=['POST'])
def start_backend():
    global backend_process
    
    with process_lock:
        if backend_process is not None:
            return jsonify({"status": "already_running"}), 400
        
        try:
            # 백엔드 디렉토리 경로
            backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backend')
            backend_script = os.path.join(backend_dir, 'main.py')
            
            # 운영체제별 프로세스 그룹 설정
            if os.name == 'nt':  # Windows
                backend_process = subprocess.Popen(
                    ["python3", backend_script],
                    stdout=None,
                    stderr=None,
                    text=True,
                    cwd=backend_dir,  # 작업 디렉토리 설정
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP
                )
            else:  # Unix/Linux/Mac
                backend_process = subprocess.Popen(
                    ["python3", backend_script],
                    stdout=None,
                    stderr=None,
                    text=True,
                    cwd=backend_dir,  # 작업 디렉토리 설정
                    preexec_fn=os.setsid
                )
            
            # 시작이 성공했는지 확인하기 위해 잠시 기다림
            time.sleep(1)
            
            if backend_process.poll() is not None:
                # 프로세스가 이미 종료된 경우
                stdout, stderr = backend_process.communicate()
                print("백엔드 실행 실패 stderr:", stderr)
                backend_process = None
                return jsonify({
                    "status": "failed", 
                    "error": f"백엔드 실행 실패: {stderr}"
                }), 500
            
            return jsonify({"status": "started", "pid": backend_process.pid}), 200
            
        except Exception as e:
            if backend_process:
                backend_process = None
            print(f"백엔드 시작 오류: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

def play_exit_tts():
    async def _play():
        tts = GoogleStreamTTS()
        await tts.start()
        await tts.enqueue("대화를 종료하겠습니다. 언제든 제가 필요하시면 다시 찾아주세요. 좋은 하루 보내세요!")
        await tts.finish()
    asyncio.run(_play())

@app.route('/stop-backend', methods=['POST'])
def stop_backend():
    global backend_process
    
    with process_lock:
        if backend_process is None:
            return jsonify({"status": "not_running"}), 400
        
        try:
            # 1. 프로세스 종료
            pid = backend_process.pid
            # 운영체제별 처리
            if os.name == 'nt':  # Windows
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
            else:  # Unix/Linux/Mac
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                    # 기본 종료가 안되면 강제 종료
                    if backend_process.poll() is None:
                        os.killpg(os.getpgid(pid), signal.SIGKILL)
                except ProcessLookupError:
                    pass  # 프로세스가 이미 종료된 경우
            backend_process = None
            # 2. 종료 멘트 TTS 재생
            play_exit_tts()
            return jsonify({"status": "stopped"}), 200
        except Exception as e:
            print(f"백엔드 종료 오류: {str(e)}")
            return jsonify({"status": "error", "message": str(e)}), 500

def cleanup_process():
    """애플리케이션 종료 시 백엔드 프로세스 정리"""
    global backend_process
    if backend_process is not None:
        try:
            pid = backend_process.pid
            if os.name == 'nt':  # Windows
                subprocess.call(['taskkill', '/F', '/T', '/PID', str(pid)])
            else:  # Unix/Linux/Mac
                try:
                    os.killpg(os.getpgid(pid), signal.SIGTERM)
                except ProcessLookupError:
                    pass  # 프로세스가 이미 종료된 경우
        except:
            pass

# 애플리케이션 종료 시 프로세스 정리 함수 등록
atexit.register(cleanup_process)

if __name__ == '__main__':
    print(f"Frontend 디렉토리: {frontend_dir}")
    print("서버 시작 중... http://localhost:8000 에서 접속하세요.")
    app.run(host='0.0.0.0', port=8000, debug=False)