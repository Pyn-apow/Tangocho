import streamlit as st
from supabase import create_client, Client
import random
import math

# ===================== CSS（ボタン調整） =====================
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
        "set_index": None,
        "question_count": 5,
        "mode": "全単語",
        "current_questions": [],
        "user_answers": [],
        "num": 0,
        "judged": None,
    })

# ===================== 単語データ取得 =====================
@st.cache_data
def fetch_words():
    res = supabase.table("words").select("id,jp,en,mastery").order("id").execute()
    return res.data or []

words = fetch_words()
total_words = len(words)
TOTAL_SETS = math.ceil(total_words / 100)

# ===================== 進捗計算関数 =====================
def calc_progress(words):
    je_sum = 0
    ej_sum = 0
    for w in words:
        mastery = w["mastery"]
        je_sum += mastery % 10      # 日→英
        ej_sum += mastery // 10     # 英→日
    je_rate = je_sum / (len(words) * 2) if words else 0
    ej_rate = ej_sum / (len(words) * 2) if words else 0
    return je_rate, ej_rate

# ===================== 英日 総合進捗 =====================
_, ej_total_rate = calc_progress(words)

# ===================== サイドバー =====================
st.sidebar.markdown("## 📊 学習進捗")
st.sidebar.markdown("### 英 → 日（総合）")
st.sidebar.progress(ej_total_rate)
st.sidebar.write(f"{int(ej_total_rate * 100)} %")

# ===================== タイトル画面 =====================
if st.session_state.screen == "title":
    st.title("📘 単語学習")
    st.write("日→英クイズ / 英→日単語帳")
    if st.button("スタート", use_container_width=True):
        st.session_state.screen = "select"
        st.rerun()

# ===================== セット選択画面 =====================
elif st.session_state.screen == "select":
    st.title("📂 セット選択")

    cols = st.columns(4)
    for i in range(TOTAL_SETS):
        col = cols[i % 4]
        if col.button(f"セット {i+1}", key=f"set_{i}"):
            st.session_state.set_index = i
            st.session_state.screen = "quiz"
            st.rerun()

    st.markdown("---")
    st.markdown("## 📊 セット別進捗")

    for i in range(TOTAL_SETS):
        start = i * 100
        end = start + 100
        set_words = words[start:end]

        je_rate, ej_rate = calc_progress(set_words)

        st.markdown(f"### セット {i+1}")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("日 → 英")
            st.progress(je_rate)
            st.write(f"{int(je_rate * 100)} %")

        with col2:
            st.markdown("英 → 日")
            st.progress(ej_rate)
            st.write(f"{int(ej_rate * 100)} %")

# ===================== クイズ画面（日→英） =====================
elif st.session_state.screen == "quiz":
    start = st.session_state.set_index * 100
    end = start + 100
    questions = words[start:end]

    if not st.session_state.current_questions:
        st.session_state.current_questions = random.sample(
            questions, k=min(st.session_state.question_count, len(questions))
        )
        st.session_state.user_answers = []
        st.session_state.num = 0
        st.session_state.judged = None

    n = st.session_state.num

    if n >= len(st.session_state.current_questions):
        st.session_state.screen = "finish"
        st.rerun()

    q = st.session_state.current_questions[n]

    st.title("✏️ 日 → 英 クイズ")
    st.write(f"問題 {n+1} / {len(st.session_state.current_questions)}")
    st.subheader(q["jp"])

    while len(st.session_state.user_answers) <= n:
        st.session_state.user_answers.append("")

    answer = st.text_input(
        "英語を入力",
        value=st.session_state.user_answers[n],
        key=f"answer_{n}"
    )

    if st.button("判定", use_container_width=True):
        st.session_state.user_answers[n] = answer
        st.session_state.judged = (answer.lower() == q["en"].lower())
        st.rerun()

    if st.session_state.judged is not None:
        if st.session_state.judged:
            st.success(f"正解！ {q['en']}")
        else:
            st.error(f"不正解… 正解：{q['en']}")

        if st.button("次へ", use_container_width=True):
            st.session_state.num += 1
            st.session_state.judged = None
            st.rerun()

# ===================== 終了画面 =====================
elif st.session_state.screen == "finish":
    st.success("🎉 セット終了")
    if st.button("セット選択へ戻る", use_container_width=True):
        st.session_state.current_questions = []
        st.session_state.screen = "select"
        st.rerun()
