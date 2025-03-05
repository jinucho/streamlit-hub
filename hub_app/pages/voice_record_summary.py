import streamlit as st
import tempfile
import os
import time
import numpy as np
import soundfile as sf
import torch
import librosa  # 추가: 다양한 오디오 형식 지원
import google.generativeai as genai  # 추가: Google Gemini AI
import requests
import base64
from dotenv import load_dotenv
import sys
import json

# 유틸리티 함수 임포트
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import check_runpod_status, HEADERS

load_dotenv()

# RunPod 정보
RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID_WHISPER")  # Whisper 엔드포인트 ID

# 전역 처리 상태 관리를 위한 세션 상태 초기화
if "processing" not in st.session_state:
    st.session_state.processing = False
if "process_id" not in st.session_state:
    st.session_state.process_id = None
if "full_text" not in st.session_state:
    st.session_state.full_text = ""
if "pure_text" not in st.session_state:
    st.session_state.pure_text = ""
if "segments_list" not in st.session_state:
    st.session_state.segments_list = []
if "meeting_minutes" not in st.session_state:
    st.session_state.meeting_minutes = ""
if "transcription_done" not in st.session_state:
    st.session_state.transcription_done = False
if "generate_minutes" not in st.session_state:
    st.session_state.generate_minutes = False


# Gemini AI 모델 초기화 함수
@st.cache_resource
def load_gemini_model(api_key):
    """Gemini 모델을 초기화하는 함수"""
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    return model


