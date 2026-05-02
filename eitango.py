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

# ===================== データ集計関数 (セットごとの進捗用) =====================
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
            s_idx = w["id"] // 100
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
        if len(data) < limit: break
        offset += limit
    
    result = {
        "sets": stats,
        "total_count": total_count,
        "total_learned1": total_learned1,
        "total_learned2": total_learned2
    }
    st.session_state.set_stats_cache = result
    return result

progress_data = get_progress_data()

# ===================== サイドバー表示 (全体進捗) =====================
rate1 = progress_data["total_learned1"] / progress_data["total_count"] if progress_data["total_count"] else 0
rate2 = progress_data["total_learned2"] / progress_data["total_count"] if progress_data["total_count"] else 0

st.sidebar.markdown("### 📊 総学習状況")
st.sidebar.caption(f"日英：{progress_data['total_learned1']} / {progress_data['total_count']} ({int(rate1*100)}%)")
st.sidebar.progress(rate1)
st.sidebar.caption(f"英日：{progress_data['total_learned2']} / {progress_data['total_count']} ({int(rate2*100)}%)")
st.sidebar.progress(rate2)

# ===================== タイトル画面 =====================
if st.session_state.screen == "title":
    st.title("📘 英検準1級単語")
    st.write("モバイル対応・進捗管理付き")
    if st.button("スタート", use_container_width=True, type="primary"):
        st.session_state.screen = "select"
        st.session_state.step = "select_set"
        st.rerun()

# ===================== セット選択画面 =====================
elif st.session_state.screen == "select":
    if st.session_state.step == "select_set":
        st.title("📂 セット選択")
        # スマホ向け：セットごとのカード表示
        for i in sorted(progress_data["sets"].keys()):
            s = progress_data["sets"][i]
            p1 = s["learned1"] / s["total"] if s["total"] else 0
            p2 = s["learned2"] / s["total"] if s["total"] else 0
            
            with st.container(border=True):
                st.markdown(f"#### 📦 セット {i+1}")
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(f"日英: {int(p1*100)}%")
                    st.progress(p1)
                with c2:
                    st.caption(f"英日: {int(p2*100)}%")
                    st.progress(p2)
                
                if st.button(f"セット {i+1} を選択", key=f"set_{i}", use_container_width=True):
                    st.session_state.set_index = i
                    st.session_state.step = "select_config"
                    st.rerun()

    elif st.session_state.step == "select_config":
        st.title(f"⚙️ 設定 (セット {st.session_state.set_index+1})")
        
        # モード選択ボタン
        st.subheader("学習モード")
        m1, m2 = st.columns(2)
        if m1.button("日英クイズ" + (" ✅" if st.session_state.study_mode == "日英クイズ" else ""), use_container_width=True):
            st.session_state.study_mode = "日英クイズ"; st.rerun()
        if m2.button("英日単語帳" + (" ✅" if st.session_state.study_mode == "英日単語帳" else ""), use_container_width=True):
            st.session_state.study_mode = "英日単語帳"; st.rerun()

        # 出題形式 / 問題数
        st.subheader("出題範囲 / 問題数")
        m_cols = st.columns(3)
        for idx, m in enumerate(["全単語", "未習得語", "my単語"]):
            if m_cols[idx].button(m + ("\n✅" if st.session_state.mode == m else ""), use_container_width=True):
                st.session_state.mode = m; st.rerun()
        
        c_cols = st.columns(4)
        for idx, c in enumerate([5, 10, 20, 50]):
            if c_cols[idx].button(str(c) + ("\n✅" if st.session_state.question_count == c else ""), use_container_width=True):
                st.session_state.question_count = c; st.rerun()

        st.divider()
        if st.button("🚀 学習を開始", use_container_width=True, type="primary"):
            start_id, end_id = st.session_state.set_index * 100, st.session_state.set_index * 100 + 99
            query = supabase.table("words").select("*").gte("id", start_id).lte("id", end_id)
            if st.session_state.mode == "未習得語":
                if st.session_state.study_mode == "英日単語帳":
                    query = query.lt("progression", 20)
                else:
                    query = query.in_("progression", [0,1,10,11,20,21])
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
                if "updated" in st.session_state: del st.session_state.updated
                st.rerun()

        if st.button("⬅️ セット選び直す", use_container_width=True):
            st.session_state.step = "select_set"; st.rerun()

