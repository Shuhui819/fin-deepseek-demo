# src/ai_agent.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any, Dict, List

import os

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()


# -----------------------------
# 自定义异常：用于在 app.py 里友好提示
# -----------------------------
class AIConfigError(Exception):
    """Raised when AI is not properly configured (e.g., missing API key)."""


@dataclass
class IndicatorInfo:
    key: str
    display_name: str
    unit: str


# -----------------------------
# DeepSeek 客户端配置
# -----------------------------
DEEPSEEK_API_BASE = "https://api.deepseek.com"
DEEPSEEK_CHAT_PATH = "/chat/completions"


def _get_api_key() -> str:
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        raise AIConfigError(
            "未检测到 DEEPSEEK_API_KEY。请在项目根目录的 .env 或环境变量中配置你的 DeepSeek API Key。"
        )
    return api_key


# -----------------------------
# 单指标 Prompt
# -----------------------------
def build_indicator_prompt(
    ticker: str,
    info: IndicatorInfo,
    series: pd.Series,
    user_prompt: str,
) -> str:
    series = series.dropna().tail(10)

    if series.empty:
        series_text = "（该指标没有可用的时间序列数据。）"
    else:
        series_text = "\n".join(
            f"- {idx}: {val:.4f}" for idx, val in series.items()
        )

    base_prompt = f"""
你是一名金融数据分析助手，擅长用通俗易懂的语言解释上市公司的财务指标趋势。

现在给你一家公司 {ticker} 的一个财务指标的时间序列数据，请你进行分析。

指标信息：
- 指标 Key: {info.key}
- 指标名称: {info.display_name}
- 单位: {info.unit}

时间序列数据（按年份排序，最近在下方）：
{series_text}

请按照以下要求回答（使用中文）：
1. 先用 1-2 句话概括这个指标在这些年份的大致趋势（例如：整体上升/下降/先升后降/波动较大等）。
2. 用 2-3 句话，从业务和财务角度解释这种趋势可能代表什么含义（例如：盈利能力、成本控制、杠杆水平、偿债能力等）。
3. 如果数据点非常少（少于 3 个），请明确说明结论的有限性，不要过度解读。
4. 结合用户的额外问题进行补充说明（如果有特殊关注点）。

用户的额外问题是：
{user_prompt.strip() if user_prompt.strip() else "无特别问题，请你自行给出中立、审慎的专业分析。"}
"""
    return base_prompt.strip()


# -----------------------------
# 多指标组合 Prompt（Group）
# -----------------------------
def build_group_prompt(
    ticker: str,
    group_key: str,
    df: pd.DataFrame,
    indicator_keys: List[str],
    schema: Optional[Any],
    user_prompt: str,
) -> str:
    """
    将一个指标组里的多条时间序列一起打包给模型。
    """
    lines: List[str] = []

    for key in indicator_keys:
        if key not in df.columns:
            continue

        series = df[key].dropna().tail(10)
        if series.empty:
            continue

        display_name = key
        unit = ""

        if schema is not None and hasattr(schema, "indicators"):
            indicators: Dict[str, Any] = getattr(schema, "indicators")
            if key in indicators:
                meta = indicators[key]
                display_name = getattr(meta, "indicator_name", getattr(meta, "name", key))
                unit = getattr(meta, "unit", "")

        header = f"- 指标 {key}（{display_name}，单位：{unit}）"
        values = "\n".join(
            f"    · {idx}: {val:.4f}" for idx, val in series.items()
        )
        lines.append(header + "\n" + values)

    if not lines:
        series_block = "（该指标组中没有任何指标有足够的时间序列数据。）"
    else:
        series_block = "\n\n".join(lines)

    base_prompt = f"""
你是一名金融数据分析助手，擅长从“多个财务指标的组合”中，看出一家公司的整体财务状况和变化趋势。

现在给你一家公司 {ticker} 的一个“指标组”（group），其中包含若干个相关的财务指标，请你结合这些指标的时间序列进行综合分析。

指标组 Key：{group_key}

该组内各指标的时间序列（按年份排序，最近在下方）：

{series_block}

请按照以下要求回答（使用中文）：
1. 先整体概括：这个指标组整体反映的是什么维度（例如：盈利能力、偿债与杠杆、成长性、运营效率等），并用 1-2 句话总结过去这些年里公司的整体变化。
2. 点名至少 2-3 个代表性的指标，分别说明它们的趋势（上升/下降/波动）以及和公司经营之间的直观联系。
3. 如果不同指标之间存在明显的“配合关系”或“矛盾关系”（例如：利润率提高但负债率也显著上升），请尝试做出合理的解释。
4. 如果数据年份较少或者波动很大，请明确说明结论的有限性，避免过度解读。
5. 结合用户给出的额外问题，做适度的补充说明，但不要给具体的投资建议。

用户的额外问题是：
{user_prompt.strip() if user_prompt.strip() else "无特别问题，请你站在长期、审慎的角度给出专业分析。"}
"""
    return base_prompt.strip()


