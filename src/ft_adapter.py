"""
Phase 2 MVP version

Currently supported metrics (stable):
- Gross Margin
- Debt Ratio

Other metrics (ROE, ROIC, P/E) are defined
but may be unavailable depending on data source.

Usage:
- MVP only (default): get_key_metrics("AAPL")  -> returns 2 metrics
- Full list:           get_key_metrics("AAPL", mvp_only=False) -> returns all defined metrics
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, List, Dict
import numpy as np
import pandas as pd

from financetoolkit import Toolkit


@dataclass(frozen=True)
class MetricSpec:
    key: str                # internal metric id
    display_name: str       # name shown in UI
    unit: str               # "%", "x", etc.
    description: str        # short explanation


# 你们项目的“统一口径指标清单”（后面只要改这里就行）
METRICS: List[MetricSpec] = [
    MetricSpec("ROE", "ROE", "%", "Return on Equity: profitability relative to shareholders' equity."),
    MetricSpec("GrossMargin", "Gross Margin", "%", "Gross Profit / Revenue."),
    MetricSpec("DebtRatio", "Debt Ratio", "%", "Total Liabilities / Total Assets."),
    MetricSpec("PE", "P/E", "x", "Price-to-Earnings ratio (valuation multiple)."),
    MetricSpec("ROIC", "ROIC", "%", "Return on Invested Capital (capital efficiency)."),
]


def _as_float(x) -> float:
    """Convert to float if possible."""
    try:
        return float(x)
    except Exception:
        return np.nan


def _clean_missing(series: pd.Series) -> pd.Series:
    """
    Finance data sometimes uses 0.0 as placeholder for missing.
    Convert 0.0 placeholders to NaN *only when it looks like missing*.
    """
    s = series.copy()

    # if the entire series is zeros, keep it (avoid over-cleaning)
    if (pd.to_numeric(s, errors="coerce").fillna(0) == 0).all():
        return pd.to_numeric(s, errors="coerce")

    s_num = pd.to_numeric(s, errors="coerce")

    # Treat exact 0 as missing if there are other non-zero values in the series
    if (s_num == 0).any() and (s_num != 0).any():
        s_num = s_num.replace(0, np.nan)

    return s_num


def _latest_period_from_columns(df: pd.DataFrame) -> Optional[str]:
    """Pick the latest period column (year) if columns look like years."""
    if df is None or df.empty:
        return None
    cols = list(df.columns)

    # try to interpret as ints (years)
    years = []
    for c in cols:
        try:
            years.append(int(str(c)))
        except Exception:
            pass
    if years:
        return str(max(years))

    # fallback: last column
    return str(cols[-1])


def get_key_metrics(ticker: str, mvp_only: bool = True) -> pd.DataFrame:
    """
    Unified interface for core metrics.

    Returns a tidy DataFrame with fields:
    Metric | Value | Period | Unit | Description

    Parameters
    ----------
    ticker : str
        Stock ticker, e.g. "AAPL"
    mvp_only : bool
        If True (default), only return stable MVP metrics:
        - Gross Margin
        - Debt Ratio
        If False, return all defined metrics (may contain NaN for some).
    """
    ticker = ticker.strip().upper()
    tk = Toolkit([ticker])

    # 1) Pull statements (these are reliable for ratios we can compute ourselves)
    income = tk.get_income_statement()
    balance = tk.get_balance_sheet_statement()

    # 2) Determine period (latest year)
    period = _latest_period_from_columns(income) or _latest_period_from_columns(balance) or "Latest"

    # Helper to safely read a value from a statement table
    def stmt_value(stmt: pd.DataFrame, row_name: str, col_name: str) -> float:
        if stmt is None or stmt.empty:
            return np.nan
        if row_name not in stmt.index:
            return np.nan
        if col_name not in stmt.columns:
            return np.nan
        s = _clean_missing(stmt.loc[row_name])
        return _as_float(s.get(col_name, np.nan))

    # 3) Compute / retrieve core metrics (MVP: compute from statements where possible)
    # --- Gross Margin = Gross Profit / Revenue
    revenue = stmt_value(income, "Revenue", period)
    gross_profit = stmt_value(income, "Gross Profit", period)
    gross_margin = (gross_profit / revenue) if (revenue and not np.isnan(revenue) and revenue != 0) else np.nan

    # --- Debt Ratio = Total Liabilities / Total Assets
    total_assets = stmt_value(balance, "Total Assets", period)
    # Some datasets may use "Total Liabilities" or "Total Liabilities Net Minority Interest"
    total_liab = stmt_value(balance, "Total Liabilities", period)
    if np.isnan(total_liab):
        total_liab = stmt_value(balance, "Total Liabilities Net Minority Interest", period)

    debt_ratio = (
        (total_liab / total_assets)
        if (total_assets and not np.isnan(total_assets) and total_assets != 0)
        else np.nan
    )

    # 4) Try to get ROE / ROIC / PE from FinanceToolkit if available
    # Different versions expose different endpoints; we keep it robust:
    roe = np.nan
    roic = np.nan
    pe = np.nan

    # ROE / ROIC sometimes available via ratios module; if not, we’ll leave NaN
    try:
        prof = tk.get_profitability_ratios()
        if prof is not None and not prof.empty:
            p = _latest_period_from_columns(prof) or period
            if "Return on Equity" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["Return on Equity"]).get(p, np.nan))
            elif "ROE" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["ROE"]).get(p, np.nan))
    except Exception:
        pass

    try:
        eff = tk.get_efficiency_ratios()
        if eff is not None and not eff.empty:
            p = _latest_period_from_columns(eff) or period
            if "Return on Invested Capital" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["Return on Invested Capital"]).get(p, np.nan))
            elif "ROIC" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["ROIC"]).get(p, np.nan))
    except Exception:
        pass

    try:
        val = tk.get_valuation_ratios()
        if val is not None and not val.empty:
            p = _latest_period_from_columns(val) or period
            # naming varies
            for candidate in ["Price Earnings Ratio", "P/E", "PE Ratio", "Price to Earnings"]:
                if candidate in val.index:
                    pe = _as_float(_clean_missing(val.loc[candidate]).get(p, np.nan))
                    break
    except Exception:
        pass

    # 5) Assemble tidy output
    values: Dict[str, float] = {
        "ROE": roe,
        "GrossMargin": gross_margin,
        "DebtRatio": debt_ratio,
        "PE": pe,
        "ROIC": roic,
    }

    # MVP only:只返回稳定的两个指标，避免页面/图表出现 NaN
    if mvp_only:
        mvp_keys = {"GrossMargin", "DebtRatio"}
        selected_metrics = [m for m in METRICS if m.key in mvp_keys]
    else:
        selected_metrics = METRICS

    rows = []
    for m in selected_metrics:
        v = values.get(m.key, np.nan)

        # Percent display: keep as ratio if toolkit returns ratio; for now, standardize to percentage number (0.23 -> 23)
        if m.unit == "%" and not np.isnan(v):
            # Heuristic: if value <= 1.5, treat as ratio; else already in percent
            if abs(v) <= 1.5:
                v = v * 100.0

        rows.append(
            {
                "Metric": m.display_name,
                "Value": v,
                "Period": period,
                "Unit": m.unit,
                "Description": m.description,
            }
        )

    return pd.DataFrame(rows)
