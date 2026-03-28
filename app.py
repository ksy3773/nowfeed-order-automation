import streamlit as st
import google.generativeai as genai
import pandas as pd
import json
import io

# --- 1. 제미나이 API 설정 ---
# 실제 사용 시에는 환경변수나 st.secrets를 사용하는 것이 안전합니다.
API_KEY = st.secrets["GEMINI_API_KEY"]API_KEY = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 2. 웹 앱 기본 설정 ---
st.set_page_config(page_title="발주 자동 정리기", layout="centered")
st.title("📦 나우피드 카톡 발주 자동 정리 웹앱")
st.markdown("카톡 대화 내용을 아래에 붙여넣으면 AI가 표 형태로 정리해 줍니다.")

# --- 3. 세션 상태(Session State) 초기화 ---
# 화면이 새로고침되어도 데이터를 유지하기 위함입니다.
if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame(columns=["발주처", "품목명", "수량", "납기일", "비고"])

# --- 4. 사용자 입력 영역 ---
raw_text = st.text_area("카톡 발주 내용 입력", height=150, 
                        placeholder="예: 김사장님, 내일 오전까지 배합사료 A형 50포, B형 20포 부탁합니다.")

if st.button("AI 자동 정리 실행"):
    if raw_text:
        with st.spinner("제미나이가 데이터를 분석하고 있습니다..."):
            # AI에게 내릴 프롬프트 (명령어)
            prompt = f"""
            다음 텍스트에서 발주 관련 정보를 추출해서 반드시 JSON 배열 형식으로만 응답해줘. 
            다른 설명은 절대 하지 마.
            키워드: "발주처", "품목명", "수량", "납기일", "비고"
            수량과 단위를 명확히 구분해 줘. 예를 들어 '배합사료 50포', '첨가제 2톤'이라고 오면 수량 칸에 '50포', '2톤'으로 정확히 기재해.
            날짜는 반드시 "yyyy-mm-dd" 형태로 납기일에 적어줘. 현재날짜 기준으로 내일까지라고 하면 내일 날짜를 적어줘. 오전 오후 이런게 적혀져서 오면 비고란에 적어줘.
            
            텍스트: {raw_text}
            """
            
            try:
                # 제미나이 API 호출
                response = model.generate_content(prompt)
                
                # 마크다운 코드 블록(```json ... ```) 제거 후 파싱
                cleaned_response = response.text.replace('```json', '').replace('```', '').strip()
                data = json.loads(cleaned_response)
                
                # 추출된 데이터를 데이터프레임으로 변환하여 세션에 저장
                new_df = pd.DataFrame(data)
                
                # 기존 데이터가 있으면 합치기, 없으면 대체
                if not st.session_state.df.empty:
                    st.session_state.df = pd.concat([st.session_state.df, new_df], ignore_index=True)
                else:
                    st.session_state.df = new_df
                    
                st.success("데이터 추출 완료!")
            except Exception as e:
                st.error(f"데이터를 추출하는 중 오류가 발생했습니다. 다시 시도해주세요. (에러: {e})")
    else:
        st.warning("먼저 카톡 내용을 입력해주세요.")

# --- 5. 데이터 확인 및 수정 영역 ---
st.subheader("📝 데이터 확인 및 세부 수정")
st.markdown("아래 표를 클릭해서 잘못된 부분을 직접 수정하거나 행을 삭제/추가할 수 있습니다.")

# st.data_editor를 사용하여 사용자가 웹에서 직접 표를 수정할 수 있게 함
edited_df = st.data_editor(st.session_state.df, num_rows="dynamic", key="data_editor")

# --- 6. 엑셀 다운로드 영역 ---
st.subheader("💾 엑셀로 내보내기")

# 메모리 상에서 엑셀 파일 생성 (서버 저장 없이 바로 다운로드)
buffer = io.BytesIO()
with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
    edited_df.to_excel(writer, index=False, sheet_name='발주내역')

st.download_button(
    label="엑셀 파일(.xlsx) 다운로드",
    data=buffer.getvalue(),
    file_name="order_list.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)