# -----------------------------
# 调用 DeepSeek LLM
# -----------------------------
def call_llm(prompt: str) -> str:
    api_key = _get_api_key()

    url = DEEPSEEK_API_BASE + DEEPSEEK_CHAT_PATH
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "deepseek-chat",
        "temperature": 0.4,
        "messages": [
            {
                "role": "system",
                "content": "你是一名专业的财务分析助手，擅长用简单中文解释复杂财务现象，语气冷静、中立、不夸大，不给具体投资建议。",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.RequestException as e:
        raise AIConfigError(f"调用 DeepSeek API 失败（网络问题）：{e}") from e

    if resp.status_code != 200:
        try:
            data = resp.json()
        except Exception:
            data = resp.text
        raise AIConfigError(
            f"DeepSeek API 返回错误状态码 {resp.status_code}，详情：{data}"
        )

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise AIConfigError(f"解析 DeepSeek 返回结果失败：{data}") from e

    return content.strip()


# -----------------------------
# 对外主函数：单指标分析
# -----------------------------
def analyze_indicator_timeseries(
    ticker: str,
    df: pd.DataFrame,
    indicator_key: str,
    schema: Optional[Any] = None,
    user_prompt: str = "",
) -> str:
    if indicator_key not in df.columns:
        raise ValueError(f"DataFrame 中不存在指标列: {indicator_key}")

    series = df[indicator_key].dropna()
    if series.empty:
        raise ValueError("该指标在当前公司几乎没有可用数据，无法进行分析。")

    display_name = indicator_key
    unit = ""

    if schema is not None and hasattr(schema, "indicators"):
        indicators: Dict[str, Any] = getattr(schema, "indicators")
        if indicator_key in indicators:
            meta = indicators[indicator_key]
            display_name = getattr(meta, "indicator_name", getattr(meta, "name", indicator_key))
            unit = getattr(meta, "unit", "")

    info = IndicatorInfo(
        key=indicator_key,
        display_name=display_name,
        unit=unit,
    )

    prompt = build_indicator_prompt(
        ticker=ticker,
        info=info,
        series=df[indicator_key],
        user_prompt=user_prompt,
    )

    return call_llm(prompt)


# -----------------------------
# 对外主函数：指标组组合分析（NEW）
# -----------------------------
def analyze_group_timeseries(
    ticker: str,
    df: pd.DataFrame,
    group_key: str,
    schema: Any,
    user_prompt: str = "",
) -> str:
    """
    对一个指标组（多指标组合）的时间序列进行 AI 分析。

    ⚠️ 针对你当前的 Schema 结构做了“精确适配”：
    - schema.groups: Dict[str, GroupMeta]
    - GroupMeta.indicator_keys: List[str]
    """

    # 1) 取出 GroupMeta 对象
    groups: Dict[str, Any] = schema.groups
    if group_key not in groups:
        raise ValueError(f"schema.groups 中不存在组: {group_key}")

    group_meta = groups[group_key]

    # 2) 直接使用 GroupMeta.indicator_keys
    indicator_keys = list(getattr(group_meta, "indicator_keys", []))

    if not indicator_keys:
        raise ValueError(
            f"组 {group_key} 的 GroupMeta.indicator_keys 为空，请检查 config/indicators.yaml 中该组的 indicator_keys 配置。"
        )

    # 3) 只保留 df 中真的存在的列
    indicator_keys = [k for k in indicator_keys if k in df.columns]

    if not indicator_keys:
        raise ValueError(
            f"组 {group_key} 中的所有指标在 DataFrame 中都不存在或没有数据，无法分析。"
        )

    # 4) 构造 Prompt 并调用 DeepSeek
    prompt = build_group_prompt(
        ticker=ticker,
        group_key=group_key,
        df=df,
        indicator_keys=indicator_keys,
        schema=schema,
        user_prompt=user_prompt,
    )

    return call_llm(prompt)
