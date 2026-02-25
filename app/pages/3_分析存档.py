"""分析存档页 — 按日期回溯历史分析记录"""

import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st
from pfa.data.store import load_all_analyses

CST = timezone(timedelta(hours=8))


# --- Page ---
st.header("分析存档")

analyses = load_all_analyses()

if not analyses:
    st.info("暂无分析记录。请先在「投研看板」页运行深度分析。")
    st.stop()

# Build date list from analysis records
dates_set = set()
for a in analyses:
    d = a.analysis_time[:10]
    if d:
        dates_set.add(d)
date_list = sorted(dates_set, reverse=True)

selected_date = st.selectbox("选择日期", date_list, index=0)

filtered = [a for a in analyses if selected_date in a.analysis_time]

st.caption(f"共 {len(filtered)} 条分析记录")

for i, rec in enumerate(filtered):
    with st.expander(
        f"#{i+1}  {rec.analysis_time[:16]}  ·  {rec.model}  ·  {rec.news_count_input} 条新闻",
        expanded=(i == 0),
    ):
        st.markdown(rec.analysis)
        if rec.token_usage:
            st.caption(
                f"Token: prompt={rec.token_usage.get('prompt_tokens', '?')}, "
                f"completion={rec.token_usage.get('completion_tokens', '?')}, "
                f"total={rec.token_usage.get('total_tokens', '?')}"
            )
