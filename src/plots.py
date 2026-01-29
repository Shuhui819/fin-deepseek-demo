from __future__ import annotations

from typing import Optional, Sequence, List

import pandas as pd
import matplotlib.pyplot as plt

from .schema import Schema, IndicatorMeta, GroupMeta


class PlotError(RuntimeError):
    pass


def _ensure_timeseries_index(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        raise PlotError("No data to plot (empty DataFrame).")
    out = df.copy()
    # try to sort by index as string/int years
    try:
        out.index = out.index.astype(str)
        out = out.sort_index()
    except Exception:
        pass
    return out


def _validate_keys_exist(df: pd.DataFrame, keys: Sequence[str]) -> None:
    missing = [k for k in keys if k not in df.columns]
    if missing:
        raise PlotError(f"Missing indicator columns in DataFrame: {missing}")


def _format_title(meta: IndicatorMeta) -> str:
    return f"{meta.indicator_name} ({meta.unit})" if meta.unit else meta.indicator_name


def plot_single_indicator(
    df_metrics: pd.DataFrame,
    meta: IndicatorMeta,
    title_prefix: str = "",
) -> plt.Figure:
    """
    单指标折线图：一家公司、一个指标、多期趋势。
    """
    df = _ensure_timeseries_index(df_metrics)
    _validate_keys_exist(df, [meta.key])

    x = df.index.astype(str)
    y = df[meta.key].astype(float)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, y, marker="o")
    ax.set_title(f"{title_prefix}{_format_title(meta)}".strip())
    ax.set_xlabel("Period")
    ax.set_ylabel(meta.unit if meta.unit else "Value")
    if len(x) > 10:
        ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, linewidth=0.3)
    fig.tight_layout()
    return fig


def plot_group_overlay(
    df_metrics: pd.DataFrame,
    schema: Schema,
    group: GroupMeta,
    title_prefix: str = "",
) -> plt.Figure:
    """
    指标组叠加：同一个 group 内多条指标，一张图 overlay。
    （要求组内单位一致，防止直觉误导）
    """
    df = _ensure_timeseries_index(df_metrics)
    keys = group.indicator_keys
    _validate_keys_exist(df, keys)

    metas = [schema.indicators[k] for k in keys]
    if group.require_same_unit:
        units = {m.unit for m in metas}
        if len(units) > 1:
            raise PlotError(
                f"Group '{group.key}' has mixed units {sorted(units)}; "
                "overlay disabled in V1."
            )

    x = df.index.astype(str)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    for m in metas:
        ax.plot(x, df[m.key].astype(float), marker="o", label=m.indicator_name)

    unit = metas[0].unit if metas else ""
    if unit:
        title = f"{title_prefix}{group.display_name} ({unit})".strip()
    else:
        title = f"{title_prefix}{group.display_name}".strip()

    ax.set_title(title)
    ax.set_xlabel("Period")
    ax.set_ylabel(unit if unit else "Value")
    if len(x) > 10:
        ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, linewidth=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_custom_bundle(
    df_metrics: pd.DataFrame,
    schema: Schema,
    indicator_keys: List[str],
    title_prefix: str = "",
) -> plt.Figure:
    """
    自定义指标组合：
    - 用户在前端任意多选若干指标
    - 在一张图里画出这些指标的时间序列

    不强制单位一致，由调用方 / 文案负责解释。
    """
    df = _ensure_timeseries_index(df_metrics)

    if not indicator_keys:
        raise PlotError("No indicators selected for custom bundle.")

    # 只保留 DataFrame 中实际存在的列
    valid_keys = [k for k in indicator_keys if k in df.columns]

    if not valid_keys:
        raise PlotError(
            "None of the selected indicators exist in DataFrame for custom bundle."
        )

    x = df.index.astype(str)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    any_plotted = False

    for key in valid_keys:
        series = df[key].dropna()
        if series.empty:
            continue

        # 默认用 key，当 schema 里有中文名时用中文名
        label = key
        if key in schema.indicators:
            meta = schema.indicators[key]
            label = meta.indicator_name or key

        ax.plot(series.index.astype(str), series.values.astype(float), marker="o", label=label)
        any_plotted = True

    if not any_plotted:
        raise PlotError(
            "All selected indicators have empty timeseries for custom bundle."
        )

    title = f"{title_prefix}自定义指标组合".strip()
    ax.set_title(title)
    ax.set_xlabel("Period")
    ax.set_ylabel("Value")
    if len(x) > 10:
        ax.tick_params(axis="x", labelrotation=45)
    ax.grid(True, linewidth=0.3)
    ax.legend()
    fig.tight_layout()
    return fig


def plot_by_selection(
    df_metrics: pd.DataFrame,
    schema: Schema,
    *,
    indicator_key: Optional[str] = None,
    group_key: Optional[str] = None,
    title_prefix: str = "",
) -> plt.Figure:
    """
    统一入口：
    - 传 indicator_key → 单指标
    - 传 group_key      → 指标组 overlay
    （自定义组合由前端单独调用 plot_custom_bundle）
    """
    if indicator_key:
        if indicator_key not in schema.indicators:
            raise PlotError(f"Unknown indicator_key: {indicator_key}")
        return plot_single_indicator(
            df_metrics,
            schema.indicators[indicator_key],
            title_prefix=title_prefix,
        )

    if group_key:
        if group_key not in schema.groups:
            raise PlotError(f"Unknown group_key: {group_key}")
        return plot_group_overlay(
            df_metrics,
            schema,
            schema.groups[group_key],
            title_prefix=title_prefix,
        )

    raise PlotError("Either indicator_key or group_key must be provided.")
