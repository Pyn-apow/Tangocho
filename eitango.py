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
        "question_count": 10,
        "mode": "全単語",
        "current_questions": [],
        "user_answers": [],
        "user_my_flags": [],
        "questions_cache": {},
        "set_stats_cache": None,
        "num": 0,
        "card_flipped": False,
        "judged": None,
        "step": "select_set"
    })
if "card_results" not in st.session_state:
    st.session_state.card_results = []

# ===================== データ集計関数 =====================
def get_progress_data():
    """全単語を取得してセットごとの進捗を計算する（キャッシュ対応）"""
    if st.session_state.set_stats_cache is not None:
        return st.session_state.set_stats_cache

    stats = {}
    total_learned1, total_learned2, total_count = 0, 0, 0
    offset = 0
    limit = 1000
    
    while True:
        res = supabase.table("words").select("id, progression").range(offset, offset + limit - 1).execute()
        data = res.data or []
        if not data:
            break
        
        for w in data:
            s_idx = w["id"] // 100  # 100単位でセット化
            if s_idx not in stats:
                stats[s_idx] = {"learned1": 0, "learned2": 0, "total": 0}
            
            stats[s_idx]["total"] += 1
            total_count += 1
            
            if w["progression"] % 10 == 2:
                stats[s_idx]["learned1"] += 1
                total_learned1 += 1
            if w["progression"] // 10 == 2:
                stats[s_idx]["learned2"] += 1
                total_learned2 += 1
                
        if len(data) < limit:
            break
        offset += limit
    
    result = {
        "sets": stats,
        "total_count": total_count,
        "total_learned1": total_learned1,
        "total_learned2": total_learned2
    }
    st.session_state.set_stats_cache = result
    return result

# 進捗データの取得
progress_data = get_progress_data()

# ===================== サイドバー表示 =====================
rate1 = progress_data["total_learned1"] / progress_data["total_count"] if progress_data["total_count"] else 0
rate2 = progress_data["total_learned2"] / progress_data["total_count"] if progress_data["total_count"] else 0

st.sidebar.markdown("### 📊 総学習状況")
st.sidebar.caption(f"日英習得：{progress_data['total_learned1']} / {progress_data['total_count']}")
st.sidebar.progress(rate1)
st.sidebar.caption(f"英日習得：{progress_data['total_learned2']} / {progress_data['total_count']}")
st.sidebar.progress(rate2)

if st.sidebar.button("データをリロード", use_container_width=True):
    st.session_state.set_stats_cache = None
    st.rerun()

# ===================== タイトル画面 =====================
if st.session_state.screen == "title":
    st.title("📘 英検準1級単語")
    st.write("継続は力なり。毎日少しずつ進めましょう。")
    if st.button("スタート", use_container_width=True, type="primary"):
        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()

