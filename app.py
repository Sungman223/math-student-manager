import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import google.generativeai as genai
import datetime

# ==========================================
# [보안 설정] 비밀 정보 불러오기 (st.secrets 사용)
# ==========================================

# 1. 구글 시트 설정
GOOGLE_SHEET_NAME = "학생관리데이터"  # 이건 공개되어도 상관없으니 그냥 둡니다.

# 2. 구글 시트 인증 함수 (수정됨: 파일 대신 secrets에서 읽기)
@st.cache_resource
def get_google_sheet_connection():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # [변경점] json 파일 이름 대신 st.secrets 딕셔너리를 사용합니다.
    # secrets.toml의 [gcp_service_account] 섹션을 가져옵니다.
    creds_dict = dict(st.secrets["gcp_service_account"])
    
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# 3. Gemini AI 설정 (수정됨: secrets에서 키 읽기)
try:
    # [변경점] 코드에 키를 적지 않고 secrets에서 가져옵니다.
    genai.configure(api_key=st.secrets["GENAI_API_KEY"])
    gemini_model = genai.GenerativeModel('gemini-pro')
except Exception as e:
    st.error(f"Gemini API 키 설정 오류: {e}")

# ==========================================
# (이 아래부터는 이전 코드와 동일합니다)
# ==========================================

def load_data_from_sheet(worksheet_name):
    try:
        client = get_google_sheet_connection()
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet(worksheet_name)
        data = sheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"데이터를 불러오는데 실패했습니다: {e}")
        return pd.DataFrame()

def add_row_to_sheet(worksheet_name, row_data_list):
    try:
        client = get_google_sheet_connection()
        sheet = client.open(GOOGLE_SHEET_NAME).worksheet(worksheet_name)
        sheet.append_row(row_data_list)
        return True
    except Exception as e:
        st.error(f"저장 실패: {e}")
        return False

# ... (나머지 UI 코드는 그대로 사용하시면 됩니다) ...