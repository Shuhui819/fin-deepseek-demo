from __future__ import annotations

from typing import Optional, Sequence

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


def plot_single_indicator(df_metrics: pd.DataFrame, meta: IndicatorMeta, title_prefix: str = "") -> plt.Figure:
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


def plot_group_overlay(df_metrics: pd.DataFrame, schema: Schema, group: GroupMeta, title_prefix: str = "") -> plt.Figure:
    df = _ensure_timeseries_index(df_metrics)
    keys = group.indicator_keys
    _validate_keys_exist(df, keys)

    metas = [schema.indicators[k] for k in keys]
    if group.require_same_unit:
        units = {m.unit for m in metas}
        if len(units) > 1:
            raise PlotError(f"Group '{group.key}' has mixed units {sorted(units)}; overlay disabled in V1.")

    x = df.index.astype(str)

    fig = plt.figure()
    ax = fig.add_subplot(111)

    for m in metas:
        ax.plot(x, df[m.key].astype(float), marker="o", label=m.indicator_name)

    unit = metas[0].unit if metas else ""
    ax.set_title(f"{title_prefix}{group.display_name} ({unit})".strip() if unit else f"{title_prefix}{group.display_name}".strip())
    ax.set_xlabel("Period")
    ax.set_ylabel(unit if unit else "Value")
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
    if indicator_key:
        if indicator_key not in schema.indicators:
            raise PlotError(f"Unknown indicator_key: {indicator_key}")
        return plot_single_indicator(df_metrics, schema.indicators[indicator_key], title_prefix=title_prefix)

    if group_key:
        if group_key not in schema.groups:
            raise PlotError(f"Unknown group_key: {group_key}")
        return plot_group_overlay(df_metrics, schema, schema.groups[group_key], title_prefix=title_prefix)

    raise PlotError("Either indicator_key or group_key must be provided.")
