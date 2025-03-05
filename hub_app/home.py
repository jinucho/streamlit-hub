import streamlit as st

# Streamlit 웹 애플리케이션 설정
st.set_page_config(page_title="Jinu's AI Projects", page_icon="🏠", layout="wide")

# 공지사항 섹션
st.markdown("## 📢 업데이트")
st.markdown(
    """
- 새 프로젝트 추가 시 여기에 공지  
- 주요 기능 개선 사항 정리
"""
)


# 홈페이지 제목
st.title("🚀 Jinu's AI Projects")
st.markdown("> LLM, RAG, LangChain, LangGraph 기반 AI 애플리케이션 모음")
st.markdown("---")

# 사용 가능한 프로젝트 섹션
st.markdown("## 📌 프로젝트 리스트")

# 프로젝트 목록
projects = [
    {
        "name": "유튜브 스크립트 추출 및 AI 채팅",
        "page": "pages/youtube_script_chatbot.py",
        "icon": "📺",
        "thumbnail": "assets/youtube_thumbnail.jpeg",  # 썸네일 이미지 경로
        "description": "유튜브 영상에서 음성을 스크립트로 추출하고 요약 및 AI 채팅",
    },
    {
        "name": "음성 녹음 요약",
        "page": "pages/voice_record_summary.py",
        "icon": "🎤",
        "thumbnail": "assets/youtube_thumbnail.jpeg",  #
        "description": "음성 녹음을 텍스트로 변환하고 요약",
    },
    # 추가 프로젝트 예시
    # {
    #     "name": "프로젝트명",
    #     "page": "pages/project2.py",
    #     "icon": "🤖",
    #     "thumbnail": "assets/project2_thumbnail.png",
    #     "description": "간단한 설명",
    # },
]

# 프로젝트를 카드 형태로 표시
cols = st.columns(len(projects))  # 프로젝트 개수만큼 컬럼 생성

for col, project in zip(cols, projects):
    with col:
        st.write(f"{project['icon']} {project['name']}")
        st.image(project["thumbnail"], width=500)
        st.markdown(f"📄 Description: {project['description']}")
        st.page_link(project["page"], label="🔗 바로가기")

st.markdown("---")


# 사이드바 설정
with st.sidebar:
    st.markdown("### 📌 NAVIGATION")
    st.page_link("home.py", label="🏠 홈")
    for project in projects:
        st.page_link(project["page"], label=f"{project['icon']} {project['name']}")
    # 기술 스택 섹션
    st.markdown("## 🛠️ 주요 기술 스택")
    st.markdown(
        """
    - **Language**: Python
    - **LLM**: OpenAI, Hugging Face
    - **Vector DB(Index)**: FAISS
    - **Framework**: LangChain, LangGraph
    - **Speech2Text**: Faster-Whisper
    - **UI**: Streamlit
    - **Backend**: RunPod
    """
    )
