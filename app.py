import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import datetime
import altair as alt

# ==========================================
# [설정 1] 구글 시트 ID
# ==========================================
GOOGLE_SHEET_KEY = "1zJHY7baJgoxyFJ5cBduCPVEfQ-pBPZ8jvhZNaPpCLY4"

# ==========================================
# [설정 2] 인증 및 연결 함수
# ==========================================
@st.cache_resource
def get_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_data_from_sheet(worksheet_name):
    try:
        client = get_google_sheet_connection()
        sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet(worksheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        return pd.DataFrame()

def add_row_to_sheet(worksheet_name, row_data_list):
    try:
        client = get_google_sheet_connection()
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

# 메뉴
menu = st.sidebar.radio("메뉴", ["학생 관리 (상담/성적)", "신규 학생 등록"])

# ------------------------------------------
# 1. 신규 학생 등록
# ------------------------------------------
if menu == "신규 학생 등록":
    st.header("📝 신규 학생 등록")
    with st.form("new_student"):
        name = st.text_input("학생 이름")
        origin = st.text_input("출신 중학교")
        target = st.text_input("배정 예정 고등학교")
        addr = st.text_input("거주지 (대략적)")
        submit = st.form_submit_button("등록")

        if submit and name:
            if add_row_to_sheet("students", [name, origin, target, addr]):
                st.success(f"{name} 학생 등록 완료!")
                st.balloons()

# ------------------------------------------
# 2. 학생 관리 (상담/성적)
# ------------------------------------------
elif menu == "학생 관리 (상담/성적)":
    df_students = load_data_from_sheet("students")
    
    if df_students.empty:
        st.warning("등록된 학생이 없습니다. 시트 제목(이름, 등)을 확인하세요.")
    else:
        # 학생 선택
        student_list = df_students["이름"].tolist()
        selected_student = st.sidebar.selectbox("학생 선택", student_list)
        
        info = df_students[df_students["이름"] == selected_student].iloc[0]
        st.sidebar.info(f"**{info['이름']}**\n\n🏫 {info['출신중']} ➡️ {info['배정고']}\n🏠 {info['거주지']}")

        tab1, tab2 = st.tabs(["🗣️ 상담 일지", "📊 주간 학습 & 성취도"])

        # --- [탭 1] 상담 일지 ---
        with tab1:
            st.subheader(f"{selected_student} 상담 기록")
            
            # 1. 이전 기록 보기
            df_counsel = load_data_from_sheet("counseling")
            with st.expander("📂 이전 상담 내역 펼치기"):
                if not df_counsel.empty:
                    my_logs = df_counsel[df_counsel["이름"] == selected_student]
                    if not my_logs.empty:
                        try:
                            my_logs = my_logs.sort_values(by="날짜", ascending=False)
                        except:
                            pass
                        for _, row in my_logs.iterrows():
                            st.markdown(f"**🗓️ {row['날짜']}**")
                            st.info(row['내용']) 
                    else:
                        st.caption("기록된 상담이 없습니다.")

            st.divider()
            
            # 2. 새로운 상담 입력
            st.write("#### ✍️ 새로운 상담 입력")
            c_date = st.date_input("상담 날짜", datetime.date.today())
            counsel_content = st.text_area("상담 내용을 자유롭게 작성하세요", height=150)

            if st.button("💾 상담 내용 저장"):
                if counsel_content:
                    if add_row_to_sheet("counseling", [selected_student, str(c_date), counsel_content]):
                        st.success("상담 내용이 저장되었습니다.")
                        st.rerun()
                else:
                    st.warning("내용을 입력해주세요.")

        # --- [탭 2] 성적 관리 ---
        with tab2:
            st.subheader("📊 주간 과제 & 성취도 평가")
            
            # 날짜 및 주기 선택
            col1, col2 = st.columns(2)
            month = col1.selectbox("월", [f"{i}월" for i in range(1, 13)])
            week = col2.selectbox("주차", [f"{i}주차" for i in range(1, 6)])
            period = f"{month} {week}"

            with st.form("grade_form"):
                st.write("##### 📝 주간 과제 수행 (Weekly)")
                c1, c2, c3 = st.columns(3)
                hw_score = c1.number_input("과제 수행도(%)", 0, 100, 80)
                weekly_score = c2.number_input("주간 과제 점수", 0, 100, 0)
                weekly_avg = c3.number_input("반 평균", 0, 100, 0)
                
                wrong_answers = st.text_input("❌ 오답 문항 번호 (예: 13, 15, 22)", placeholder="틀린 문제 번호를 적으세요")

                st.divider()
                
                # 성취도 평가
                st.write("##### 🏆 성취도 평가 (해당될 때만 입력)")
                with st.expander("성취도 평가 점수 입력 열기"):
                    cc1, cc2 = st.columns(2)
                    ach_score = cc1.number_input("성취도 점수 (없으면 0)", 0, 100, 0)
                    ach_avg = cc2.number_input("성취도 반 평균 (없으면 0)", 0, 100, 0)
                
                total_review = st.text_area("📝 이번 주 총평")

                if st.form_submit_button("성적 및 평가 저장"):
                    row_data = [selected_student, period, hw_score, weekly_score, weekly_avg, wrong_answers, ach_score, ach_avg, total_review]
                    if add_row_to_sheet("weekly", row_data):
                        st.success("데이터 저장 완료!")

            # --- 데이터 시각화 (0~100점 고정, 줌 끄기, 숫자 표시) ---
            st.divider()
            df_weekly = load_data_from_sheet("weekly")
            
            if not df_weekly.empty:
                my_weekly = df_weekly[df_weekly["이름"] == selected_student]
                
                if not my_weekly.empty:
                    st.write("#### 📈 주간 과제 점수 추이")
                    
                    base = alt.Chart(my_weekly).encode(x=alt.X('시기', sort=None))
                    
                    # Y축 0~100 고정
                    y_scale = alt.Scale(domain=[0, 100])

                    # 1. 점수 선 (파랑)
                    line_score = base.mark_line(color='#29b5e8').encode(
                        y=alt.Y('주간점수', scale=y_scale), 
                        tooltip=['시기', '주간점수']
                    )
                    # 2. 점수 점
                    point_score = base.mark_point(color='#29b5e8', size=100).encode(
                        y=alt.Y('주간점수', scale=y_scale)
                    )
                    # 3. 점수 숫자
                    text_score = base.mark_text(dy=-15, fontSize=12, color='#29b5e8').encode(
                        y=alt.Y('주간점수', scale=y_scale), 
                        text='주간점수'
                    )
                    # 4. 평균 선 (회색 점선)
                    line_avg = base.mark_line(color='gray', strokeDash=[5,5]).encode(
                        y=alt.Y('주간평균', scale=y_scale)
                    )
                    
                    st.altair_chart((line_score + point_score + text_score + line_avg), use_container_width=True)
                    
                    # 성취도 평가 그래프
                    if my_weekly["성취도점수"].sum() > 0:
                        st.write("#### 🏆 성취도 평가 기록")
                        ach_data = my_weekly[my_weekly["성취도점수"] > 0]
                        
                        base_ach = alt.Chart(
