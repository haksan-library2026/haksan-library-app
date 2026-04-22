import streamlit as st
import pandas as pd
import google.generativeai as genai

# 1. 페이지 설정
st.set_page_config(page_title="학산여고 마음 처방 도서관", page_icon="📚")

# 2. 데이터 불러오기 (파일 이름을 data.csv로 고정)
try:
    df = pd.read_csv('data.csv')
except FileNotFoundError:
    st.error("⚠️ 'data.csv' 파일을 찾을 수 없습니다. 깃허브에서 도서 목록 파일 이름을 'data.csv'로 변경해주세요.")
    st.stop()

# 3. 제목 및 안내
st.title("📚 학산여고 마음 처방 도서관")
st.subheader("지금 당신의 마음에 필요한 책을 추천해 드립니다.")

# 4. 입력창 및 로직 (예시 - 선생님의 기존 기획에 맞춰 수정 가능)
user_input = st.text_input("오늘 기분은 어떠신가요? (예: 시험 때문에 불안해요, 위로받고 싶어요)")

if st.button("처방전 받기"):
    if user_input:
        st.info(f"'{user_input}'에 대한 마음 처방을 준비 중입니다...")
        # 여기에 AI 추천 로직이 들어갑니다.
        st.write("📖 추천 도서: 선생님의 도서 목록에서 가장 적합한 책을 찾는 중입니다.")
    else:
        st.warning("증상을 입력해주세요!")