# 회의록 생성 함수
def generate_meeting_minutes(text, model):
    """Gemini AI를 사용하여 회의록을 생성하는 함수"""

    prompt = f"""
    다음은 회의 녹취록입니다. 이 내용을 바탕으로 전문적인 회의록을 작성해주세요.
    회의록에는 다음 내용이 포함되어야 합니다:
    1. 회의 주요 주제
    2. 논의된 중요 사항
    3. 결정된 사항
    4. 향후 조치 사항
    5. 요약 및 결론
    6. 주요 용어 및 정의

    녹취록:
    {text}
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        st.error(f"Gemini API 호출 중 오류: {str(e)}")
        return f"회의록 생성 중 오류가 발생했습니다: {str(e)}"


# 페이지 설정
st.set_page_config(page_title="음성 텍스트 변환 서비스", page_icon="🎙️", layout="wide")

# 제목 및 설명
st.title("🎙️ 음성 텍스트 변환 서비스")

# 사이드바 설정
with st.sidebar:
    model_size = "large-v3"  # RunPod에서 사용할 모델 크기
    language = st.selectbox(
        "언어 선택",
        ["자동감지", "ko", "en", "ja"],
        index=1,
    )

    if language == "자동감지":
        language = None

    # Google API 키 입력
    api_key = os.getenv("GOOGLE_API_KEY")
    if api_key:
        try:
            gemini_model = load_gemini_model(api_key)
        except Exception as e:
            st.error(f"Gemini API 연결 실패: {str(e)}")
            api_key = None  # 연결 실패 시 키를 None으로 설정
    else:
        st.warning(
            "Google Gemini API 키가 설정되지 않았습니다. .env 파일에 GOOGLE_API_KEY를 추가해주세요."
        )

    # RunPod API 키 확인
    if not RUNPOD_ENDPOINT_ID:
        st.warning(
            "RunPod API 키 또는 엔드포인트 ID가 설정되지 않았습니다. .env 파일에 RUNPOD_API_KEY와 RUNPOD_WHISPER_ENDPOINT_ID를 추가해주세요."
        )

    st.markdown("---")
    st.write("사용 방법")
    st.markdown(
        """
    1. 음성 파일(.mp3, .wav, .m4a, .ogg)을 업로드합니다.
    2. 업로드가 완료되면 "음성 변환 시작" 버튼을 클릭합니다.
    3. 변환된 텍스트를 확인하고 필요시 다운로드합니다.
    4. 하단의 "회의록 생성" 버튼을 클릭하여 AI 회의록을 생성합니다.
    
    **참고사항:**
    - 언어를 선택하면 해당 언어로 인식 정확도가 높아집니다.
    - 회의에 다양한 언어가 포함 됐을 경우 언어를 선택하지 않고 자동 감지를 선택하세요.
    """
    )


# 메인 영역
uploaded_file = st.file_uploader(
    "음성 파일 업로드 (.mp3, .wav, .m4a, .ogg)", type=["mp3", "wav", "m4a", "ogg"]
)

# 파일이 업로드되면 세션 상태 초기화
if uploaded_file is not None and "current_file" not in st.session_state:
    st.session_state.current_file = uploaded_file.name
    st.session_state.transcription_done = False
    st.session_state.meeting_minutes = ""
elif (
    uploaded_file is not None
    and st.session_state.get("current_file") != uploaded_file.name
):
    # 새 파일이 업로드되면 상태 초기화
    st.session_state.current_file = uploaded_file.name
    st.session_state.transcription_done = False
    st.session_state.meeting_minutes = ""

# 다른 사용자가 처리 중인지 확인
if st.session_state.processing and st.session_state.process_id != id(st.session_state):
    st.warning(
        "⚠️ 현재 다른 사용자가 음성 변환을 처리 중입니다. 잠시 후 다시 시도해주세요."
    )

if uploaded_file is not None:
    # 임시 파일로 저장
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=os.path.splitext(uploaded_file.name)[1]
    ) as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    st.audio(
        uploaded_file, format=f"audio/{os.path.splitext(uploaded_file.name)[1][1:]}"
    )

    # 변환 시작 버튼 추가
    if not st.session_state.transcription_done:
        if st.button("음성 변환 시작") and not (
            st.session_state.processing
            and st.session_state.process_id != id(st.session_state)
        ):
            # 처리 상태 설정
            st.session_state.processing = True
            st.session_state.process_id = id(st.session_state)

            with st.spinner("음성 변환 중..."):
                # 오디오 파일 로드 및 정보 표시
                try:
                    # librosa를 사용하여 다양한 오디오 형식 지원
                    audio_data, sample_rate = librosa.load(tmp_file_path, sr=None)
                    duration = librosa.get_duration(y=audio_data, sr=sample_rate)
                    st.info(
                        f"오디오 길이: {duration:.2f}초, 샘플레이트: {sample_rate}Hz"
                    )
                except Exception as e:
                    st.error(f"오디오 파일 로드 중 오류 발생: {str(e)}")
                    os.unlink(tmp_file_path)
                    # 처리 상태 해제
                    st.session_state.processing = False
                    st.stop()

                # 텍스트 추출 시작
                start_time = time.time()
                try:
                    # 파일을 base64로 인코딩
                    with open(tmp_file_path, "rb") as audio_file:
                        audio_bytes = audio_file.read()
                        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

                    # RunPod API 요청 페이로드 구성
                    payload = {
                        "input": {
                            "audio": {"data": audio_base64, "type": "base64"},
                            "model": "large-v3",
                            "batch_size": 24,
                            "chunk_length": 30,
                            "task": "transcribe",
                            "language": language if language else None,
                        }
                    }

                    # RunPod API 호출
                    result = check_runpod_status(payload, RUNPOD_ENDPOINT_ID)

                    if result and "output" in result:
                        output = result["output"]

                        # 결과 처리
                        segments_list = output.get("segments", [])
                        st.session_state.segments_list = segments_list

                        # 전체 텍스트 구성
                        full_text = ""
                        for segment in segments_list:
                            full_text += f"{segment['start']}s - {segment['end']}s: {segment['text']}\n"
                        st.session_state.full_text = full_text

                        # 회의록 생성용 순수 텍스트 추출
                        pure_text = " ".join(
                            [segment["text"] for segment in segments_list]
                        )
                        st.session_state.pure_text = pure_text

                        # 변환 완료 상태 설정
                        st.session_state.transcription_done = True
                    else:
                        st.error("RunPod API에서 유효한 응답을 받지 못했습니다.")

                except Exception as e:
                    st.error(f"변환 중 오류 발생: {str(e)}")
                    os.unlink(tmp_file_path)
                    # 처리 상태 해제
                    st.session_state.processing = False
                    st.stop()

                # 처리 시간 계산
                process_time = time.time() - start_time

                # 결과 표시
                st.success(
                    f"변환 완료! 처리 시간: {process_time:.2f}초 (처리 속도: {duration/process_time:.2f}x)"
                )

                # 처리 상태 해제
                st.session_state.processing = False

                # 페이지 새로고침
                st.rerun()

    # 변환이 완료된 경우 결과 표시
    if st.session_state.transcription_done:
        st.subheader("결과")
        # 텍스트 다운로드 버튼
        st.download_button(
            label="텍스트 파일 다운로드",
            data=st.session_state.full_text,
            file_name=f"{os.path.splitext(uploaded_file.name)[0]}_transcript.txt",
            mime="text/plain",
        )

        # 세그먼트별 텍스트 표시 - 컨테이너로 감싸기
        with st.container():
            st.subheader("시간별 텍스트")

            # 접을 수 있는 expander로 추가 옵션 제공 (선택사항)
            with st.expander("시간별 텍스트 보기", expanded=False):
                # 세그먼트 데이터를 표 형식으로 표시
                segment_data = []
                for i, segment in enumerate(st.session_state.segments_list):
                    segment_data.append(
                        {
                            "번호": i + 1,
                            "시작 시간": f"{segment['start']:.2f}s",
                            "종료 시간": f"{segment['end']:.2f}s",
                            "텍스트": segment["text"],
                            "신뢰도": (
                                f"{segment.get('confidence', 0) * 100:.1f}%"
                                if "confidence" in segment
                                else "N/A"
                            ),
                        }
                    )

                st.dataframe(segment_data, use_container_width=True)

        # 구분선 추가로 섹션 분리
        st.markdown("---")

        # 회의록 생성 버튼 추가
        with st.container():
            st.subheader("AI 회의록 생성")

            # 회의록 생성 버튼 (세션 상태를 사용하여 상태 유지)
            if api_key:
                if st.button("회의록 생성") or st.session_state.generate_minutes:
                    if (
                        not st.session_state.meeting_minutes
                    ):  # 회의록이 아직 생성되지 않은 경우에만 실행
                        st.session_state.generate_minutes = True
                        with st.spinner("AI가 회의록을 작성 중입니다..."):
                            try:
                                meeting_minutes = generate_meeting_minutes(
                                    st.session_state.pure_text, gemini_model
                                )
                                st.session_state.meeting_minutes = meeting_minutes
                                st.session_state.generate_minutes = (
                                    False  # 생성 완료 후 상태 업데이트
                                )
                                st.success("회의록 생성 완료!")
                                st.rerun()  # 페이지 새로고침
                            except Exception as e:
                                st.error(f"회의록 생성 중 오류 발생: {str(e)}")
                                st.error("상세 오류 정보: " + str(e.__class__.__name__))
                                st.session_state.generate_minutes = False
            else:
                st.warning(
                    "회의록 생성을 위한 Google Gemini API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."
                )

            # 회의록이 생성되었으면 표시
            if st.session_state.meeting_minutes:
                with st.container():
                    st.markdown("### AI 회의록")
                    st.markdown(st.session_state.meeting_minutes)

                    # 회의록 다운로드 버튼
                    st.download_button(
                        label="회의록 다운로드",
                        data=st.session_state.meeting_minutes,
                        file_name=f"{os.path.splitext(uploaded_file.name)[0]}_meeting_minutes.txt",
                        mime="text/plain",
                    )
    else:
        st.info(
            "파일이 업로드되었습니다. '음성 변환 시작' 버튼을 클릭하여 변환을 시작하세요."
        )

    # 임시 파일 삭제
    os.unlink(tmp_file_path)
else:
    st.info("위에서 음성 파일을 업로드해주세요.")
