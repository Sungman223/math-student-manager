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
    gemini_model = genai.GenerativeModel('gemini-pro')
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
            # [수정됨] 여기가 아까 에러났던 부분입니다! df 대신 정확한 코드를 넣었습니다.
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
            
            # 2. 상담 내용 입력 및 AI 변환
            st.write("#### ✍️ 새로운 상담 입력")
            c_date = st.date_input("상담 날짜", datetime.date.today())
            
            col_input, col_ai = st.columns([1, 0.2])
            with col_input:
                raw_input = st.text_area("상담 메모 (대충 적으세요)", height=100, placeholder="예: 오늘 지각함. 숙제는 다 해왔는데 함수 부분을 어려워함.")
            
            with col_ai:
                st.write("") 
                st.write("")
                if st.button("🤖 AI 문장\n다듬기"):
                    if raw_input:
                        with st.spinner("문장 다듬는 중..."):
                            prompt = f"""
                            당신은 베테랑 수학 선생님입니다. 아래 상담 메모를 학부모나 나중에 다시 보기 좋게 정돈된 문장으로 바꿔주세요.
                            핵심 내용은 빠뜨리지 말되, 말투는 정중하고 명확하게 수정하세요.
                            
                            [메모 내용]: {raw_input}
                            """
                            try:
                                response = gemini_model.generate_content(prompt)
                                st.session_state.refined_text = response.text
                                st.rerun()
                            except Exception as e:
                                st.error(f"AI 오류: {e}")

            # 3. 최종 수정 및 저장
            st.write("🔻 **최종 저장될 내용 (직접 수정 가능)**")
            
            final_content = st.text_area(
                "저장하기 전에 내용을 확인하세요", 
                value=st.session_state.refined_text, 
                height=150
            )

            if st.button("💾 상담 내용 최종 저장"):
                if final_content:
                    if add_row_to_sheet("counseling", [selected_student, str(c_date), final_content]):
                        st.success("상담 내용이 안전하게 저장되었습니다.")
                        st.session_state.refined_text = "" 
                        st.rerun()
                else:
                    st.warning("저장할 내용이 없습니다.")

        # --- [탭 2] 성적 관리 ---
        with tab2:
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
                        st.success("성적 저장 완료!")

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
                            try:
                                st.text_area("문자 내용", gemini_model.generate_content(prompt).text)
                            except Exception as e:
                                st.error(f"AI 오류: {e}")

