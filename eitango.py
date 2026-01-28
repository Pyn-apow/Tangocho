import streamlit as st
from supabase import create_client, Client
import random

# ===================== CSS =====================
st.markdown("""
<style>
div[data-testid="stButton"] > button {
    height: 3.2em;
    font-size: 1.1em;
    padding: 0.2em 0.6em;
}
</style>
""", unsafe_allow_html=True)

# ===================== Supabase 設定 =====================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===================== セッション初期化 =====================
if "screen" not in st.session_state:
    st.session_state.update({
        "screen": "title",
        "step": "select_set",
        "set_index": None,
        "mode": "全単語",
        "quiz_mode": "日英クイズ",  # ← 追加
        "question_count": 5,
        "current_questions": [],
        "num": 0,
        "judged": None,
        "user_answers": [],
        "user_my_flags": [],
        "card_flipped": False,
        "enjp_streak": 0,
        "questions_cache": {},
        "progress_cache": None,
    })

# ===================== 学習状況 =====================
if st.session_state.progress_cache is None:
    learned, total = 0, 0
    offset = 0
    limit = 1000
    while True:
        res = supabase.table("words").select("progression").range(offset, offset+limit-1).execute()
        data = res.data or []
        if not data:
            break
        learned += sum(1 for w in data if w["progression"] % 10 == 2)
        total += len(data)
        offset += limit
    st.session_state.progress_cache = (learned, total)
else:
    learned, total = st.session_state.progress_cache

st.sidebar.progress(learned / total if total else 0)
st.sidebar.write(f"{learned}/{total}")

# ===================== タイトル =====================
if st.session_state.screen == "title":
    st.title("📘 単語学習")
    if st.button("スタート", use_container_width=True):
        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()

# ===================== 選択画面 =====================
elif st.session_state.screen == "select":
    TOTAL_SETS = (total - 1) // 100 + 1

    if st.session_state.step == "select_set":
        st.write("### セット選択")
        cols = st.columns(4)
        for i in range(TOTAL_SETS):
            if cols[i % 4].button(f"{i+1}セット", key=f"set_{i}"):
                st.session_state.set_index = i
                st.session_state.step = "select_config"
                st.rerun()

    elif st.session_state.step == "select_config":
        st.write(f"### セット {st.session_state.set_index+1}")

        # ---- 出題モード ----
        st.write("#### モード")
        qm_cols = st.columns(2)
        for i, m in enumerate(["日英クイズ", "英日単語帳"]):
            label = m + (" (選択中)" if st.session_state.quiz_mode == m else "")
            if qm_cols[i].button(label, key=f"qm_{m}"):
                st.session_state.quiz_mode = m
                st.rerun()

        # ---- 出題形式 ----
        st.write("#### 出題形式")
        mode_cols = st.columns(3)
        for i, m in enumerate(["全単語", "未習得語", "my単語"]):
            label = m + (" (選択中)" if st.session_state.mode == m else "")
            if mode_cols[i].button(label, key=f"mode_{m}"):
                st.session_state.mode = m
                st.rerun()

        # ---- 問題数 ----
        st.write("#### 問題数")
        cnt_cols = st.columns(4)
        for i, c in enumerate([3, 5, 10, 20]):
            label = str(c) + (" (選択中)" if st.session_state.question_count == c else "")
            if cnt_cols[i].button(label, key=f"cnt_{c}"):
                st.session_state.question_count = c
                st.rerun()

        if st.button("開始", use_container_width=True):
            start_id = st.session_state.set_index * 100
            end_id = start_id + 99
            query = supabase.table("words").select("id,jp,en,progression,my").gte("id", start_id).lte("id", end_id)
            if st.session_state.mode == "未習得語":
                query = query.lt("progression", 2)
            elif st.session_state.mode == "my単語":
                query = query.eq("my", True)

            words = query.execute().data or []
            st.session_state.current_questions = random.sample(words, min(len(words), st.session_state.question_count))
            st.session_state.num = 0
            st.session_state.card_flipped = False
            st.session_state.enjp_streak = 0
            st.session_state.screen = "quiz" if st.session_state.quiz_mode == "日英クイズ" else "wordbook"
            st.rerun()

# ===================== 日英クイズ（既存） =====================
elif st.session_state.screen == "quiz":
    q = st.session_state.current_questions[st.session_state.num]
    st.subheader(q["jp"])
    ans = st.text_input("英語を入力")
    if st.button("判定"):
        correct = ans.lower() == q["en"].lower()
        prog = min((q["progression"] % 10) + (1 if correct else 0), 2)
        supabase.table("words").update({"progression": (q["progression"] // 10)*10 + prog}).eq("id", q["id"]).execute()
        st.session_state.num += 1
        st.rerun()

# ===================== 英日単語帳 =====================
elif st.session_state.screen == "wordbook":
    q = st.session_state.current_questions[st.session_state.num]
    text = q["jp"] if st.session_state.card_flipped else q["en"]

    if st.button("カード", use_container_width=True):
        st.session_state.card_flipped = not st.session_state.card_flipped
        st.rerun()

    st.markdown(f"<div style='text-align:center;font-size:2.2em'>{text}</div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    if c1.button("⬅ 不正解", use_container_width=True):
        st.session_state.enjp_streak = 0
        st.session_state.card_flipped = False
        st.session_state.num += 1
        st.rerun()

    if c2.button("➡ 正解", use_container_width=True):
        st.session_state.enjp_streak += 1
        level = 20 if st.session_state.enjp_streak >= 2 else 10
        supabase.table("words").update({"progression": level + (q["progression"] % 10)}).eq("id", q["id"]).execute()
        st.session_state.card_flipped = False
        st.session_state.num += 1
        st.rerun()
