import pandas as pd
from supabase import create_client, Client

# =====================
# Supabase 設定
# =====================
SUPABASE_URL = "https://zrxbncjwqjzjudvzehfl.supabase.co"
SUPABASE_KEY = "sb_publishable__QkdLcW7YOOFU6oTc_byXg_YqJm_uK_"                     # あなたのanonキー
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================
# CSV 読み込み
# =====================
CSV_PATH = "tangocho.csv"
df = pd.read_csv(CSV_PATH)

# =====================
# テーブル初期化（完全リセット）
# =====================
print("テーブルをリセットしています...")
supabase.table("words").delete().neq("id", 0).execute()  # 既存データ削除
# Supabaseのテーブル自体を削除 → 作り直す場合は Supabase の UI で「Delete table」して作成

# =====================
# 挿入データ作成
# =====================
records = []
for _, row in df.iterrows():
    records.append({
        "jp": row["jp"],
        "en": row["en"],
        "progression": 0,
        "my": False
    })

# =====================
# データを分割して挿入（100件ずつなどで安定）
# =====================
BATCH_SIZE = 1900
for i in range(0, len(records), BATCH_SIZE):
    batch = records[i:i+BATCH_SIZE]
    res = supabase.table("words").insert(batch).execute()
    if res.data is None:
        print("挿入に失敗しました")
    else:
        print(f"{len(records)} 件 挿入完了")
print("CSV の Supabase への初期挿入が完了しました。")
