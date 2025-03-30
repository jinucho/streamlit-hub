# Python 3.11 이미지를 기반으로 함
FROM python:3.11-slim

# 작업 디렉토리 설정
WORKDIR /app

# 필요한 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    ffmpeg \
    cron \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# 현재 디렉토리의 파일들을 컨테이너의 /app 디렉토리로 복사
COPY . /app

# Python 패키지 설치
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# 환경 변수 설정
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH="${PYTHONPATH}:/app"

# crontab 설정
RUN crontab /app/crontab

# 로그 디렉토리 생성
RUN mkdir -p /app/logs

# 8501 포트 노출 (Streamlit 기본 포트)
EXPOSE 8501

# crontab 설정
COPY crontab /etc/cron.d/app-cron
RUN chmod 0644 /etc/cron.d/app-cron && \
    crontab /etc/cron.d/app-cron && \
    echo "PATH=/usr/local/bin:$PATH" >> /etc/environment