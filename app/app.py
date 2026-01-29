# app/app.py

import sys
from pathlib import Path

import streamlit as st

# 让 src 可被导入
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics
from src.schema import load_schema
from src.plots import (
    plot_by_selection,
    plot_custom_bundle,
    PlotError,
)
from src.ai_agent import (
    analyze_indicator_timeseries,
    analyze_group_timeseries,
    analyze_custom_bundle_timeseries,  # NEW
    AIConfigError,
)


# --------------------------
# 全局配置
# --------------------------
st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("目标：多期趋势 + 指标组 + 自定义组合 + DeepSeek 解读")

schema = load_schema("config/indicators.yaml")

# --------------------------
# 初始化 session_state
# --------------------------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_state("data_loaded", False)
init_state("df", None)
init_state("view_mode", "Group")
init_state("selected_group", next(iter(schema.groups.keys()), None))
init_state("selected_indicator", next(iter(schema.indicators.keys()), None))
init_state("selected_bundle", [])
init_state("ai_last_answer", "")

# --------------------------
# 输入：Ticker + View Mode
# --------------------------
ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

view_options = ["Group", "Single indicator", "Custom bundle"]
view_mode = st.radio(
    "View Mode",
    view_options,
    horizontal=True,
    index=view_options.index(st.session_state.view_mode),
    key="view_mode",
)


# --------------------------
# Run 按钮：拉取 & 缓存数据
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
            st.warning("No data returned. Try another ticker (MSFT / NVDA / META).")
            st.session_state.data_loaded = False
            st.session_state.df = None
        else:
            st.session_state.df = df
            st.session_state.data_loaded = True
            st.session_state.ai_last_answer = ""  # 换公司 → 清空 AI 输出
    except Exception as e:
        st.error(f"运行失败：{e}")
        st.session_state.data_loaded = False
        st.session_state.df = None


# --------------------------
# 展示数据 + 图表
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
    current_bundle_keys = None

    try:
        # -------------------------
        # Group 模式
        # -------------------------
        if st.session_state.view_mode == "Group":
            group_key = st.selectbox(
                "Select group",
                options=list(schema.groups.keys()),
                index=list(schema.groups.keys()).index(st.session_state.selected_group),
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

        # -------------------------
        # 单指标模式
        # -------------------------
        elif st.session_state.view_mode == "Single indicator":
            indicator_key = st.selectbox(
                "Select indicator",
                options=list(schema.indicators.keys()),
                index=list(schema.indicators.keys()).index(st.session_state.selected_indicator),
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

        # -------------------------
        # 自定义组合模式（NEW）
        # -------------------------
        else:
            bundle_keys = st.multiselect(
                "选择任意多个指标",
                options=list(schema.indicators.keys()),
                default=st.session_state.selected_bundle,
                key="selected_bundle",
            )
            current_bundle_keys = bundle_keys

            if bundle_keys:
                fig = plot_custom_bundle(
                    df,
                    schema,
                    indicator_keys=bundle_keys,
                    title_prefix=f"{ticker} - "
                )
                st.pyplot(fig)
            else:
                st.info("请选择至少 1 个指标才能绘图。")

    except PlotError as e:
        st.error(f"Plot error: {e}")
    except Exception as e:
        st.error(f"绘图失败：{e}")


    # --------------------------
    # AI Insight 区域
    # --------------------------
    st.subheader("AI Insight")

    # 默认提示语
    if st.session_state.view_mode == "Single indicator":
        default_prompt = "请根据折线图，用通俗中文分析该指标趋势（不提供投资建议）。"
    elif st.session_state.view_mode == "Group":
        default_prompt = "请综合分析该指标组反映的财务状况和变化（不提供投资建议）。"
    else:
        default_prompt = "请分析这些指标组合呈现的财务洞察（不提供投资建议）。"

    user_prompt = st.text_area("补充你的分析需求（可选）", value=default_prompt)

    # -------------------------
    # AI：单指标
    # -------------------------
    if st.session_state.view_mode == "Single indicator" and current_indicator_key:
        if st.button("让 AI 解读这个指标"):
            try:
                with st.spinner("AI 正在分析…"):
                    ans = analyze_indicator_timeseries(
                        ticker=ticker,
                        df=df,
                        indicator_key=current_indicator_key,
                        schema=schema,
                        user_prompt=user_prompt,
                    )
                st.session_state.ai_last_answer = ans
            except Exception as e:
                st.error(f"AI 分析失败：{e}")

    # -------------------------
    # AI：指标组
    # -------------------------
    elif st.session_state.view_mode == "Group" and current_group_key:
        if st.button("让 AI 解读这个指标组"):
            try:
                with st.spinner("AI 正在分析…"):
                    ans = analyze_group_timeseries(
                        ticker=ticker,
                        df=df,
                        group_key=current_group_key,
                        schema=schema,
                        user_prompt=user_prompt,
                    )
                st.session_state.ai_last_answer = ans
            except Exception as e:
                st.error(f"AI 分析失败：{e}")

    # -------------------------
    # AI：自定义组合（NEW）
    # -------------------------
    elif st.session_state.view_mode == "Custom bundle" and current_bundle_keys:
        if st.button("让 AI 解读这一组指标"):
            try:
                with st.spinner("AI 正在分析自定义组合…"):
                    ans = analyze_custom_bundle_timeseries(
                        ticker=ticker,
                        df=df,
                        indicator_keys=current_bundle_keys,
                        schema=schema,
                        user_prompt=user_prompt,
                    )
                st.session_state.ai_last_answer = ans
            except Exception as e:
                st.error(f"AI 分析失败：{e}")

    # -------------------------
    # 展示 AI 输出
    # -------------------------
    if st.session_state.ai_last_answer:
        st.markdown("---")
        st.markdown("**AI 分析结果：**")
        st.markdown(st.session_state.ai_last_answer)

else:
    st.info("请输入有效 Ticker 并点击 Run。")
