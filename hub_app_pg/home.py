import streamlit as st
from utils import load_notices

# Streamlit 웹 애플리케이션 설정
st.set_page_config(page_title="포도남자의 AI Projects", page_icon="🏠", layout="wide")

# 홈페이지 제목
st.title("🚀 포도남자의 AI Projects")
st.write("LLM, RAG, LangChain, LangGraph 기반 AI 애플리케이션 모음")
st.markdown("---")

# 공지사항 불러오기
notices = load_notices()

# 공지사항 표시
with st.expander("🔔 업데이트 내역", expanded=False):
    with st.container(height=300):
        if notices:
            # 날짜 기준으로 내림차순 정렬 (최신순)
            sorted_notices = sorted(notices, key=lambda x: x.get("date", ""), reverse=True)

            for notice in sorted_notices:
                st.markdown(f"#### {notice['date']}")
                st.markdown(notice["content"], unsafe_allow_html=True)
        else:
            st.info("등록된 공지사항이 없습니다.")

# 페이지 네비게이션 숨기기
hide_pages = """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
"""
st.markdown(hide_pages, unsafe_allow_html=True)


st.markdown("---")
# 사용 가능한 프로젝트 섹션
st.markdown("## 📌 Project List")

# 프로젝트 목록
projects = [
    {
        "name": "유튜브 스크립트 추출 및 AI 채팅",
        "page": "./pages/youtube_script_chatbot.py",
        "icon": "📺",
        "thumbnail": "https://raw.githubusercontent.com/jinucho/streamlit-hub/refs/heads/main/hub_app/assets/youtube_script_chatbot.webp",
        "description": "유튜브 영상에서 음성을 스크립트로 추출하고 요약 및 AI 채팅",
    },
    {
        "name": "음성 녹음 요약",
        "page": "./pages/voice_record_summary.py",
        "icon": "🎤",
        "thumbnail": "https://raw.githubusercontent.com/jinucho/streamlit-hub/refs/heads/main/hub_app/assets/voice_record_summary.webp",
        "description": "음성 녹음을 텍스트로 변환 후 회의록 작성",
    },
    {
        "name": "먹텐 - 맛집 추천 AI",
        "page": "./pages/meokten.py",
        "icon": "🍽️",
        "thumbnail": "https://raw.githubusercontent.com/jinucho/streamlit-hub/refs/heads/main/hub_app/assets/MeokTen.png",
        "description": "성시경 유튜브 먹을텐데 컨텐츠기반 맛집 추천",
    },
]

# 각 프로젝트를 위한 컨테이너 생성
with st.container(height=800):
    # 프로젝트를 카드 형태로 세로로 표시
    for project in projects:
        # 제목과 아이콘
        st.subheader(f"{project['icon']} {project['name']}")

        # 이미지와 설명을 가로로 배치
        cols = st.columns([1, 5])  # 이미지:설명 = 3:5 비율

        with cols[0]:
            # 이미지 표시 (더 큰 크기로)
            st.image(project["thumbnail"], width=200)

        with cols[1]:
            # 설명과 링크 버튼
            st.markdown(f"### 📄 Description")
            st.markdown(f"{project['description']}")
            st.page_link(project["page"], label="🔗 바로가기")

        # 구분선 추가
        st.markdown("---")


# 사이드바 설정
with st.sidebar:
    st.markdown("### 📌 Project Navigation")
    st.page_link("home.py", label="🏠 홈")
    for project in projects:
        st.page_link(project["page"], label=f"{project['icon']} {project['name']}")
    st.markdown("---")
    st.page_link("./pages/admin.py", label="🔒 관리자 페이지")
    st.page_link("https://grapeman.duckdns.org/notion", label="👨‍💻 포트폴리오")

    st.markdown("---")

    # 기술 스택 섹션
    st.markdown("## 🛠️ 주요 기술 스택")
    st.markdown(
        """
        <div class="small-font">
        <ul>
            <li><b>Language</b>: Python</li>
            <li><b>LLM</b>: OpenAI, VLLM</li>
            <li><b>Vector DB(Index)</b>: FAISS</li>
            <li><b>Framework</b>: LangChain, LangGraph</li>
            <li><b>Speech2Text</b>: Faster-Whisper</li>
            <li><b>UI</b>: Streamlit</li>
            <li><b>Backend</b>: RunPod Serverless</li>
            <li><b>Map</b>: Folium</li>
        </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.subheader("Contact")
    st.markdown("📧 Email: duojinwu@gmail.com")
    st.markdown("💻 GitHub: https://github.com/jinucho")
    st.markdown("🔗 LinkedIn: https://www.linkedin.com/in/jinucho")
    st.markdown("""
        <a href="https://www.buymeacoffee.com/duojinwuq" target="_blank">
            <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" 
                alt="Buy Me A Coffee" 
                style="height: 60px; width: 217px;" >
        </a>
    """, unsafe_allow_html=True)
    
