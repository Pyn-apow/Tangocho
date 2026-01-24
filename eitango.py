import streamlit as st
from supabase import create_client, Client
import random

# =====================
# Supabase 設定
# =====================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]                   # あなたの anon key
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================
# Streamlit セッション初期化
# =====================
defaults = {
    "screen": "title",
    "num": 0,
    "question_indices": [],
    "question_count": 10,
    "mode": "全単語",
    "current_questions": [],
    "judged": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# =====================
# 学習度・習得率取得
# =====================
def get_progress_rate():
    res = supabase.table("words").select("progression").execute()
    data = res.data
    if not data:
        return 0, 0
    learned = sum(1 for w in data if w["progression"] == 2)
    return learned, len(data)

learned, total = get_progress_rate()
rate = learned / total if total else 0
st.sidebar.markdown("### 📊 学習状況")
st.sidebar.progress(rate)
st.sidebar.write(f"習得済み：{learned} / {total} ({int(rate*100)}%)")

# =====================
# タイトル画面
# =====================
if st.session_state.screen == "title":
    st.title("📘 単語テスト")
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
        question_count = st.selectbox("問題数", [5, 10, 20, 30], index=1)
        mode = st.selectbox("出題範囲", ["全単語", "未習得語", "my単語"])
        start = st.form_submit_button("開始", use_container_width=True)

    if start:
        st.session_state.question_count = question_count
        st.session_state.mode = mode
        st.session_state.num = 0
        st.session_state.judged = None

        # Supabase から出題条件に応じて取得
        query = supabase.table("words").select("id,jp,en,progression,my")
        if mode == "未習得語":
            query = query.lt("progression", 2)
        elif mode == "my単語":
            query = query.eq("my", True)
        res = query.execute()
        questions = res.data or []

        if not questions:
            st.warning("条件に合う単語がありません。")
            st.stop()

        # ランダムに抽出
        st.session_state.current_questions = random.sample(
            questions, k=min(question_count, len(questions))
        )
        st.session_state.screen = "quiz"
        st.rerun()

# =====================
# クイズ画面
# =====================
elif st.session_state.screen == "quiz":
    n = st.session_state.num
    questions = st.session_state.current_questions

    if n >= len(questions):
        st.success("🎉 このセットは終了！")
        if st.button("問題選択へ戻る", use_container_width=True):
            st.session_state.screen = "select"
            st.rerun()
        st.stop()

    q = questions[n]
    st.title("✏️ 単語テスト")
    st.write(f"問題 {n+1}/{len(questions)}")
    st.subheader(q["jp"])
    st.write(f"ヒント：{q['en'][0]}-")

    # ===== 入力 =====
    answer = st.text_input("英語を入力してください", key=f"answer_{q['id']}")

    # ===== 判定 =====
    if st.session_state.judged is None:
        if st.button("判定", use_container_width=True):
            if answer.strip() == "":
                st.warning("英語を入力してください")
            elif answer.lower() == q["en"].lower():
                new_prog = min(q["progression"] + 1, 2)
                supabase.table("words").update({"progression": new_prog}).eq("id", q["id"]).execute()
                st.session_state.judged = "correct"
                st.rerun()
            else:
                supabase.table("words").update({"progression": 0}).eq("id", q["id"]).execute()
                st.session_state.judged = "wrong"
                st.rerun()

    # ===== 結果表示 & My単語 =====
    else:
        if st.session_state.judged == "correct":
            st.success(f"正解！ 答え：{q['en']}")
        else:
            st.error(f"不正解… 答え：{q['en']}")

        my = st.checkbox("⭐ My単語に追加", value=q["my"], key=f"my_{q['id']}")
        supabase.table("words").update({"my": my}).eq("id", q["id"]).execute()

        if st.button("次へ", use_container_width=True):
            st.session_state.num += 1
            st.session_state.judged = None
            st.rerun()
