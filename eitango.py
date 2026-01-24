import streamlit as st
import pandas as pd
import random

CSV_PATH = "tangocho.csv"

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
defaults = {
    "screen": "title",
    "set_index": 0,
    "num": 0,
    "judged": None,
    "question_indices": [],
    "question_count": 10,
    "mode": "全単語"
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================
# CSV 読み込み
# =====================
df = pd.read_csv(CSV_PATH)

TOTAL = len(df)
SET_SIZE = 100
NUM_SETS = (TOTAL - 1) // SET_SIZE + 1

# =====================
# 学習度・習得率表示
# =====================
learned = (df["progression"] == 2).sum()
progress_rate = learned / TOTAL if TOTAL else 0

st.sidebar.markdown("### 📊 学習状況")
st.sidebar.progress(progress_rate)
st.sidebar.write(f"習得済み：{learned} / {TOTAL}（{int(progress_rate*100)}%）")

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
        set_no = st.selectbox("セット（100語ごと）", list(range(1, NUM_SETS + 1)))
        question_count = st.selectbox("問題数", [5, 10, 20, 30], index=1)
        mode = st.selectbox("出題範囲", ["全単語", "未習得語", "my単語"])
        start = st.form_submit_button("開始", use_container_width=True)

    if start:
        st.session_state.set_index = set_no - 1
        st.session_state.question_count = question_count
        st.session_state.mode = mode
        st.session_state.num = 0
        st.session_state.judged = None

        start_row = st.session_state.set_index * SET_SIZE
        end_row = min(start_row + SET_SIZE, TOTAL)
        subset = df.iloc[start_row:end_row]

        if mode == "未習得語":
            subset = subset[subset["progression"] < 2]
        elif mode == "my単語":
            subset = subset[subset["my"] == 1]

        indices = subset.index.tolist()

        st.session_state.question_indices = random.sample(
            indices, k=min(question_count, len(indices))
        )

        st.session_state.screen = "quiz"
        st.rerun()

# =====================
# 回答入力画面
# =====================
elif st.session_state.screen == "quiz":

    questions = st.session_state.question_indices
    num = st.session_state.num

    if num >= len(questions):
        st.success("🎉 このセットは終了です！")
        if st.button("問題選択へ戻る", use_container_width=True):
            st.session_state.screen = "select"
            st.rerun()
        st.stop()

    index = questions[num]
    row = df.loc[index]

    jp = row["jp"]
    en = str(row["en"])

    st.title("✏️ 単語テスト")
    st.write(f"問題 {num + 1} / {len(questions)}")
    st.subheader(jp)
    st.write(f"ヒント：{en[0]}-")

    with st.form("quiz_form"):
        answer = st.text_input("英語を入力してください", key="answer_input")
        submit = st.form_submit_button("判定", use_container_width=True)

    if submit:
        if answer.strip() == "":
            st.warning("英語を入力してください")
            st.stop()

        if answer.lower() == en.lower():
            df.at[index, "progression"] = min(2, df.at[index, "progression"] + 1)
            st.session_state.judged = "correct"
        else:
            df.at[index, "progression"] = 0
            st.session_state.judged = "wrong"

        df.to_csv(CSV_PATH, index=False)

        st.session_state.screen = "result"
        st.rerun()

# =====================
# 結果表示画面
# =====================
elif st.session_state.screen == "result":

    index = st.session_state.question_indices[st.session_state.num]
    en = str(df.at[index, "en"])

    if st.session_state.judged == "correct":
        st.success(f"正解！ 答え：{en}")
    else:
        st.error(f"不正解… 答え：{en}")

    my = st.checkbox(
        "⭐ My単語に追加",
        value=bool(df.at[index, "my"]),
        key=f"my_{index}"
    )

    df.at[index, "my"] = 1 if my else 0
    df.to_csv(CSV_PATH, index=False)

    if st.button("次へ", use_container_width=True):
        st.session_state.num += 1
        st.session_state.judged = None
        st.session_state.pop("answer_input", None)
        st.session_state.screen = "quiz"
        st.rerun()
