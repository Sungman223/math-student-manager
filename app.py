import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import altair as alt
import re

# ==========================================
# [설정 1] 구글 시트 ID
# ==========================================
GOOGLE_SHEET_KEY = "1zJHY7baJgoxyFJ5cBduCPVEfQ-pBPZ8jvhZNaPpCLY4"

# ==========================================
# [설정 2] 인증 및 연결 함수
# ==========================================
@st.cache_resource
def get_google_sheet_connection():
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        return None

def load_data_from_sheet(worksheet_name):
    try:
        client = get_google_sheet_connection()
        if not client: return pd.DataFrame()
        sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet(worksheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

def add_row_to_sheet(worksheet_name, row_data_list):
    try:
        client = get_google_sheet_connection()
        if not client: return False
        sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet(worksheet_name)
        sheet.append_row(row_data_list)
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

# ==========================================
# 메인 앱 화면
# ==========================================
st.set_page_config(page_title="강북청솔 학생 관리", layout="wide")
st.title("👨‍🏫 김성만 선생님의 학생 관리 시스템")

menu = st.sidebar.radio("메뉴", ["학생 관리 (상담/성적)", "신규 학생 등록"])

# ------------------------------------------
# 1. 신규 학생 등록
# ------------------------------------------
if menu == "신규 학생 등록":
    st.header("📝 신규 학생 등록")
    with st.form("new_student"):
        col1, col2 = st.columns(2)
        name = col1.text_input("학생 이름")
        ban = col2.text_input("반 (Class)")
        origin = st.text_input("출신 중학교")
        target = st.text_input("배정 예정 고등학교")
        addr = st.text_input("거주지 (대략적)")
        
        if st.form_submit_button("등록"):
            if name:
                if add_row_to_sheet("students", [name, ban, origin, target, addr]):
                    st.success(f"{name} 학생 등록 완료!")
                    st.balloons()

# ------------------------------------------
# 2. 학생 관리 (상담/성적/리포트)
# ------------------------------------------
elif menu == "학생 관리 (상담/성적)":
    df_students = load_data_from_sheet("students")
    
    if df_students.empty:
        st.warning("학생 데이터가 없습니다. 먼저 학생을 등록해주세요.")
    else:
        # 학생 선택
        student_list = df_students["이름"].tolist()
        selected_student = st.sidebar.selectbox("학생 선택", student_list)
        
        info = df_students[df_students["이름"] == selected_student].iloc[0]
        ban_txt = info['반'] if '반' in info else ''
        st.sidebar.info(f"**{info['이름']} ({ban_txt})**\n\n🏫 {info['출신중']} ➡️ {info['배정고']}\n🏠 {info['거주지']}")

        tab1, tab2, tab3 = st.tabs(["🗣️ 상담 일지", "📊 주간 학습 & 성취도 입력", "👨‍👩‍👧‍👦 학부모 전송용 리포트"])

        # --- [탭 1] 상담 일지 ---
        with tab1:
            st.subheader(f"{selected_student} 상담 기록")
            df_c = load_data_from_sheet("counseling")
            with st.expander("📂 이전 상담 내역"):
                if not df_c.empty:
                    logs = df_c[df_c["이름"] == selected_student]
                    for _, r in logs.iterrows():
                        st.markdown(f"**🗓️ {r['날짜']}**")
                        st.info(r['내용'])

            st.divider()
            st.write("#### ✍️ 새로운 상담 입력")
            c_date = st.date_input("날짜", datetime.date.today())
            c_txt = st.text_area("내용", height=100)
            if st.button("저장", key="save_counsel"):
                if c_txt:
                    if add_row_to_sheet("counseling", [selected_student, str(c_date), c_txt]):
                        st.success("저장되었습니다.")
                        st.rerun()

        # --- [탭 2] 성적 입력 ---
        with tab2:
            st.subheader("📊 성적 데이터 입력")
            c1, c2 = st.columns(2)
            mon = c1.selectbox("월", [f"{i}월" for i in range(1, 13)])
            wk = c2.selectbox("주차", [f"{i}주차" for i in range(1, 6)])
            period = f"{mon} {wk}"

            with st.form("grade_form"):
                st.write("**[주간 과제]**")
                cc1, cc2, cc3 = st.columns(3)
                hw = cc1.number_input("수행도(%)", 0, 100, 80)
                w_sc = cc2.number_input("점수", 0, 100, 0)
                w_av = cc3.number_input("반 평균", 0, 100, 0)
                wrong = st.text_input("오답 문항 (예: 13 15)", placeholder="띄어쓰기로 구분 가능")
                memo = st.text_area("특이사항", height=50)

                st.divider()
                st.write("**[성취도 평가]** (없으면 0)")
                cc4, cc5 = st.columns(2)
                a_sc = cc4.number_input("성취도 점수", 0, 100, 0)
                a_av = cc5.number_input("성취도 평균", 0, 100, 0)
                rev = st.text_area("총평", height=80)

                if st.form_submit_button("성적 저장"):
                    row = [selected_student, period, hw, w_sc, w_av, wrong, memo, a_sc, a_av, rev]
                    if add_row_to_sheet("weekly", row):
                        st.success("저장 완료!")

        # --- [탭 3] 학부모 리포트 (수정됨) ---
        with tab3:
            st.header(f"📑 {selected_student} 학생 학습 리포트")
            st.divider()

            df_w = load_data_from_sheet("weekly")
            if not df_w.empty:
                my_w = df_w[df_w["이름"] == selected_student]
                if not my_w.empty:
                    periods = my_w["시기"].tolist()
                    sel_p = st.multiselect("기간 선택:", periods, default=periods)
                    
                    if sel_p:
                        rep = my_w[my_w["시기"].isin(sel_p)].copy()

                        # [오답번호 콤마 변환]
                        if '오답번호' in rep.columns:
                            rep['오답번호'] = rep['오답번호'].astype(str).apply(
                                lambda x: re.sub(r'[\s,]+', ', ', x).strip(', ') if x else ''
                            )

                        # 1. 주간 과제 그래프 (고정축, 줌X)
                        st.subheader("1️⃣ 주간 과제 성취도")
                        base = alt.Chart(rep).encode(x=alt.X('시기', sort=None))
                        y_fix = alt.Scale(domain=[0, 100])

                        l1 = base.mark_line(color='#29b5e8').encode(y=alt.Y('주간점수', scale=y_fix))
                        p1 = base.mark_point(color='#29b5e8', size=100).encode(y='주간점수')
                        t1 = base.mark_text(dy=-15, fontSize=14, color='#29b5e8', fontWeight='bold').encode(y='주간점수', text='주간점수')
                        l2 = base.mark_line(color='gray', strokeDash=[5,5]).encode(y='주간평균')
                        
                        st.altair_chart(l1 + p1 + t1 + l2, use_container_width=True)

                        # 2. 성취도 그래프 (데이터 있을 때만)
                        if "성취도점수" in rep.columns and rep["성취도점수"].sum() > 0:
                            st.subheader("2️⃣ 성취도 평가 결과")
                            ach_d = rep[rep["성취도점수"] > 0]
                            base_ach = alt.Chart(ach_d).encode(x=alt.X('시기', sort=None))
                            
                            al1 = base_ach.mark_line(color='#ff6c6c').encode(y=alt.Y('성취도점수', scale=y_fix))
                            ap1 = base_ach.mark_point(color='#ff6c6c', size=100).encode(y='성취도점수')
                            at1 = base_ach.mark_text(dy=-15, fontSize=14, color='#ff6c6c', fontWeight='bold').encode(y='성취도점수', text='성취도점수')
                            al2 = base_ach.mark_line(color='gray', strokeDash=[5,5]).encode(y='성취도평균')
                            
                            st.altair_chart(al1 + ap1 + at1 + al2, use_container_width=True)

                        # 3. 상세 표
                        st.subheader("3️⃣ 상세 학습 내역")
                        cols = ["시기", "과제", "주간점수", "주간평균", "오답번호", "특이사항", "성취도점수", "성취도평균"]
                        real_cols = [c for c in cols if c in rep.columns]
                        
                        disp = rep[real_cols].copy()
                        rename_map = {"시기":"시기", "과제":"과제(%)", "주간점수":"점수", "주간평균":"반평균", 
                                      "오답번호":"오답", "특이사항":"코멘트", "성취도점수":"성취도", "성취도평균":"성취도평균"}
                        disp.rename(columns=rename_map, inplace=True)
                        st.table(disp.set_index("시기"))

                        # 4. 총평 (파란 박스)
                        for i, r in rep.iterrows():
                            if r.get('총평'):
                                st.info(f"**[{r['시기']} 총평]**\n\n{r['총평']}")
                    else:
                        st.warning("기간을 선택해주세요.")
                else:
                    st.info("데이터가 없습니다.")
