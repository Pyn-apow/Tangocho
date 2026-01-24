import streamlit as st
import pandas as pd

# =====================
# 初期化
# =====================
if "screen" not in st.session_state:
    st.session_state.screen = "title"

if "set_index" not in st.session_state:
    st.session_state.set_index = 0

if "num" not in st.session_state:
    st.session_state.num = 0

# =====================
# CSV 読み込み
# =====================
df = pd.read_csv("tangocho.csv")
TOTAL = len(df)
SET_SIZE = 100
NUM_SETS = (TOTAL - 1) // SET_SIZE + 1


# =====================
# タイトル画面
# =====================
if st.session_state.screen == "title":
    st.title("📘 単語テスト")

    st.write("英単語テストへようこそ")

    if st.button("スタート"):
        st.session_state.screen = "select"


# =====================
# 問題選択画面（100問ごと）
# =====================
elif st.session_state.screen == "select":
    st.title("📂 問題選択")

    set_no = st.selectbox(
        "何セット目をやりますか？",
        list(range(1, NUM_SETS + 1))
    )

    if st.button("開始"):
        st.session_state.set_index = set_no - 1
        st.session_state.num = 0
        st.session_state.screen = "quiz"
        st.session_state.answer_input = ""


# =====================
# 回答画面
# =====================
elif st.session_state.screen == "quiz":
    start = st.session_state.set_index * SET_SIZE
    index = start + st.session_state.num

    if index >= min(start + SET_SIZE, TOTAL):
        st.success("🎉 このセットは終了です！")
        if st.button("問題選択へ戻る"):
            st.session_state.screen = "select"
        st.stop()

    row = df.iloc[index]
    jp = row[df.columns[2]]
    en = str(row[df.columns[1]])

    st.title("✏️ 単語テスト")
    st.write(f"問題 {st.session_state.num + 1} / 100")
    st.subheader(f"{jp}（{en[0]}-）")

    answer = st.text_input(
        "英語を入力してください",
        key="answer_input"
    )

    if st.button("判定"):
        if answer.strip() == "":
            st.warning("英語を入力してください")
        elif answer.strip().lower() == en.lower():
            st.success("○ 正解")
            st.session_state.num += 1
            st.session_state.answer_input = ""
        else:
            st.error(f"× 不正解（正解：{en}）")

    if st.button("中断して戻る"):
        st.session_state.screen = "select"
