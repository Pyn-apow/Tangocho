import streamlit as st
import pandas as pd

st.title("単語テスト")

df = pd.read_csv("tangocho.csv")

num = 0
row = df.iloc[num]
jp = row[df.columns[0]]
en = row[df.columns[1]]

st.write(f"{jp}({en[0]}-)：")

answer = st.text_input(
    "英語を入力してください",
    key="answer_input"
)

if st.button("判定"):
    if answer.strip() == "":
        st.warning("英語を入力してください")
    elif answer.strip().lower() == str(en).lower():
        st.success("○ 正解")
    else:
        st.error(f"× 不正解（正解：{en}）")
    num+=1
