# src/plots.py
import matplotlib.pyplot as plt
import pandas as pd


def plot_two_metrics_bar(metrics_df: pd.DataFrame, title: str = "Core Metrics (MVP)"):
    """
    Draw a simple bar chart for the MVP metrics.
    Expected columns: Metric, Value, Period, Unit
    """
    # 保证字段存在
    needed = {"Metric", "Value", "Period", "Unit"}
    missing = needed - set(metrics_df.columns)
    if missing:
        raise ValueError(f"metrics_df missing columns: {missing}")

    # 只取非空
    df = metrics_df.dropna(subset=["Value"]).copy()
    if df.empty:
        raise ValueError("No metric values available to plot.")

    period = str(df["Period"].iloc[0])

    fig = plt.figure()
    plt.bar(df["Metric"], df["Value"])
    plt.title(f"{title} - {period}")
    plt.ylabel("Value")
    plt.xticks(rotation=15)

    # 在柱子上标注数值
    for i, v in enumerate(df["Value"].tolist()):
        plt.text(i, v, f"{v:.2f}", ha="center", va="bottom")

    plt.tight_layout()
    return fig
