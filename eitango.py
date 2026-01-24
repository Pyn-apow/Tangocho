import streamlit as st
import pandas as pd

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
        start = st.form_submit_button("開始", use_container_width=True)

    if start:
        st.session_state.set_index = set_no - 1
        st.session_state.num = 0
        st.session_state.screen = "quiz"
        st.session_state.pop("answer_input", None)
        st.rerun()

# =====================
# 回答画面（判定 → 次へ方式）
# =====================
elif st.session_state.screen == "quiz":

    if "judged" not in st.session_state:
        st.session_state.judged = False

    start = st.session_state.set_index * SET_SIZE
    index = start + st.session_state.num

    if index >= min(start + SET_SIZE, TOTAL):
        st.success("🎉 このセットは終了です！")
        if st.button("問題選択へ戻る"):
            st.session_state.screen = "select"
            st.rerun()
        st.stop()

    row = df.iloc[index]
    jp = row[df.columns[2]]
    en = str(row[df.columns[1]])

    st.title("✏️ 単語テスト")
    st.write(f"問題 {st.session_state.num + 1} / 100")
    st.subheader(jp)
    st.write(f"ヒント：{en[0]}-")

    # ===== フォーム（ボタンは1つ）=====
    with st.form("quiz_form"):
        answer = st.text_input(
            "英語を入力してください",
            key="answer_input"
        )

        submit = st.form_submit_button(
            "判定" if not st.session_state.judged else "次へ",
            use_container_width=True
        )

    # ===== ボタン処理 =====
    if submit:
        # --- 判定フェーズ ---
        if not st.session_state.judged:
            if answer.strip() == "":
                st.warning("英語を入力してください")
            elif answer.lower() == en.lower():
                st.success("○ 正解")
                st.info(f"答え：{en}")
                st.session_state.judged = True
            else:
                st.error("× 不正解")
                st.info(f"答え：{en}")
                st.session_state.judged = True

        # --- 次へフェーズ ---
        else:
            st.session_state.num += 1
            st.session_state.judged = False
            st.session_state.answer_input = ""
            st.rerun()