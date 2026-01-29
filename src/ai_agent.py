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
    构造“指标组”的 Prompt：
    - 利用 Schema 里的 GroupMeta / IndicatorMeta 提供更多上下文
    - 让大模型按一个小型“分析报告”的结构来输出
    """

    # ---- 1) 解析组的元信息 ----
    group_display_name = group_key
    group_desc = ""

    if schema is not None and hasattr(schema, "groups"):
        groups: Dict[str, Any] = getattr(schema, "groups")
        if group_key in groups:
            gm = groups[group_key]
            group_display_name = getattr(gm, "display_name", group_key)
            group_desc = getattr(gm, "description", "")

    # ---- 2) 构造多指标时间序列块 ----
    lines: List[str] = []

    for key in indicator_keys:
        if key not in df.columns:
            continue

        series = df[key].dropna().tail(10)
        if series.empty:
            continue

        # 从 indicators 里补充元信息
        display_name = key
        unit = ""
        category = ""

        if schema is not None and hasattr(schema, "indicators"):
            indicators: Dict[str, Any] = getattr(schema, "indicators")
            if key in indicators:
                meta = indicators[key]
                display_name = getattr(meta, "indicator_name", key)
                unit = getattr(meta, "unit", "")
                category = getattr(meta, "category", "")

        header = f"- 指标 {key}｜名称：{display_name}｜类别：{category or '未标注'}｜单位：{unit or '无单位/比率'}"
        values = "\n".join(
            f"    · {idx}: {val:.4f}" for idx, val in series.items()
        )
        lines.append(header + "\n" + values)

    if not lines:
        series_block = "（该指标组中没有任何指标有足够的时间序列数据。）"
    else:
        series_block = "\n\n".join(lines)

    # ---- 3) 拼接最终 Prompt ----
    base_prompt = f"""
你是一名金融数据分析助手，擅长从“多个财务指标的组合”中，看出一家公司的整体财务状况和变化趋势。

现在给你一家公司 {ticker} 的一个“指标组”（group），其中包含若干个相关的财务指标，请你结合这些指标的时间序列进行综合分析。

指标组基本信息：
- Group Key：{group_key}
- Group 名称：{group_display_name}
- Group 描述：{group_desc or "（无额外描述）"}

该组内各指标的时间序列（按年份排序，最近在下方）：

{series_block}

请严格按照以下结构，用中文输出你的分析（使用 Markdown 小标题）：

### 1. 趋势总览（整体视角）
- 用 2-3 句话概括：这个指标组整体反映的财务维度是什么（例如：盈利能力、偿债与杠杆、成长性、运营效率等）。
- 概括过去这些年里，公司在这一维度是整体改善、恶化还是大致稳定。

### 2. 指标拆解（逐个看代表性指标）
- 至少点名 2-3 个关键指标（用“指标中文名 + 简短解释”的形式），说明：
  - 各自的走势（上升/下降/波动）
  - 以及它们和公司经营之间最直观的联系（例如：毛利率提升意味着定价能力/成本控制改善）。

### 3. 指标之间的关系（协同 / 矛盾）
- 如果不同指标之间存在明显的“配合关系”或“矛盾关系”（例如：利润率提高但负债率也显著上升），请：
  - 先描述现象，再给出 1-2 个可能的合理解释。
- 如果数据不足以支持清晰结论，也请明确说明。

### 4. 风险与不确定性（不要给投资建议）
- 指出该组数据中可能存在的局限性，例如：
  - 时间跨度较短、波动很大、缺少关键年份等。
- 从“解读角度”出发给出提示：哪些地方需要谨慎，不要做过度推断。
- 不要给任何“买入/卖出/估值便宜或昂贵”的判断，也不要给投资建议。

### 5. 回应用户的特别关注点
用户的额外问题是：
{user_prompt.strip() if user_prompt.strip() else "无特别问题，请你站在长期、审慎的角度给出专业分析。"}

- 请在最后一个小段落单独用 2-3 句话回应用户的问题，或者说明为什么当前数据不足以回答。
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

def analyze_custom_bundle_timeseries(
    ticker: str,
    df: pd.DataFrame,
    indicator_keys: List[str],
    schema: Any = None,
    user_prompt: str = "",
) -> str:
    """
    对“用户自定义选出的多个指标”的时间序列进行 AI 分析。

    和 analyze_group_timeseries 很像，只是不依赖 schema.groups，
    指标集合完全来自前端的 multiselect。
    """
    if not indicator_keys:
        raise ValueError("请至少选择一个指标进行分析。")

    # 过滤掉 df 中不存在的列
    valid_keys = [k for k in indicator_keys if k in df.columns]

    if not valid_keys:
        raise ValueError("选中的指标在当前数据中都没有对应的数据列。")

    # 复用 group 的 Prompt，只是 group_key 换成“自定义组合”
    prompt = build_group_prompt(
        ticker=ticker,
        group_key="自定义指标组合",
        df=df,
        indicator_keys=valid_keys,
        schema=schema,
        user_prompt=user_prompt,
    )

    return call_llm(prompt)
