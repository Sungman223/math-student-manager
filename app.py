import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# ==========================================
# [설정 1] 구글 시트 ID (선생님 시트)
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
# [설정 3] Gemini AI 설정 (최신 모델 적용됨)
# ==========================================
try:
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
    # [수정] 구형 gemini-pro 대신 최신 gemini-1.5-flash 사용
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.warning(f"Gemini API 설정 오류: {e}")

# ==========================================
# 메인 앱 화면
# ==========================================
st.set_page_config(page_title="강북청솔 학생 관리", layout="wide")
st.title("👨‍🏫 김성만 선생님의 학생 관리 시스템")

# [세션 상태 초기화]
if "refined_text" not in st.session_state:
    st.session_state.refined_text = ""

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

        tab1, tab2 = st.tabs(["🗣️ 상담 일지 (AI 수정)", "📊 주간 학습 & 문자"])

        # --- [탭 1] 상담 일지 ---
        with tab1:
            st.subheader(f"{selected_student} 상담 기록")
            
            # 1. 이전 기록 보기
            df
