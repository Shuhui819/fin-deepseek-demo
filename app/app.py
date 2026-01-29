# app/app.py

import sys
from pathlib import Path

import streamlit as st
import matplotlib.pyplot as plt  # 用于多公司对比的绘图

# 让 src 可被导入
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics, get_key_metrics_multi_indicators
from src.schema import load_schema
from src.plots import plot_by_selection, PlotError
from src.ai_agent import (
    analyze_indicator_timeseries,
    analyze_group_timeseries,
    AIConfigError,
)
from src.ai_compare import analyze_multi_company_indicator, AIMultiCompareError


# --------------------------
# 全局配置
# --------------------------
st.set_page_config(page_title="Finance Deepseek Demo", layout="wide")
st.title("Finance Deepseek Demo")
st.write("目标：单公司多期趋势 + 指标/指标组可视化 + DeepSeek AI 解读 + 多公司对比 (beta)")

schema = load_schema("config/indicators.yaml")

# --------------------------
# 初始化 session_state
# --------------------------
def init_state(key, default):
    if key not in st.session_state:
        st.session_state[key] = default

init_state("data_loaded", False)
init_state("df", None)
init_state("view_mode", "Group (recommended)")
init_state("selected_group", next(iter(schema.groups.keys()), None))
init_state("selected_indicator", next(iter(schema.indicators.keys()), None))
init_state("ai_last_answer", "")

# 多公司对比相关的状态
init_state("compare_result", None)
init_state("compare_tickers_raw", "AAPL, MSFT, NVDA")
init_state("compare_metric", None)
init_state("ai_multi_last_answer", "")  # 跨公司 AI 分析结果


# --------------------------
# 基础输入（单公司）
# --------------------------
ticker = st.text_input("Ticker（股票代码）", value="AAPL").strip().upper()

view_mode = st.radio(
    "View Mode（单公司模式）",
    ["Group (recommended)", "Single indicator"],
    horizontal=True,
    index=0 if st.session_state.view_mode == "Group (recommended)" else 1,
    key="view_mode",
)


# --------------------------
# Run 按钮：只负责“重新拉单公司数据”
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
# 有数据时展示单公司表格 + 图表 + AI
# --------------------------
if st.session_state.data_loaded and st.session_state.df is not None:
    df = st.session_state.df

    st.caption(f"[Single company] shape: {df.shape}")
    st.caption(f"index sample: {list(df.index)[:5]}")
    st.caption(f"columns: {list(df.columns)}")

    st.subheader("Single Company Metrics (Time Series)")
    st.dataframe(df, width="stretch")

    st.subheader("Single Company Chart")

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
    # AI Insight 区域（单公司）
    # --------------------------
    st.subheader("AI Insight（单公司）")

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
        st.markdown("**AI 分析结果（单公司）：**")
        st.markdown(st.session_state.ai_last_answer)
else:
    st.info("请输入有效的 Ticker 并点击 Run。")


# ======================================================
# 🌟 Multi-company comparison (beta) 多公司对比区域
# ======================================================

st.markdown("---")
st.header("Multi-company comparison (beta)｜多公司对比")

st.write("在这里可以一次性对比多个公司的 **同一指标** 随时间的变化，并让 AI 做横向分析。")

# 输入多个公司（逗号分隔）
compare_tickers_raw = st.text_input(
    "公司列表（逗号分隔，例如：AAPL, MSFT, NVDA）",
    value=st.session_state.compare_tickers_raw,
    key="compare_tickers_raw",
)

# 拉取多公司数据
if st.button("Run comparison"):
    tickers = [t.strip().upper() for t in compare_tickers_raw.split(",") if t.strip()]
    if not tickers:
        st.error("请输入至少一个有效的 Ticker。")
    else:
        try:
            res = get_key_metrics_multi_indicators(
                tickers,
                output="timeseries",
                periods="all",
                mvp_only=False,
                inspect=False,
            )
            st.session_state.compare_result = res
            st.session_state.compare_metric = None
            st.session_state.ai_multi_last_answer = ""  # 换公司后清空跨公司 AI 输出
            st.success(f"已成功获取 {len(tickers)} 家公司的时间序列指标。")
        except Exception as e:
            st.error(f"多公司对比数据获取失败：{e}")
            st.session_state.compare_result = None

# 如果已有对比数据，展示指标选择 + 表格 + 图 + AI
if st.session_state.compare_result:
    metric_keys = list(st.session_state.compare_result.keys())
    if not metric_keys:
        st.warning("当前没有可用的指标，请检查数据源。")
    else:
        # 选择要对比的指标
        default_index = 0
        if st.session_state.compare_metric in metric_keys:
            default_index = metric_keys.index(st.session_state.compare_metric)

        metric_key = st.selectbox(
            "选择要对比的指标",
            options=metric_keys,
            index=default_index,
            key="compare_metric",
        )

        df_metric = st.session_state.compare_result[metric_key]

        st.subheader(f"指标 {metric_key} 的跨公司对比表")
        st.dataframe(df_metric, width="stretch")

        # 画多公司折线图：x = 年份 / index，y = 指标值，每条线一个公司
        st.subheader(f"指标 {metric_key} 的多公司折线对比图")

        if df_metric is not None and not df_metric.empty:
            fig, ax = plt.subplots()
            x = df_metric.index.astype(str)

            for col in df_metric.columns:
                ax.plot(x, df_metric[col].astype(float), marker="o", label=col)

            ax.set_title(f"{metric_key} - Multi-company comparison")
            ax.set_xlabel("Period")
            ax.set_ylabel("Value")
            if len(x) > 10:
                ax.tick_params(axis="x", labelrotation=45)
            ax.grid(True, linewidth=0.3)
            ax.legend()
            fig.tight_layout()

            st.pyplot(fig)
        else:
            st.warning("该指标在所选公司中没有有效数据。")

        # --------------------------
        # AI Insight（跨公司对比）
        # --------------------------
        if df_metric is not None and not df_metric.empty:
            st.subheader("AI Insight（跨公司对比）")

            multi_user_prompt = st.text_area(
                "（可选）告诉 AI 你想关注什么，比如“谁更稳定”“谁改善更大”“为什么差异这么大”。",
                value="请客观分析该指标在不同公司之间的水平与趋势差异，并讨论可能原因，但不要提供任何投资建议。",
                height=120,
                key="multi_ai_prompt",
            )

            if st.button("让 AI 分析这个指标的跨公司对比", key="btn_multi_ai"):
                try:
                    with st.spinner("AI 正在分析跨公司数据，请稍等…"):
                        answer = analyze_multi_company_indicator(
                            metric_key=metric_key,
                            df_metric=df_metric,
                            user_prompt=multi_user_prompt,
                        )
                    st.session_state.ai_multi_last_answer = answer
                except AIMultiCompareError as e:
                    st.error(f"AI 错误：{e}")
                except Exception as e:
                    st.error(f"分析失败：{e}")

            if st.session_state.ai_multi_last_answer:
                st.markdown("---")
                st.markdown("**AI 分析结果（跨公司）：**")
                st.markdown(st.session_state.ai_multi_last_answer)
