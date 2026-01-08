import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import streamlit as st
from src.ft_adapter import get_key_metrics
from src.plots import plot_two_metrics_bar

st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo (MVP)")
st.write("目标：先跑通端到端流程（2个稳定指标 + 图表展示）")

ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

col1, col2 = st.columns([1, 2])
with col1:
    run = st.button("Run")

if run:
    try:
        # 1) 拿指标（默认 mvp_only=True，所以只返回两行）
        df = get_key_metrics(ticker)

        st.subheader("Core Metrics (MVP)")
        st.dataframe(df, use_container_width=True)

        # 2) 画图
        fig = plot_two_metrics_bar(df, title=f"{ticker} Metrics")
        st.subheader("Chart")
        st.pyplot(fig)

    except Exception as e:
        st.error(f"运行失败：{e}")
