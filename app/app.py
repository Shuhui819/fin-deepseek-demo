# app/app.py

import sys
from pathlib import Path

import streamlit as st

# 让 src 可被导入
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics
from src.schema import load_schema
from src.plots import plot_by_selection, PlotError
from src.ai_agent import (
    analyze_indicator_timeseries,
    analyze_group_timeseries,
    AIConfigError,
)


# --------------------------
# 全局配置
# --------------------------
st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("目标：单公司多期趋势 + 指标/指标组可视化 + DeepSeek AI 解读")

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

if "selected_group" not in st.session_state:
    default_group = next(iter(schema.groups.keys()), None)
    st.session_state.selected_group = default_group

if "selected_indicator" not in st.session_state:
    default_indicator = next(iter(schema.indicators.keys()), None)
    st.session_state.selected_indicator = default_indicator

if "ai_last_answer" not in st.session_state:
    st.session_state.ai_last_answer = ""

# --------------------------
# 基础输入
# --------------------------
ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

view_mode = st.radio(
    "View Mode",
    ["Group (recommended)", "Single indicator"],
    horizontal=True,
    index=0 if st.session_state.view_mode == "Group (recommended)" else 1,
    key="view_mode",
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
            st.session_state.ai_last_answer = ""  # 换公司时清空 AI 输出
    except Exception as e:
        st.error(f"运行失败：{e}")
        st.session_state.data_loaded = False
        st.session_state.df = None


# --------------------------
# 有数据时展示表格 + 图表
# --------------------------
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df

    st.caption(f"shape: {df.shape}")
    st.caption(f"index sample: {list(df.index)[:5]}")
    st.caption(f"columns: {list(df.columns)}")

    st.subheader("Metrics (Time Series)")
    st.dataframe(df, width="stretch")

    st.subheader("Chart")

    current_indicator_key = None
    current_group_key = None

    try:
        if st.session_state.view_mode == "Group (recommended)":
            group_key = st.selectbox(
                "Select group",
                options=list(schema.groups.keys()),
                index=0 if st.session_state.selected_group is None
                        else list(schema.groups.keys()).index(st.session_state.selected_group),
                key="selected_group",
            )
            current_group_key = group_key

            fig = plot_by_selection(
                df,
                schema,
                group_key=group_key,
                title_prefix=f"{ticker} - ",
            )
            st.pyplot(fig)

        else:  # Single indicator
            indicator_key = st.selectbox(
                "Select indicator",
                options=list(schema.indicators.keys()),
                index=0 if st.session_state.selected_indicator is None
                        else list(schema.indicators.keys()).index(st.session_state.selected_indicator),
                key="selected_indicator",
            )
            current_indicator_key = indicator_key

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


    # --------------------------
    # AI Insight 区域
    # --------------------------
    st.subheader("AI Insight")

    # 根据模式切换默认提示语
    if st.session_state.view_mode == "Single indicator":
        default_user_prompt = "请根据上面的折线图，用通俗的中文分析一下该指标的整体趋势和可能含义，不要给投资建议。"
    else:
        default_user_prompt = "请根据上面的多条折线，综合分析该指标组反映的财务状况和变化，不要给投资建议。"

    user_prompt = st.text_area(
        "你希望 AI 重点关注什么？（可选）",
        value=default_user_prompt,
        height=100,
    )

    if st.session_state.view_mode == "Single indicator" and current_indicator_key is not None:
        if st.button("让 AI 解读这个指标"):
            try:
                with st.spinner("AI 正在分析单个指标，请稍等…"):
                    answer = analyze_indicator_timeseries(
                        ticker=ticker,
                        df=df,
                        indicator_key=current_indicator_key,
                        schema=schema,
                        user_prompt=user_prompt,
                    )
                st.session_state.ai_last_answer = answer
            except AIConfigError as e:
                st.error(f"AI 配置问题：{e}")
            except ValueError as e:
                st.error(f"数据不足：{e}")
            except Exception as e:
                st.error(f"AI 分析失败：{e}")

    elif st.session_state.view_mode == "Group (recommended)" and current_group_key is not None:
        if st.button("让 AI 解读这个指标组"):
            try:
                with st.spinner("AI 正在分析指标组，请稍等…"):
                    answer = analyze_group_timeseries(
                        ticker=ticker,
                        df=df,
                        group_key=current_group_key,
                        schema=schema,
                        user_prompt=user_prompt,
                    )
                st.session_state.ai_last_answer = answer
            except AIConfigError as e:
                st.error(f"AI 配置问题：{e}")
            except ValueError as e:
                st.error(f"数据不足：{e}")
            except Exception as e:
                st.error(f"AI 分析失败：{e}")

    # 展示上一轮 AI 输出
    if st.session_state.ai_last_answer:
        st.markdown("---")
        st.markdown("**AI 分析结果：**")
        st.markdown(st.session_state.ai_last_answer)
else:
    st.info("请输入有效的 Ticker 并点击 Run。")
