# src/ai_compare.py

from __future__ import annotations
import os
import pandas as pd
import requests
from dataclasses import dataclass


# -----------------------------------
# 错误结构
# -----------------------------------
@dataclass
class AIMultiCompareError(Exception):
    message: str
    def __str__(self):
        return self.message


# -----------------------------------
# 加载 API key
# -----------------------------------
def _load_api_key() -> str:
    key = os.getenv("DEEPSEEK_API_KEY")
    if not key:
        raise AIMultiCompareError("未设置 DEEPSEEK_API_KEY 环境变量。")
    return key


# -----------------------------------
# 将 df 转成纯文本
# -----------------------------------
def _df_to_text(df: pd.DataFrame) -> str:
    out = "Year | " + " | ".join(df.columns) + "\n"
    out += "-" * (len(out) + 10) + "\n"

    for idx in df.index:
        row = df.loc[idx]
        row_txt = " | ".join(
            (f"{row[c]:.4f}" if pd.notna(row[c]) else "NaN") for c in df.columns
        )
        out += f"{idx} | {row_txt}\n"

    return out


# -----------------------------------
# 主函数：多公司分析
# -----------------------------------
def analyze_multi_company_indicator(
    metric_key: str,
    df_metric: pd.DataFrame,
    user_prompt: str = "",
) -> str:

    if df_metric is None or df_metric.empty:
        raise AIMultiCompareError("df_metric 为空，无法分析。")

    api_key = _load_api_key()

    df_text = _df_to_text(df_metric)

    final_prompt = f"""
你是专业财务分析 AI，请基于真实数据进行严格的趋势分析，不提供投资建议。

分析指标：{metric_key}

### 数据（多个公司，多年份）

用户补充需求：
{user_prompt}

请输出内容：
1. 各公司水平对比（谁高谁低）
2. 趋势变化（改善/恶化/波动性）
3. 结构性差异（盈利模式、成本结构）
4. 指标可能反映的经营特征（不提供投资建议）
5. 数据局限
"""

    url = "https://api.deepseek.com/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "user", "content": final_prompt}
        ],
        "temperature": 0.3,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        return data["choices"][0]["message"]["content"]

    except Exception as e:
        raise AIMultiCompareError(f"调用 DeepSeek API 失败：{e}")
