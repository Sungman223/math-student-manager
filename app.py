import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# ==========================================
# [설정 1] 구글 시트 ID로 직접 연결 (가장 확실함)
# ==========================================
# 선생님의 시트 주소에서 복사한 ID입니다.
GOOGLE_SHEET_KEY = "1zJHY7baJgoxyFJ5cBduCPVEfQ-pBPZ8jvhZNaPpCLY4"

# ==========================================
# [설정 2] 인증 및 연결 함수
# ==========================================
@st.cache_resource
def get_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    # Secrets에서 정보 가져오기
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def load_data_from_sheet(worksheet_name):
    try:
        client = get_google_sheet_connection()
        # [변경점] 이름 대신 ID(Key)로 엽니다. 100% 정확합니다.
        sheet = client.open_by_key(GOOGLE_SHEET_KEY).worksheet(worksheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        # 에러가 나면 화면에 이유를 보여줍니다.
        st.error(f"데이터 불러오기 오류 ({worksheet_name}): {e}")
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
# [설정 3] Gemini AI
# ==========================================
try:
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.warning(f"Gemini API 설정 오류: {e}")

# ==========================================
# 메인 앱 화면
# ==========================================
st.set_page_config(page_title="강북청솔 학생 관리", layout="wide")
st.title("👨‍🏫 김성만 선생님의 학생 관리 시스템")

# 메뉴
menu = st.sidebar.radio("메뉴", ["학생 관리 (상담/성적)", "신규 학생 등록"])

if menu == "신규 학생 등록":
    st.header("📝 신규 학생 등록")
    with st.form("new_student"):
        name = st.text_input("학생 이름")
        origin = st.text_input("출신 중학교")
        target = st.text_input("배정 예정 고등학교")
        addr = st.text_input("거주지 (대략적)")
        submit = st.form_submit_button("등록")

        if submit and name:
            # 구글 시트에 바로 저장
            if add_row_to_sheet("students", [name, origin, target, addr]):
                st.success(f"{name} 학생 등록 완료!")
                st.balloons()

elif menu == "학생 관리 (상담/성적)":
    # 학생 명단 불러오기
    df_students = load_data_from_sheet("students")
    
    if df_students.empty:
        st.warning("등록된 학생이 없거나 시트를 읽지 못했습니다. (시트 첫 줄에 '이름' 등 제목을 적었는지 확인하세요!)")
    else:
        student_list = df_students["이름"].tolist()
        selected_student = st.sidebar.selectbox("학생 선택", student_list)
        
        # 선택된 학생 정보
        if not df_students.empty:
            info = df_students[df_students["이름"] == selected_student].iloc[0]
            st.sidebar.info(f"**{info['이름']}**\n\n🏫 {info['출신중']} ➡️ {info['배정고']}\n🏠 {info['거주지']}")

        tab1, tab2 = st.tabs(["🗣️ 상담 일지", "📊 주간 학습 & 문자"])

        with tab1: # 상담 탭
            st.subheader(f"{selected_student} 상담 기록")
            df_counsel = load_data_from_sheet("counseling")
            with st.expander("📂 이전 상담 내역 보기", expanded=True):
                if not df_counsel.empty:
                    my_logs = df_counsel[df_counsel["이름"] == selected_student]
                    if not my_logs.empty:
                         # 날짜순 정렬 시도 (날짜 형식이 다르면 에러날 수 있으므로 try 사용)
                        try:
                            my_logs = my_logs.sort_values(by="날짜", ascending=False)
                        except:
                            pass
                        for _, row in my_logs.iterrows():
                            st.markdown(f"**🗓️ {row['날짜']}**")
                            st.write(row['내용'])
                            st.divider()
                    else:
                        st.caption("기록된 상담이 없습니다.")
            
            st.write("#### ✍️ 새로운 상담 입력")
            c_date = st.date_input("상담 날짜", datetime.date.today())
            c_content = st.text_area("상담 내용", height=100)
            if st.button("상담 저장하기"):
                if add_row_to_sheet("counseling", [selected_student, str(c_date), c_content]):
                    st.success("저장되었습니다.")
                    st.rerun()

        with tab2: # 성적 탭
            st.subheader("주간 성적 관리")
            col1, col2 = st.columns(2)
            month = col1.selectbox("월", [f"{i}월" for i in range(1, 13)])
            week = col2.selectbox("주차", [f"{i}주차" for i in range(1, 6)])
            period = f"{month} {week}"

            with st.form("weekly_form"):
                c1, c2, c3 = st.columns(3)
                hw_score = c1.number_input("과제 수행(%)", 0, 100, 80)
                score = c2.number_input("학생 점수", 0, 100, 0)
                avg = c3.number_input("반 평균", 0, 100, 0)
                memo = st.text_area("특이사항 (선생님 메모)")
                if st.form_submit_button("성적 저장"):
                    if add_row_to_sheet("weekly", [selected_student, period, hw_score, score, avg, memo]):
                        st.success("저장 완료!")

            df_weekly = load_data_from_sheet("weekly")
            if not df_weekly.empty:
                my_weekly = df_weekly[df_weekly["이름"] == selected_student]
                if not my_weekly.empty:
                    st.write("#### 📈 성적 변화")
                    st.line_chart(my_weekly[["시기", "점수", "평균"]].set_index("시기"))
                    
                    st.write("#### 📩 학부모 문자 생성")
                    last_rec = my_weekly.iloc[-1]
                    st.table(pd.DataFrame({"항목": ["시기", "점수", "과제", "특이사항"], "내용": [last_rec['시기'], f"{last_rec['점수']}점", f"{last_rec['과제']}%", last_rec['메모']]}))
                    
                    if st.button("🤖 Gemini 문자 생성"):
                         prompt = f"학부모 문자 작성. 학생:{selected_student}, 시기:{last_rec['시기']}, 점수:{last_rec['점수']}, 과제:{last_rec['과제']}%, 내용:{last_rec['메모']}. 정중하게."
                         with st.spinner("작성 중..."):
                            st.text_area("문자 내용", gemini_model.generate_content(prompt).text)