# ===================== クイズ画面 =====================
elif st.session_state.screen == "quiz":
    questions = st.session_state.current_questions
    n = st.session_state.num
    if n >= len(questions):
        st.session_state.screen = "finish"; st.rerun()

    q = questions[n]
    st.title("✏️ クイズ")
    st.progress(n / len(questions))
    
    with st.container(border=True):
        st.subheader(q["jp"])
        st.caption(f"ヒント：{q['en'][0]}...")

    while len(st.session_state.user_answers) <= n: st.session_state.user_answers.append("")
    while len(st.session_state.user_my_flags) <= n: st.session_state.user_my_flags.append(q["my"])

    if st.session_state.judged is None:
        with st.form(f"f_{n}"):
            ans = st.text_input("英語を入力", value="", key=f"ans_{n}")
            my = st.checkbox("⭐ My単語に追加", value=q["my"])
            if st.form_submit_button("判定", use_container_width=True):
                st.session_state.user_answers[n] = ans
                st.session_state.user_my_flags[n] = my
                st.session_state.judged = "correct" if ans.lower().strip() == q["en"].lower().strip() else "wrong"
                st.rerun()
    else:
        if st.session_state.judged == "correct": st.success(f"⭕ 正解！\n\n**{q['en']}**")
        else: st.error(f"❌ 不正解...\n\n正解: **{q['en']}**")
        if st.button("次へ", use_container_width=True, type="primary"):
            st.session_state.num += 1; st.session_state.judged = None; st.rerun()

# ===================== 単語帳画面 =====================
elif st.session_state.screen == "card":
    questions = st.session_state.current_questions
    n = st.session_state.num
    if n >= len(questions):
        st.session_state.screen = "finish"; st.rerun()

    q = questions[n]
    st.title("📖 単語帳")
    st.progress(n / len(questions))
    
    word_display = q["jp"] if st.session_state.card_flipped else q["en"]
    if st.button(f"\n\n{word_display}\n\n", use_container_width=True):
        st.session_state.card_flipped = not st.session_state.card_flipped; st.rerun()
    st.caption("タップで反転")

    st.divider()
    c1, c2 = st.columns(2)
    if c1.button("❌ わからない", use_container_width=True):
        st.session_state.card_results.append(0); st.session_state.num += 1; st.session_state.card_flipped = False; st.rerun()
    if c2.button("⭕ わかる", use_container_width=True, type="primary"):
        st.session_state.card_results.append(1); st.session_state.num += 1; st.session_state.card_flipped = False; st.rerun()

# ===================== 終了結果画面 =====================
elif st.session_state.screen == "finish":
    st.title("🎉 セット完了！")
    questions = st.session_state.current_questions

    # 初回表示時にDBを更新
    if "updated" not in st.session_state:
        with st.spinner("保存中..."):
            for i, q in enumerate(questions):
                if st.session_state.study_mode == "英日単語帳":
                    res = st.session_state.card_results[i]
                    prog_enjp = min((q["progression"] // 10) + 1, 2) if res == 1 else 0
                    new_prog = prog_enjp * 10 + (q["progression"] % 10)
                    supabase.table("words").update({"progression": new_prog}).eq("id", q["id"]).execute()
                else:
                    ans, my = st.session_state.user_answers[i], st.session_state.user_my_flags[i]
                    is_correct = ans.lower().strip() == q["en"].lower().strip()
                    prog_jpen = min((q["progression"] % 10) + 1, 2) if is_correct else 0
                    new_prog = (q["progression"] // 10) * 10 + prog_jpen
                    supabase.table("words").update({"progression": new_prog, "my": my}).eq("id", q["id"]).execute()
        st.session_state.updated = True

    # 結果一覧の表示
    st.subheader("今回のまとめ")
    for i, q in enumerate(questions):
        if st.session_state.study_mode == "日英クイズ":
            is_correct = st.session_state.user_answers[i].lower().strip() == q["en"].lower().strip()
            my_val = st.session_state.user_my_flags[i]
            level = min((q["progression"] % 10) + 1, 2) if is_correct else 0
        else:
            is_correct = st.session_state.card_results[i] == 1
            my_val = q["my"]
            level = min((q["progression"] // 10) + 1, 2) if is_correct else 0
        
        status_icon = "⭕" if is_correct else "❌"
        level_stars = "⭐" * level if level > 0 else "🌑"
        
        with st.container(border=True):
            col_text, col_my = st.columns([4, 1])
            with col_text:
                st.markdown(f"{status_icon} **{q['en']}**")
                st.caption(f"{q['jp']} | 習熟度: {level_stars}")
            with col_my:
                # 日英クイズの時はMy単語チェックをその場で変更可能
                if st.session_state.study_mode == "日英クイズ":
                    new_my = st.checkbox("My", value=my_val, key=f"res_my_{q['id']}_{i}")
                    if new_my != my_val:
                        supabase.table("words").update({"my": new_my}).eq("id", q["id"]).execute()
                        st.session_state.user_my_flags[i] = new_my
                else:
                    if q["my"]: st.write("⭐")

    if st.button("問題選択へ戻る", use_container_width=True, type="primary"):
        st.session_state.set_stats_cache = None # 進捗再計算のため
        st.session_state.screen, st.session_state.step = "select", "select_set"
        if "updated" in st.session_state: del st.session_state.updated
        st.rerun()