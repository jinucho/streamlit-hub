from datetime import datetime

import streamlit as st
from utils import (add_notice, delete_notice, load_notices, update_notice,
                   verify_admin)

# 페이지 네비게이션 숨기기
hide_pages = """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
"""
st.markdown(hide_pages, unsafe_allow_html=True)

# 세션 상태 초기화
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = False
if "edit_id" not in st.session_state:  
    st.session_state.edit_id = None



# 관리자 인증 UI
if not st.session_state.admin_authenticated:
    st.title("🔒 관리자 로그인")

    # 홈으로 돌아가기 버튼 (로그인 전)
    if st.button("🏠 홈으로 돌아가기"):
        st.switch_page("home.py")

    st.markdown("---")  # 구분선 추가

    with st.form("admin_login"):
        username = st.text_input("사용자 이름")
        password = st.text_input("비밀번호", type="password")
        submit = st.form_submit_button("로그인")

        if submit:
            if verify_admin(username, password):
                st.session_state.admin_authenticated = True
                st.success("로그인 성공!")
                st.rerun()
            else:
                st.error("인증 실패. 사용자 이름과 비밀번호를 확인하세요.")
else:
    # 관리자 대시보드
    st.title("🔧 관리자 대시보드")

    # 탭 생성
    tab1, tab2 = st.tabs(["공지사항 관리", "기타 설정"])

    # 공지사항 관리 탭
    with tab1:
        st.header("공지사항 관리")

        # 공지사항 불러오기
        notices = load_notices()
        if not isinstance(notices, list):
            notices = []

        # 공지사항 추가/수정 폼
        with st.form("notice_form"):
            if st.session_state.edit_mode:
                st.subheader("✏️ 공지사항 수정")
                notice = next((n for n in notices if n["id"] == st.session_state.edit_id), None)
                if notice:
                    edited_date = st.date_input("날짜 선택", value=datetime.strptime(notice["date"], "%Y-%m-%d"))
                    edited_content = st.text_area("내용 입력", value=notice.get("content", ""))
                    if st.form_submit_button("✅ 수정 완료"):
                        update_notice(
                            st.session_state.edit_id,
                            {
                                "date": edited_date.strftime("%Y-%m-%d"),
                                "content": edited_content.replace("\n", "<br>"),
                            }
                        )
                        st.session_state.edit_mode = False
                        st.session_state.edit_id = None
                        st.rerun()
            else:
                st.subheader("➕ 새 공지사항 추가")
                new_date = st.date_input("날짜 선택", value=datetime.now())
                new_content = st.text_area("새 공지사항 내용 입력")
                if st.form_submit_button("✅ 추가"):
                    add_notice(
                        {
                            "date": new_date.strftime("%Y-%m-%d"),
                            "content": new_content.replace("\n", "<br>"),
                        }
                    )
                    st.success("새 공지사항이 추가되었습니다.")
                    st.rerun()


        # 공지사항 목록 표시 (폼 외부에 배치)
        st.subheader("공지사항 목록")
        if notices:
            # 날짜 기준으로 내림차순 정렬 (최신순)
            sorted_notices = sorted(
                notices, key=lambda x: x.get("date", ""), reverse=True
            )

            for notice in sorted_notices:
                notice_id = notice["id"]
                with st.expander(f"{notice.get('date', '날짜 없음')} - {notice.get('content', '')}", expanded=False):
                    st.write(f"**{notice.get('date', '날짜 없음')}**")
                    st.write(notice.get("content", "내용 없음"))

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("✏️ 수정", key=f"edit_{notice_id}"):
                            st.session_state.edit_mode = True
                            st.session_state.edit_id = notice_id
                            st.rerun()
                    with col2:
                        if st.button("🗑 삭제", key=f"delete_{notice_id}"):
                            delete_notice(notice_id)
                            st.success("공지사항이 삭제되었습니다.")
                            st.rerun()


        else:
            st.info("등록된 공지사항이 없습니다.")

    # 기타 설정 탭
    with tab2:
        st.header("기타 설정")
        st.info("추후 추가될 관리 기능들이 이곳에 표시됩니다.")

    # 로그아웃 버튼
    if st.sidebar.button("로그아웃"):
        st.session_state.admin_authenticated = False
        st.rerun()

    # 홈으로 돌아가기 버튼
    if st.sidebar.button("홈으로 돌아가기"):
        st.switch_page("home.py")
