import io
import json
import os
import re
import smtplib
import time
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
import streamlit as st
from dotenv import load_dotenv

load_dotenv()
kst = timezone(timedelta(hours=9))

# RunPod 정보
RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
HEADERS = {
    "Authorization": f"Bearer {RUNPOD_API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

# 관리자 인증 정보
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "password")

# 공지사항 파일 경로 설정 (Cloudinary 대신 로컬 파일 시스템 사용)
NOTICE_FILE_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "notices.json")

# 디렉토리가 없으면 생성
os.makedirs(os.path.dirname(NOTICE_FILE_PATH), exist_ok=True)


def get_video_id(url):
    # 정규식을 통해 다양한 유튜브 링크에서 ID 추출
    match = re.search(
        r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|v/|.+\?v=))([^&=%\?]{11})", url
    )
    return match.group(1) if match else None


def get_current_time():
    return datetime.now(kst).strftime("%H:%M")


def check_runpod_status(payload, RUNPOD_ENDPOINT_ID, interval=5):
    """
    RunPod 상태를 지속적으로 확인하여 'COMPLETED' 상태일 때 데이터를 반환.
    :param runpod_url: RunPod API 호출 URL
    :param headers: HTTP 요청 헤더
    :param payload: 요청에 필요한 데이터
    :param interval: 상태 확인 주기 (초)
    :return: 작업이 완료되면 결과 데이터 반환
    """
    RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/runsync"
    response = requests.post(RUNPOD_API_URL, headers=HEADERS, json=payload)
    if response.status_code == 200:
        result = response.json()
        if result.get("status") in ["IN_PROGRESS", "IN_QUEUE"]:
            job_id = result.get("id")
            status_url = (
                f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}/status/{job_id}"
            )

            while True:
                status_response = requests.get(status_url, headers=HEADERS)
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    if status_data.get("status") == "COMPLETED":
                        return status_data
                    else:
                        continue

                time.sleep(interval)  # 지정된 간격 후 다시 상태 확인
        elif result.get("status") == "COMPLETED":
            return result
        else:
            return response.json()


def send_feedback_email(feedback, session_id):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")
    receiver_email = os.getenv("SENDER_EMAIL")

    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = receiver_email
    message["Subject"] = f"새로운 사용자 피드백 (세션 ID: {session_id[:8]})"

    current_time = datetime.now(kst).strftime("%Y-%m-%d %H:%M:%S")
    body = f"피드백 시간: {current_time}\n"
    body += f"세션 ID: {session_id}\n\n"
    body += f"피드백 내용:\n{feedback}"

    message.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        return True
    except Exception as e:
        print(f"이메일 전송 중 오류 발생: {e}")
        return False


def create_downloadable_file(session_state):
    # 텍스트 파일로 저장할 내용 구성
    title = f"제목: {session_state.title}"
    hashtags = f"해시태그: {session_state.hashtags}"
    joined_summary = "\n".join(session_state.summary)
    summary = f"\n[요약]\n{joined_summary}"

    # 스크립트를 텍스트로 변환
    transcript = "[스크립트]\n" + "\n".join(
        [
            f"{item['start']}초 - {item['end']}초: {item['text']}"
            for item in session_state.transcript
        ]
    )

    # 채팅 내역을 텍스트로 변환
    chat_history = "[채팅 내역]\n" + "\n".join(
        [
            f"{message['role']}: {message['content']}"
            for message in session_state.messages
        ]
    )

    # 모든 내용을 하나의 문자열로 결합
    data = f"{title}\n{hashtags}\n\n{summary}\n\n{transcript}\n\n{chat_history}"

    # 텍스트 파일을 바이트 형식으로 변환
    file_buffer = io.BytesIO()
    file_buffer.write(data.encode("utf-8"))
    file_buffer.seek(0)  # 파일 시작 위치로 포인터 이동
    return file_buffer


# 관리자 인증 함수
def verify_admin(username, password):
    """
    관리자 인증을 수행하는 함수

    Args:
        username (str): 사용자 이름
        password (str): 비밀번호

    Returns:
        bool: 인증 성공 여부
    """
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


# 공지사항 저장 함수 - 로컬 파일 시스템 사용
def save_notices(notices):
    """공지사항을 로컬 JSON 파일로 저장"""
    try:
        # JSON 데이터를 파일로 저장
        with open(NOTICE_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(notices, f, ensure_ascii=False, indent=4)
        return True
    except Exception as e:
        print(f"[ERROR] 공지사항 저장 실패: {e}")
        return False


# 공지사항 불러오기 함수 - 로컬 파일 시스템 사용
def load_notices():
    """로컬 파일 시스템에서 공지사항 JSON 파일을 불러오기"""
    try:
        # 파일이 없으면 빈 공지사항 생성
        if not os.path.exists(NOTICE_FILE_PATH):
            return create_empty_notices()
            
        # 파일에서 JSON 데이터 불러오기
        with open(NOTICE_FILE_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # 데이터 변환 (문자열 리스트 -> 딕셔너리 리스트)
        if isinstance(data, list) and all(isinstance(item, str) for item in data):
            data = [
                {"date": item.split(": ")[0], "content": item.split(": ")[1]}
                for item in data
                if ": " in item
            ]
            
        return data
    except Exception as e:
        print(f"[ERROR] 공지사항 불러오기 실패: {e}")
        return []


# 빈 공지사항 생성 함수 - 로컬 파일 시스템 사용
def create_empty_notices():
    """
    빈 공지사항 파일을 생성하고 로컬에 저장합니다.

    Returns:
        list: 빈 공지사항 목록
    """
    try:
        print("빈 공지사항 파일을 생성합니다.")
        empty_notices = []
        save_notices(empty_notices)
        return empty_notices
    except Exception as e:
        print(f"빈 공지사항 파일 생성 중 오류 발생: {str(e)}")
        return []


# 공지사항 추가 함수 - 로컬 파일 시스템 사용
def add_notice(new_notice):
    """새로운 공지사항 추가 후 로컬에 저장"""
    notices = load_notices()
    notices.append(new_notice)
    return save_notices(notices)


# 공지사항 삭제 함수 - 로컬 파일 시스템 사용
def delete_notice(index):
    """공지사항 삭제 후 로컬에 저장"""
    notices = load_notices()
    if 0 <= index < len(notices):
        del notices[index]
    return save_notices(notices)


# 공지사항 수정 함수 - 로컬 파일 시스템 사용
def update_notice(index, updated_notice):
    """공지사항 수정 후 로컬에 저장"""
    notices = load_notices()
    if 0 <= index < len(notices):
        notices[index] = updated_notice
    return save_notices(notices)