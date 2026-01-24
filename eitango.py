import streamlit as st
import pandas as pd
import random

# =====================
# iPhone向けUI調整
# =====================
st.markdown("""
<style>
button {
    font-size: 20px !important;
    height: 60px !important;
}
input {
    font-size: 20px !important;
}
</style>
""", unsafe_allow_html=True)

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

    with st.form("title_form"):
        start = st.form_submit_button("スタート", use_container_width=True)

    if start:
        st.session_state.screen = "select"
        st.rerun()


# =====================
# 問題選択画面
# =====================
elif st.session_state.screen == "select":
    st.title("📂 問題選択")

    with st.form("select_form"):
        set_no = st.selectbox(
            "何セット目をやりますか？",
            list(range(1, NUM_SETS + 1))
        )

        question_count = st.selectbox(
            "問題数を選んでください",
            [5, 10, 20, 30],
            index=1
        )

        start = st.form_submit_button("開始", use_container_width=True)

    if start:
        st.session_state.set_index = set_no - 1
        st.session_state.question_count = question_count
        st.session_state.num = 0
        st.session_state.judged = False

        # ===== ランダム問題リスト作成 =====
        start_row = st.session_state.set_index * SET_SIZE
        end_row = min(start_row + SET_SIZE, TOTAL)

        all_indices = list(range(start_row, end_row))
        st.session_state.question_indices = random.sample(
            all_indices,
            k=min(question_count, len(all_indices))
        )

        st.session_state.screen = "quiz"
        st.session_state.pop("answer_input", None)
        st.rerun()


# =====================
# 回答画面（判定 → 次へ方式）
# =====================
elif st.session_state.screen == "quiz":

    if "judged" not in st.session_state:
        st.session_state.judged = False

    questions = st.session_state.question_indices
    num = st.session_state.num

    if num >= len(questions):
        st.success("🎉 このセットは終了です！")
        if st.button("問題選択へ戻る"):
            st.session_state.screen = "select"
            st.rerun()
        st.stop()

    index = questions[num]

    row = df.iloc[index]
    jp = row[df.columns[2]]
    en = str(row[df.columns[1]])

    st.title("✏️ 単語テスト")
    st.write(f"問題 {num + 1} / {len(questions)}")

    st.subheader(jp)
    st.write(f"ヒント：{en[0]}-")

    # ===== formは1つ =====
    with st.form("quiz_form", clear_on_submit=True):
        answer = st.text_input("英語を入力してください")

        if not st.session_state.judged:
            submit = st.form_submit_button("判定", use_container_width=True)
            next_btn = False
        else:
            submit = False
            next_btn = st.form_submit_button("次へ", use_container_width=True)
            if st.session_state.judged == "correct":
                st.success(f"正解   答え：{en}")
            elif st.session_state.judged == "wrong":
                st.error(f"不正解   答え：{en}")

    # ===== 判定フェーズ =====
    if submit:
        if answer.strip() == "":
            st.warning("英語を入力してください")
        elif answer.lower() == en.lower():
            st.session_state.judged = "correct"
            st.rerun()
        else:
            st.session_state.judged = "wrong"
            st.rerun()

    # ===== 次へフェーズ =====
    if next_btn:
        st.session_state.num += 1
        st.session_state.judged = False
        st.rerun()
