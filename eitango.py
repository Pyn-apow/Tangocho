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
        "set_index": None,
        "study_mode": "日英クイズ",
        "question_count": 5,
        "mode": "全単語",
        "current_questions": [],
        "user_answers": [],
        "user_my_flags": [],
        "questions_cache": {},
        "progress_cache": None,
        "num": 0,
        "card_flipped": False,   # 単語カードが裏返っているか
        "judged": None,
        "step": "select_set"  # セット選択か出題設定か
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
    st.title("📘 英検準1級単語")
    if st.button("スタート", use_container_width=True):
        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()

# ===================== セット選択画面 =====================
elif st.session_state.screen == "select":
    st.title("📂 問題選択")

    TOTAL_SETS = (total - 1) // 100 + 1

    if st.session_state.step == "select_set":
        st.write("### セットを選択")
        cols = st.columns(min(TOTAL_SETS, 4))  # 横に最大4列
        for i in range(TOTAL_SETS):
            col = cols[i % 4]
            if col.button(f"{i+1}セット", key=f"set_{i}"):
                st.session_state.set_index = i
                st.session_state.step = "select_config"
                st.rerun()

    elif st.session_state.step == "select_config":
        st.write(f"### セット {st.session_state.set_index+1} を選択しました")

        st.write("#### 学習モード")
        study_modes = ["日英クイズ", "英日単語帳"]
        study_cols = st.columns(len(study_modes))
        for i, sm in enumerate(study_modes):
            label = sm + (" (選択中)" if st.session_state.study_mode == sm else "")
            if study_cols[i].button(label, key=f"study_{sm}"):
                st.session_state.study_mode = sm
                st.rerun()
            
        # 出題形式ボタン
        st.write("#### 出題形式")
        mode_options = ["全単語", "未習得語", "my単語"]
        mode_cols = st.columns(len(mode_options))
        for i, m in enumerate(mode_options):
            label = m + (" (選択中)" if st.session_state.mode == m else "")
            if mode_cols[i].button(label, key=f"mode_{m}"):
                st.session_state.mode = m
                st.rerun()  # 選択を即反映

        # 問題数ボタン
        st.write("#### 問題数")
        count_options = [3,5,10,20]
        count_cols = st.columns(len(count_options))
        for i, c in enumerate(count_options):
            label = str(c) + (" (選択中)" if st.session_state.question_count == c else "")
            if count_cols[i].button(label, key=f"count_{c}"):
                st.session_state.question_count = c
                st.rerun()  # 選択を即反映

        # 開始ボタン
        if st.button("開始", use_container_width=True):
            st.session_state.num = 0
            st.session_state.user_answers = []
            st.session_state.user_my_flags = []

            # 問題取得（キャッシュ使用）
            cache_key = f"set_{st.session_state.set_index+1}_{st.session_state.mode}"
            if cache_key in st.session_state.questions_cache:
                questions_in_set = st.session_state.questions_cache[cache_key]
            else:
                start_id = st.session_state.set_index * 100
                end_id = start_id + 99
                query = supabase.table("words").select("id,jp,en,progression,my").gte("id", start_id).lte("id", end_id)
                if st.session_state.mode == "未習得語":
                    query = query.lt("progression", 2)
                elif st.session_state.mode == "my単語":
                    query = query.eq("my", True)
                res = query.execute()
                questions_in_set = res.data or []
                st.session_state.questions_cache[cache_key] = questions_in_set

            if not questions_in_set:
                st.warning("条件に合う単語がありません。")
                st.stop()

            st.session_state.current_questions = random.sample(
                questions_in_set, k=min(st.session_state.question_count, len(questions_in_set))
            )
            if st.session_state.study_mode == "英日単語帳":
                st.session_state.screen = "card"   # 単語帳
            else:
                st.session_state.screen = "quiz"   # 日英クイズ
            st.rerun()


