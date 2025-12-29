import streamlit as st
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import altair as alt

# ==========================================
# [설정] 구글 시트 연결
# ==========================================
GOOGLE_SHEET_KEY = "1zJHY7baJgoxyFJ5cBduCPVEfQ-pBPZ8jvhZNaPpCLY4"

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

# ==========================================
# 메인 화면
# ==========================================
st.set_page_config(page_title="학생 관리", layout="wide")
st.title("👨‍🏫 학부모 리포트 전용")

df_students = load_data_from_sheet("students")

if df_students.empty:
    st.warning("학생 데이터가 없습니다.")
else:
    student_list = df_students["이름"].tolist()
    selected_student = st.sidebar.selectbox("학생 선택", student_list)
    
    st.header(f"📑 {selected_student} 학생 학습 리포트")
    st.caption("👇 아래 내용을 캡처해서 학부모님께 보내세요.")
    st.divider()

    df_weekly = load_data_from_sheet("weekly")
    
    if not df_weekly.empty:
        my_weekly = df_weekly[df_weekly["이름"] == selected_student]
        
        if not my_weekly.empty:
            # 1. 기간 선택
            all_periods = my_weekly["시기"].tolist()
            selected_periods = st.multiselect("기간 선택:", all_periods, default=all_periods)
            
            if selected_periods:
                report_data = my_weekly[my_weekly["시기"].isin(selected_periods)]

                # [그래프 1] 주간 과제
                st.subheader("1️⃣ 주간 과제 성취도")
                base = alt.Chart(report_data).encode(x=alt.X('시기', sort=None))
                y_scale = alt.Scale(domain=[0, 100])

                line = base.mark_line(color='#29b5e8').encode(y=alt.Y('주간점수', scale=y_scale))
                point = base.mark_point(color='#29b5e8', size=100).encode(y=alt.Y('주간점수', scale=y_scale))
                text = base.mark_text(dy=-15).encode(y=alt.Y('주간점수', scale=y_scale), text='주간점수')
                
                st.altair_chart((line + point + text).interactive(), use_container_width=True)

                # [표] 상세 내역
                st.subheader("2️⃣ 상세 학습 내역")
                display_df = report_data[["시기", "과제", "주간점수", "주간평균", "오답번호", "특이사항"]].copy()
                st.table(display_df.set_index("시기"))

                # [그래프 2] 성취도 평가
                if report_data["성취도점수"].sum() > 0:
                    st.divider()
                    st.subheader("3️⃣ 성취도 평가 결과")
                    ach_data = report_data[report_data["성취도점수"] > 0]
                    
                    base_ach = alt.Chart(ach_data).encode(x=alt.X('시기', sort=None))
                    line_ach = base_ach.mark_line(color='#ff6c6c').encode(y=alt.Y('성취도점수', scale=y_scale))
                    point_ach = base_ach.mark_point(color='#ff6c6c', size=100).encode(y=alt.Y('성취도점수', scale=y_scale))
                    text_ach = base_ach.mark_text(dy=-15).encode(y=alt.Y('성취도점수', scale=y_scale), text='성취도점수')

                    st.altair_chart((line_ach + point_ach + text_ach).interactive(), use_container_width=True)
                    
                    # 총평
                    for i, row in ach_data.iterrows():
                        if row['총평']:
                            st.info(f"**[{row['시기']} 총평]**\n{row['총평']}")
            else:
                st.warning("기간을 선택해주세요.")
        else:
            st.info("데이터가 없습니다.")
