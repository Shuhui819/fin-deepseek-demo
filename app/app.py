import sys
from pathlib import Path

import streamlit as st

# 让 src 可被导入
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics
from src.schema import load_schema
from src.plots import plot_by_selection, PlotError


# --------------------------
# 全局配置
# --------------------------
st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("目标：单公司多期趋势（line）+ 组内/单指标可视化")

schema = load_schema("config/indicators.yaml")

# --------------------------
# 初始化 session_state
# --------------------------
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False

if "df" not in st.session_state:
    st.session_state.df = None

if "view_mode" not in st.session_state:
    st.session_state.view_mode = "Group (recommended)"

# 注意：下面两个 key 只负责记住用户选择
if "selected_group" not in st.session_state:
    # 如果 schema.groups 为空就给个占位
    default_group = next(iter(schema.groups.keys()), None)
    st.session_state.selected_group = default_group

if "selected_indicator" not in st.session_state:
    default_indicator = next(iter(schema.indicators.keys()), None)
    st.session_state.selected_indicator = default_indicator


# --------------------------
# 基础输入
# --------------------------
ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

view_mode = st.radio(
    "View Mode",
    ["Group (recommended)", "Single indicator"],
    horizontal=True,
    index=0 if st.session_state.view_mode == "Group (recommended)" else 1,
    key="view_mode",  # 和 session_state 绑定
)


# --------------------------
# Run 按钮：只负责“重新拉数据”
# --------------------------
if st.button("Run"):
    try:
        df = get_key_metrics(
            ticker,
            output="timeseries",
            periods="all",
            inspect=False,
        )
        if df is None or df.empty:
            st.warning("No data returned. Try another ticker (e.g. MSFT / NVDA).")
            st.session_state.data_loaded = False
            st.session_state.df = None
        else:
            st.session_state.df = df
            st.session_state.data_loaded = True
    except Exception as e:
        st.error(f"运行失败：{e}")
        st.session_state.data_loaded = False
        st.session_state.df = None


# --------------------------
# 只有在 data_loaded=True 的时候才展示数据和图表
# --------------------------
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df

    # 小检查，帮助你确认已经是时间序列
    st.caption(f"shape: {df.shape}")
    st.caption(f"index sample: {list(df.index)[:5]}")
    st.caption(f"columns: {list(df.columns)}")

    st.subheader("Metrics (Time Series)")
    st.dataframe(df, use_container_width=True)

    st.subheader("Chart")

    try:
        if st.session_state.view_mode == "Group (recommended)":
            # 组选择：用 selected_group 记住选择
            group_key = st.selectbox(
                "Select group",
                options=list(schema.groups.keys()),
                index=0 if st.session_state.selected_group is None
                        else list(schema.groups.keys()).index(st.session_state.selected_group),
                key="selected_group",
            )

            fig = plot_by_selection(
                df,
                schema,
                group_key=group_key,
                title_prefix=f"{ticker} - ",
            )
        else:
            # 单指标选择：用 selected_indicator 记住选择
            indicator_key = st.selectbox(
                "Select indicator",
                options=list(schema.indicators.keys()),
                index=0 if st.session_state.selected_indicator is None
                        else list(schema.indicators.keys()).index(st.session_state.selected_indicator),
                key="selected_indicator",
            )

            fig = plot_by_selection(
                df,
                schema,
                indicator_key=indicator_key,
                title_prefix=f"{ticker} - ",
            )

        st.pyplot(fig)

    except PlotError as e:
        st.error(f"Plot error: {e}")
    except Exception as e:
        st.error(f"绘图失败：{e}")
