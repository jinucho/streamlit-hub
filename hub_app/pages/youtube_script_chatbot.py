import time
import uuid

import streamlit as st

from utils import (
    check_runpod_status,
    create_downloadable_file,
    get_current_time,
    get_video_id,
    send_feedback_email,
)

import os
from dotenv import load_dotenv

load_dotenv()

# 홈 페이지 링크
with st.sidebar:
    st.markdown("### 📌 NAVIGATION")
    st.page_link("home.py", label="홈", icon="🏠")
    st.page_link(
        "pages/youtube_script_chatbot.py",
        label="유튜브 스크립트 추출 및 요약과 AI 채팅",
        icon="📺",
    )
    st.page_link("pages/voice_record_summary.py", label="음성 녹음 요약", icon="🎤")
    st.markdown("---")
    st.write("사용 방법")
    st.markdown(
        """
    1. 유튜브 영상의 URL을 입력합니다.
    2. 사용하고자 하는 모델을 선택 합니다.
    3. 스크립트 추출을 클릭 합니다.
    4. 영상에 대한 요약 및 전체 스크립트가 제공되고, 채팅 창에서 질문을 입력 할 수 있습니다.
    """
    )
# Streamlit 웹 애플리케이션 설정
st.title("유튜브 스크립트 추출 및 요약과 AI 채팅")

col1, col2 = st.columns(2)
with col1:
    st.write(
        "영상의 주소를 입력 후 스크립트를 추출하면 영상 내용 요약 및 전체 스크립트가 추출됩니다."
    )
    st.write("스크립트 내용에 기반하여 AI에게 질문 할 수 있습니다.")
with col2:
    st.write("최초 실행 시 백엔드(RUNPOD) 세션이 활성화 되는데 시간이 소요 됩니다.")
    st.write(
        "주의사항 : 1분 동안 아무 요청이 없을 경우 백엔드(RUNPOD)세션이 종료 됩니다."
    )


def initialize_session_state():
    """세션 상태 초기화 함수"""
    if "last_url" not in st.session_state:
        st.session_state.last_url = ""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_input" not in st.session_state:
        st.session_state.last_input = ""
    if "title" not in st.session_state:
        st.session_state.title = ""
    if "hashtags" not in st.session_state:
        st.session_state.hashtags = ""
    if "video_id" not in st.session_state:
        st.session_state.video_id = ""
    if "summary" not in st.session_state:
        st.session_state.summary = ""
    if "transcript" not in st.session_state:
        st.session_state.transcript = []
    if "recommendations" not in st.session_state:
        st.session_state.recommendations = []
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())
    if "runpod_id" not in st.session_state:
        st.session_state.runpod_id = os.getenv("RUNPOD_ENDPOINT_ID")


def reset_session_state():
    """새로운 URL 처리를 위한 세션 상태 리셋 함수"""
    st.session_state.messages = []
    st.session_state.last_input = ""
    st.session_state.title = ""
    st.session_state.hashtags = ""
    st.session_state.video_id = ""
    st.session_state.summary = ""
    st.session_state.transcript = []
    st.session_state.recommendations = []
    st.session_state.session_id = str(uuid.uuid4())  # 새로운 세션 ID 생성


initialize_session_state()


def process_chat_response(prompt, url_id, message_placeholder):
    """AI 응답을 스트리밍 방식으로 처리"""
    bot_message = ""
    payload = {
        "input": {
            "endpoint": "rag_stream_chat",
            "headers": {"x-session-id": st.session_state.session_id},
            "params": {"prompt": prompt, "url_id": url_id},
        }
    }

    try:
        chunks = check_runpod_status(payload, st.session_state.runpod_id)
        for chunk in chunks.get("output"):
            if "content" in chunk:
                content = chunk["content"]
                if content == "[DONE]":
                    break
                bot_message += content
                message_placeholder.write(f"{bot_message}▌")
                time.sleep(0.05)

        return bot_message
    except Exception as e:
        st.error(f"오류가 발생했습니다: {e}")
        return None


def handle_question(question):
    """추천 질문이나 사용자 입력 질문 처리"""
    current_time = get_current_time()

    # 사용자 메시지 추가 및 표시
    user_message = f"{question} ({current_time})"
    with st.chat_message("user"):
        st.write(user_message)
    st.session_state.messages.append({"role": "user", "content": user_message})

    # 봇 응답 생성
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        bot_message = process_chat_response(
            question, st.session_state.video_id, message_placeholder
        )

        if bot_message:
            final_message = f"{bot_message} ({current_time})"
            message_placeholder.write(final_message)
            st.session_state.messages.append(
                {"role": "assistant", "content": final_message}
            )


# 유튜브 URL 입력 받기
col1, col2 = st.columns([3, 1])
with col1:
    url = st.text_input("유튜브 URL을 입력하세요:", key="youtube_url")
with col2:
    model = st.selectbox(
        "모델 선택", ["gpt4o-mini", "Qwen2.5-7b"], key="model_selection"
    )

