import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

import streamlit as st

from src.ft_adapter import get_key_metrics
import inspect as _inspect
import src.ft_adapter as _m

st.write("ft_adapter loaded from:", _m.__file__)
st.write("get_key_metrics signature:", str(_inspect.signature(get_key_metrics)))

from src.schema import load_schema
from src.plots import plot_by_selection, PlotError


st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("目标：单公司多期趋势（line）+ 组内叠加（schema 驱动）")

schema = load_schema("config/indicators.yaml")

ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

view_mode = st.radio(
    "View Mode",
    ["Group (recommended)", "Single indicator"],
    horizontal=True,
    index=0,
)

run = st.button("Run")

if run:
    try:
        # ✅ IMPORTANT: use timeseries output
        df = get_key_metrics(
            ticker,
            output="timeseries",
            periods="all",
            inspect=False,   # set True if you want terminal debug
        )

        if df is None or df.empty:
            st.warning("No data returned. Try another ticker (MSFT/NVDA) or set inspect=True.")
            st.stop()

        # quick sanity check
        st.caption(f"shape: {df.shape}")
        st.caption(f"index sample: {list(df.index)[:5]}")
        st.caption(f"columns: {list(df.columns)}")

        st.subheader("Metrics (Time Series)")
        st.dataframe(df, use_container_width=True)

        st.subheader("Chart")
        if view_mode == "Group (recommended)":
            group_key = st.selectbox("Select group", list(schema.groups.keys()), index=0)
            fig = plot_by_selection(df, schema, group_key=group_key, title_prefix=f"{ticker} - ")
        else:
            ind_key = st.selectbox("Select indicator", list(schema.indicators.keys()), index=0)
            fig = plot_by_selection(df, schema, indicator_key=ind_key, title_prefix=f"{ticker} - ")

        st.pyplot(fig)

    except PlotError as e:
        st.error(f"Plot error: {e}")
    except Exception as e:
        st.error(f"运行失败：{e}")
