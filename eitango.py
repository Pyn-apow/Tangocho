import streamlit as st
from supabase import create_client, Client
import random

# ===================== Supabase 設定 =====================
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ===================== セッション初期化 =====================
if "screen" not in st.session_state:
    st.session_state.update({
        "screen": "title",
        "set_index": 0,
        "num": 0,
        "question_count": 10,
        "mode": "全単語",
        "current_questions": [],
        "user_answers": [],   # ユーザーの回答を保持
        "user_my_flags": [],  # My単語チェックを保持
        "questions_cache": {},  # セットキャッシュ
        "progress_cache": None, # 総学習状況キャッシュ
    })

# ===================== 総単語数と学習率 =====================
if st.session_state.progress_cache is None:
    learned, total = 0, 0
    offset = 0
    limit = 1000
    while True:
        res = supabase.table("words").select("progression").range(offset, offset + limit - 1).execute()
        data = res.data or []
        if not data:
            break
        learned += sum(1 for w in data if w["progression"] == 2)
        total += len(data)
        if len(data) < limit:
            break
        offset += limit
    st.session_state.progress_cache = (learned, total)
else:
    learned, total = st.session_state.progress_cache

rate = learned / total if total else 0
st.sidebar.markdown("### 📊 学習状況")
st.sidebar.progress(rate)
st.sidebar.write(f"習得済み：{learned} / {total} ({int(rate*100)}%)")

# ===================== タイトル画面 =====================
if st.session_state.screen == "title":
    st.title("📘 単語テスト")
    if st.button("スタート", use_container_width=True):
        st.session_state.screen = "select"
        st.rerun()

# ===================== 問題選択画面 =====================
elif st.session_state.screen == "select":
    st.title("📂 問題選択")
    TOTAL_SETS = (total - 1) // 100 + 1
    set_no = st.selectbox("セット（100語ごと）", list(range(1, TOTAL_SETS + 1)))
    question_count = st.selectbox("問題数", [5, 10, 20, 30], index=1)
    mode = st.selectbox("出題範囲", ["全単語", "未習得語", "my単語"])
    
    if st.button("開始", use_container_width=True):
        st.session_state.set_index = set_no - 1
        st.session_state.question_count = question_count
        st.session_state.mode = mode
        st.session_state.num = 0
        st.session_state.user_answers = []
        st.session_state.user_my_flags = []

        # キャッシュ確認
        cache_key = f"set_{set_no}_{mode}"
        if cache_key in st.session_state.questions_cache:
            questions_in_set = st.session_state.questions_cache[cache_key]
        else:
            start_id = st.session_state.set_index * 100
            end_id = start_id + 99
            query = supabase.table("words").select("id,jp,en,progression,my").gte("id", start_id).lte("id", end_id)
            if mode == "未習得語":
                query = query.lt("progression", 2)
            elif mode == "my単語":
                query = query.eq("my", True)
            res = query.execute()
            questions_in_set = res.data or []
            st.session_state.questions_cache[cache_key] = questions_in_set

        if not questions_in_set:
            st.warning("条件に合う単語がありません。")
            st.stop()

        st.session_state.current_questions = random.sample(
            questions_in_set, k=min(question_count, len(questions_in_set))
        )
        st.session_state.screen = "quiz"
        st.rerun()

# ===================== クイズ画面 =====================
elif st.session_state.screen == "quiz":
    n = st.session_state.num
    questions = st.session_state.current_questions

    if n >= len(questions):
        st.success("🎉 このセットは終了！")

        # セット終了時にまとめてDB更新
        updates = []
        for q, answer, my_flag in zip(questions, st.session_state.user_answers, st.session_state.user_my_flags):
            # progression更新
            if answer.lower() == q["en"].lower():
                new_prog = min(q["progression"] + 1, 2)
            else:
                new_prog = 0
            updates.append({"id": q["id"], "progression": new_prog, "my": my_flag})

        for u in updates:
            supabase.table("words").update({"progression": u["progression"], "my": u["my"]}).eq("id", u["id"]).execute()

        if st.button("問題選択へ戻る", use_container_width=True):
            st.session_state.screen = "select"
            st.rerun()
        st.stop()

    q = questions[n]
    st.title("✏️ 単語テスト")
    st.write(f"問題 {n+1}/{len(questions)}")
    st.subheader(q["jp"])
    st.write(f"ヒント：{q['en'][0]}-")

    # 判定状態
    if "judged" not in st.session_state or len(st.session_state.user_answers) <= n:
        st.session_state.judged = None

    # ===== 入力フォーム =====
    if st.session_state.judged is None:
        with st.form(f"quiz_form_{q['id']}"):
            answer = st.text_input("英語を入力してください")
            my = st.checkbox("⭐ My単語に追加", value=q["my"])
            submit = st.form_submit_button("判定")
            if submit:
                if answer.strip() == "":
                    st.warning("英語を入力してください")
                else:
                    st.session_state.user_answers.append(answer)
                    st.session_state.user_my_flags.append(my)
                    if answer.lower() == q["en"].lower():
                        st.session_state.judged = "correct"
                    else:
                        st.session_state.judged = "wrong"
                    st.rerun()

    # ===== 結果表示 & 次へ =====
    if st.session_state.judged is not None:
        if st.session_state.judged == "correct":
            st.success(f"正解！ 答え：{q['en']}")
        else:
            st.error(f"不正解… 答え：{q['en']} (あなたの答え: {st.session_state.user_answers[n]}) )")

        if st.button("次へ", use_container_width=True):
            st.session_state.num += 1
            st.session_state.judged = None
            st.rerun()