# ===================== クイズ画面 =====================
elif st.session_state.screen == "quiz":
    questions = st.session_state.current_questions
    n = st.session_state.num

    if n >= len(questions):
        st.session_state.screen = "finish"
        st.rerun()

    q = questions[n]
    st.title("✏️ 単語テスト")
    st.write(f"問題 {n+1}/{len(questions)}")
    st.subheader(q["jp"])
    st.write(f"ヒント：{q['en'][0]}-")

    while len(st.session_state.user_answers) <= n:
        st.session_state.user_answers.append("")
    while len(st.session_state.user_my_flags) <= n:
        st.session_state.user_my_flags.append(q["my"])

    with st.form(f"quiz_form_{q['id']}"):
        answer = st.text_input("英語を入力してください", value=st.session_state.user_answers[n])
        my = st.checkbox("⭐ My単語に追加", value=st.session_state.user_my_flags[n])
        submit = st.form_submit_button("判定")

        if submit:
            st.session_state.user_answers[n] = answer
            st.session_state.user_my_flags[n] = my
            st.session_state.judged = "correct" if answer.lower() == q["en"].lower() else "wrong"
            st.rerun()

    if st.session_state.judged is not None:
        if st.session_state.judged == "correct":
            st.success(f"正解！ 答え：{q['en']}")
        else:
            st.error(f"不正解… 答え：{q['en']} (あなたの答え: {st.session_state.user_answers[n]}) )")

        if st.button("次へ", use_container_width=True):
            st.session_state.num += 1
            st.session_state.judged = None
            st.rerun()

# ===================== 英日単語帳画面 =====================
elif st.session_state.screen == "card":
    questions = st.session_state.current_questions
    n = st.session_state.num

    if n >= len(questions):
        st.session_state.screen = "finish"
        st.rerun()

    q = questions[n]

    st.title("📖 英日単語帳")
    st.write(f"{n+1} / {len(questions)}")

    # --- カード表示 ---
    card_text = q["jp"] if st.session_state.card_flipped else q["en"]

    if st.button(card_text, use_container_width=True):
        st.session_state.card_flipped = not st.session_state.card_flipped
        st.rerun()

    st.markdown("※ タップで反転")

    st.divider()

    # --- 判定ボタン ---
    col1, col2 = st.columns(2)

    with col1:
        if st.button("❌ 不正解", use_container_width=True):
            # 英日用 progression（十の位）
            new_prog = (q["progression"] // 10) * 10
            supabase.table("words").update({
                "progression": new_prog
            }).eq("id", q["id"]).execute()

            st.session_state.num += 1
            st.session_state.card_flipped = False
            st.rerun()

    with col2:
        if st.button("⭕ 正解", use_container_width=True):
            prog = q["progression"] // 10
            prog = min(prog + 1, 2)
            new_prog = prog * 10 + (q["progression"] % 10)

            supabase.table("words").update({
                "progression": new_prog
            }).eq("id", q["id"]).execute()

            st.session_state.num += 1
            st.session_state.card_flipped = False
            st.rerun()


# ===================== セット終了画面 =====================
elif st.session_state.screen == "finish":
    st.success("🎉 このセットは終了！")
    st.write("今回の結果まとめ：")

    questions = st.session_state.current_questions
    for i, (q, answer, my_flag) in enumerate(zip(questions, st.session_state.user_answers, st.session_state.user_my_flags)):
        col1, col2, col3, col4 = st.columns([0.5, 2.5, 2, 1])
        with col1:
            st.markdown("✅" if answer.lower() == q["en"].lower() else "❌")
        with col2:
            st.write(q["jp"])
        with col3:
            new_prog = min(q["progression"] + 1, 2) if answer.lower() == q["en"].lower() else 0
            progress_rate = 0.5 if new_prog == 1 else 1.0 if new_prog == 2 else 0.0
            st.progress(progress_rate)
        with col4:
            my = st.checkbox("⭐", value=my_flag, key=f"my_finish_{q['id']}")
            st.session_state.user_my_flags[i] = my

    if st.button("DBに反映して問題選択へ戻る", use_container_width=True):
        updates = []
        for q, answer, my_flag in zip(questions, st.session_state.user_answers, st.session_state.user_my_flags):
            new_prog = min(q["progression"] + 1, 2) if answer.lower() == q["en"].lower() else 0
            updates.append({"id": q["id"], "progression": new_prog, "my": my_flag})

        for u in updates:
            supabase.table("words").update({"progression": u["progression"], "my": u["my"]}).eq("id", u["id"]).execute()

        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()
