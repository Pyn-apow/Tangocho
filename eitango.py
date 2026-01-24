import pandas as pd
import streamlit as st

# CSV読み込み
df = pd.read_csv("tangocho.csv")

WORDS_PER_TEST = 100

total_words = len(df)
num_tests = (total_words - 1) // WORDS_PER_TEST + 1

st.write(f"全{total_words}語 / {num_tests}セットあります")

# どの100語をやるか選択
test_no = int(st.text_input(f"何セット目をやりますか？ (1～{num_tests})：")) - 1

start = test_no * WORDS_PER_TEST
end = start + WORDS_PER_TEST
test_df = df.iloc[start:end]

correct = 0

st.write("\n--- 単語テスト開始 ---\n")
1
for i, row in test_df.iterrows():
    jp = row["jp"]
    en = row["en"]

    answer = st.text_input(f"{jp}({en[0]}-)：").strip()

    if answer.lower() == en.lower():
        st.write("○ 正解\n")
        correct += 1
    else:
        st.write(f"× 不正解（正解：{en}）\n")

st.write("=== 結果 ===")
st.write(f"{len(test_df)}問中 {correct}問 正解")
st.write(f"正答率：{correct / len(test_df) * 100:.1f}%")