# ===================== セット選択画面 =====================
elif st.session_state.screen == "select":
    if st.session_state.step == "select_set":
        st.title("📂 セット選択")
        
        # セットごとにカードを表示
        for i in sorted(progress_data["sets"].keys()):
            s = progress_data["sets"][i]
            p1 = s["learned1"] / s["total"] if s["total"] else 0
            p2 = s["learned2"] / s["total"] if s["total"] else 0
            
            with st.container(border=True):
                col1, col2 = st.columns([1, 1])
                with col1:
                    st.markdown(f"#### 📦 セット {i+1}")
                    st.caption(f"範囲: ID {i*100}〜")
                with col2:
                    st.caption(f"全 {s['total']} 単語")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(f"日英: {int(p1*100)}%")
                    st.progress(p1)
                with c2:
                    st.caption(f"英日: {int(p2*100)}%")
                    st.progress(p2)
                
                if st.button(f"セット {i+1} を選択", key=f"btn_{i}", use_container_width=True):
                    st.session_state.set_index = i
                    st.session_state.step = "select_config"
                    st.rerun()

    elif st.session_state.step == "select_config":
        st.title(f"⚙️ セット {st.session_state.set_index+1} 設定")
        
        # モード選択
        st.subheader("学習モード")
        cols = st.columns(2)
        if cols[0].button("日英クイズ" + (" ✅" if st.session_state.study_mode == "日英クイズ" else ""), use_container_width=True):
            st.session_state.study_mode = "日英クイズ"
            st.rerun()
        if cols[1].button("英日単語帳" + (" ✅" if st.session_state.study_mode == "英日単語帳" else ""), use_container_width=True):
            st.session_state.study_mode = "英日単語帳"
            st.rerun()

        # 出題形式
        st.subheader("出題形式")
        m_cols = st.columns(3)
        modes = ["全単語", "未習得語", "my単語"]
        for idx, m in enumerate(modes):
            if m_cols[idx].button(m + ("\n✅" if st.session_state.mode == m else ""), use_container_width=True):
                st.session_state.mode = m
                st.rerun()

        # 問題数
        st.subheader("問題数")
        c_cols = st.columns(4)
        counts = [5, 10, 20, 50]
        for idx, c in enumerate(counts):
            if c_cols[idx].button(str(c) + ("\n✅" if st.session_state.question_count == c else ""), use_container_width=True):
                st.session_state.question_count = c
                st.rerun()

        st.divider()
        if st.button("🚀 開始する", use_container_width=True, type="primary"):
            # データ取得
            start_id = st.session_state.set_index * 100
            end_id = start_id + 99
            query = supabase.table("words").select("id,jp,en,progression,my").gte("id", start_id).lte("id", end_id)
            
            if st.session_state.mode == "未習得語":
                if st.session_state.study_mode == "英日単語帳":
                    query = query.lt("progression", 20) # 十の位が2未満
                else:
                    query = query.in_("progression", [0,1,10,11,20,21]) # 一の位が2未満
            elif st.session_state.mode == "my単語":
                query = query.eq("my", True)
                
            res = query.execute()
            questions = res.data or []
            
            if not questions:
                st.warning("条件に合う単語がありません。")
            else:
                st.session_state.current_questions = random.sample(questions, min(st.session_state.question_count, len(questions)))
                st.session_state.num = 0
                st.session_state.user_answers = []
                st.session_state.user_my_flags = []
                st.session_state.card_results = []
                st.session_state.screen = "quiz" if st.session_state.study_mode == "日英クイズ" else "card"
                st.rerun()

        if st.button("⬅️ セット選択に戻る", use_container_width=True):
            st.session_state.step = "select_set"
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
    st.progress((n) / len(questions))
    st.write(f"問題 {n+1} / {len(questions)}")
    
    with st.container(border=True):
        st.subheader(q["jp"])
        st.caption(f"ヒント：{q['en'][0]}...")

    while len(st.session_state.user_answers) <= n:
        st.session_state.user_answers.append("")
    while len(st.session_state.user_my_flags) <= n:
        st.session_state.user_my_flags.append(q["my"])

    if st.session_state.judged is None:
        with st.form(f"quiz_form_{n}"):
            ans = st.text_input("英語を入力", value="", key=f"input_{n}")
            my = st.checkbox("⭐ My単語", value=q["my"])
            if st.form_submit_button("判定", use_container_width=True):
                st.session_state.user_answers[n] = ans
                st.session_state.user_my_flags[n] = my
                st.session_state.judged = "correct" if ans.lower().strip() == q["en"].lower().strip() else "wrong"
                st.rerun()
    else:
        if st.session_state.judged == "correct":
            st.success(f"⭕ 正解！\n\n**{q['en']}**")
        else:
            st.error(f"❌ 不正解...\n\n正解: **{q['en']}**\n(入力: {st.session_state.user_answers[n]})")
        
        if st.button("次へ", use_container_width=True, type="primary"):
            st.session_state.num += 1
            st.session_state.judged = None
            st.rerun()

# ===================== 単語帳画面 =====================
elif st.session_state.screen == "card":
    questions = st.session_state.current_questions
    n = st.session_state.num

    if n >= len(questions):
        st.session_state.screen = "finish"
        st.rerun()

    q = questions[n]
    st.title("📖 単語帳")
    st.progress(n / len(questions))
    st.write(f"{n+1} / {len(questions)}")

    # カード表示
    card_height = 200
    if not st.session_state.card_flipped:
        if st.button(f"\n\n{q['en']}\n\n", use_container_width=True):
            st.session_state.card_flipped = True
            st.rerun()
        st.caption("タップで日本語を表示")
    else:
        if st.button(f"\n\n{q['jp']}\n\n", use_container_width=True):
            st.session_state.card_flipped = False
            st.rerun()
        st.caption("タップで英語を表示")

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("❌ わからない", use_container_width=True):
        st.session_state.card_results.append(0)
        st.session_state.num += 1
        st.session_state.card_flipped = False
        st.rerun()
    if c2.button("⭕ わかる", use_container_width=True, type="primary"):
        st.session_state.card_results.append(1)
        st.session_state.num += 1
        st.session_state.card_flipped = False
        st.rerun()

# ===================== 終了画面 =====================
elif st.session_state.screen == "finish":
    st.title("🎉 お疲れ様でした！")
    questions = st.session_state.current_questions

    # データベース更新
    with st.spinner("進捗を保存中..."):
        if st.session_state.study_mode == "英日単語帳":
            for q, res in zip(questions, st.session_state.card_results):
                prog_enjp = min((q["progression"] // 10) + 1, 2) if res == 1 else 0
                new_prog = prog_enjp * 10 + (q["progression"] % 10)
                supabase.table("words").update({"progression": new_prog}).eq("id", q["id"]).execute()
        else:
            for q, ans, my in zip(questions, st.session_state.user_answers, st.session_state.user_my_flags):
                correct = 1 if ans.lower().strip() == q["en"].lower().strip() else 0
                prog_jpen = min((q["progression"] % 10) + 1, 2) if correct == 1 else 0
                new_prog = (q["progression"] // 10) * 10 + prog_jpen
                supabase.table("words").update({"progression": new_prog, "my": my}).eq("id", q["id"]).execute()

    st.success("学習内容を保存しました。")
    
    if st.button("トップへ戻る", use_container_width=True, type="primary"):
        st.session_state.set_stats_cache = None # キャッシュクリア
        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()