# 모델 선택에 따라 session_state 값 업데이트
if model == "Qwen2.5-7b":
    st.session_state.runpod_id = os.getenv("RUNPOD_ENDPOINT_ID_VLLM")
else:
    st.session_state.runpod_id = os.getenv("RUNPOD_ENDPOINT_ID")

# URL이 변경되었는지 확인하고 처리
if url != st.session_state.last_url:
    st.session_state.last_url = url
    if url:  # URL이 있는 경우에만 리셋
        reset_session_state()

# URL 입력 및 스크립트 추출을 위한 버튼 클릭 상태 확인
if st.button("스크립트 추출"):
    if url:
        if "youtu" not in url:
            st.warning("유효한 유튜브 URL을 입력하세요.")
        else:
            st.session_state.video_id = get_video_id(url)
            # get_title_hash 엔드포인트 호출
            payload = {
                "input": {
                    "endpoint": "get_title_hash",
                    "params": {"url": url, "url_id": st.session_state.video_id},
                }
            }
            data = check_runpod_status(payload, st.session_state.runpod_id)
            st.write(data)
            st.session_state.title = data.get("output", {}).get("title", "제목")
            st.session_state.hashtags = data.get("output", {}).get("hashtags", "")
            st.rerun()  # 기본 정보를 표시하기 위한 리런

if st.session_state.title:  # 타이틀이 존재하는 경우에만 레이아웃 표시
    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"제목 : {st.session_state.title}")
        st.write(st.session_state.hashtags)

        if st.session_state.video_id:
            st.markdown(
                f'<iframe width="100%" height="600" src="https://www.youtube.com/embed/{st.session_state.video_id}" '
                f'frameborder="0" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" '
                f"allowfullscreen></iframe>",
                unsafe_allow_html=True,
            )
        if not st.session_state.summary:
            with st.spinner("요약 중입니다..."):
                # get_script_summary 엔드포인트 호출
                payload = {
                    "input": {
                        "endpoint": "get_script_summary",
                        "headers": {"x-session-id": st.session_state.session_id},
                        "params": {"url": url, "url_id": st.session_state.video_id},
                    }
                }

                # 상태를 직접 확인하여 작업 완료 시까지 대기
                summary_response = check_runpod_status(
                    payload, st.session_state.runpod_id
                )

                if summary_response:
                    result = summary_response.get("output", {})
                    summary = result.get("summary_result", "없음")
                    questions = result.get("recommended_questions", "")
                    summary[0] = f"KEY TOPIC : {summary[0]}"
                    st.session_state.summary = summary
                    st.session_state.recommendations = questions
                    st.session_state.language = result.get("language", "")
                    st.session_state.transcript = result.get("script", [])
                else:
                    st.error("스크립트 요약에 실패했습니다.")
        if st.session_state.summary:
            st.subheader("요약내용")
            for summary in st.session_state.summary:
                st.write(summary)

            transcript_expander = st.expander("스크립트 보기", expanded=False)
            with transcript_expander:
                if st.session_state.transcript:
                    with st.container(height=400):
                        for item in st.session_state.transcript:
                            st.write(
                                f"{item['start']}초 - {item['end']}초: {item['text']}"
                            )

    with col2:
        st.subheader("AI 채팅")

        # 추천 질문 섹션
        if st.session_state.recommendations:
            recommed_container = st.container(border=True)
            with recommed_container:
                st.write("추천 질문(click):")
                # 각 질문에 대한 버튼 생성
                for question in st.session_state.recommendations:
                    if st.button(question, key=f"btn_{question}"):
                        handle_question(question)

        # 메시지를 표시할 고정 컨테이너
        messages_container = st.container(height=800)

        # 채팅 입력창을 위한 컨테이너
        input_container = st.container()

        # 채팅 입력 처리
        with input_container:
            prompt = st.chat_input("메시지를 입력하세요")

        # 메시지 표시 (채팅 이력)
        with messages_container:
            # 이전 메시지들 표시
            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.write(message["content"])

        # 새 메시지 처리
        if prompt:
            handle_question(prompt)
        if st.session_state.summary and st.session_state.transcript:
            st.markdown("---")
            st.header("데이터 다운로드")
            file_buffer = create_downloadable_file(st.session_state)
            st.download_button(
                label="요약, 스크립트, 채팅 내역 다운로드",
                data=file_buffer,
                file_name="youtube.txt",
                mime="text/plain",
            )


st.markdown("---")
st.header("피드백을 보내주세요.")
feedback = st.text_area("사용 시 불편한 점이나, 오류가 있었다면 알려주세요.:")
if st.button("전송"):
    if feedback:
        if send_feedback_email(feedback, st.session_state.session_id):
            st.success("피드백 감사합니다!")
        else:
            st.error("전송 중 오류가 발생했습니다. 나중에 다시 시도해 주세요.")
    else:
        st.warning("피드백을 입력해 주세요.")
