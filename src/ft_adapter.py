"""
Phase 1 MVP + Timeseries Upgrade

Two output modes:
- output="tidy":      your original MVP snapshot table (Metric/Value/Period/Unit/Description)
- output="timeseries": time series df for plotting (index=year, columns=indicator_key)

Default output = "timeseries" (so app can draw line charts).
"""

from __future__ import annotations

from dotenv import load_dotenv
load_dotenv()

from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import os

import numpy as np
import pandas as pd

from financetoolkit import Toolkit


# -----------------------------
# Existing tidy metric specs (kept)
# -----------------------------
@dataclass(frozen=True)
class MetricSpec:
    key: str
    display_name: str
    unit: str
    description: str


METRICS: List[MetricSpec] = [
    MetricSpec("ROE", "ROE", "%", "Return on Equity: profitability relative to shareholders' equity."),
    MetricSpec("GrossMargin", "Gross Margin", "%", "Gross Profit / Revenue."),
    MetricSpec("DebtRatio", "Debt Ratio", "%", "Total Liabilities / Total Assets."),
    MetricSpec("PE", "P/E", "x", "Price-to-Earnings ratio (valuation multiple)."),
    MetricSpec("ROIC", "ROIC", "%", "Return on Invested Capital (capital efficiency)."),
]


# -----------------------------
# Helpers (from your original, kept)
# -----------------------------
def _as_float(x) -> float:
    try:
        return float(x)
    except Exception:
        return np.nan


def _clean_missing(series: pd.Series) -> pd.Series:
    """
    Finance data sometimes uses 0.0 as placeholder for missing.
    Convert 0.0 placeholders to NaN only when it looks like missing.
    """
    s = series.copy()

    # if entire series zeros -> keep it
    if (pd.to_numeric(s, errors="coerce").fillna(0) == 0).all():
        return pd.to_numeric(s, errors="coerce")

    s_num = pd.to_numeric(s, errors="coerce")

    # Treat exact 0 as missing if there are other non-zero values
    if (s_num == 0).any() and (s_num != 0).any():
        s_num = s_num.replace(0, np.nan)

    return s_num


def _latest_period_from_columns(df: pd.DataFrame) -> Optional[Any]:
    if df is None or df.empty:
        return None
    cols = df.columns
    try:
        return cols.max()
    except Exception:
        return cols[-1] if len(cols) > 0 else None


# -----------------------------
# Toolkit init with FMP -> Yahoo fallback (same idea as yours)
# -----------------------------
def _unwrap_statement(obj: Any, ticker: str) -> pd.DataFrame:
    """Unwrap FinanceToolkit return types: DataFrame or dict[ticker] -> DataFrame."""
    if obj is None:
        return pd.DataFrame()
    if isinstance(obj, dict):
        df = obj.get(ticker)
        return df if isinstance(df, pd.DataFrame) else pd.DataFrame()
    if isinstance(obj, pd.DataFrame):
        return obj
    return pd.DataFrame()


def _init_toolkit(ticker: str, api_key: Optional[str], inspect: bool) -> Tuple[Toolkit, str]:
    ticker = ticker.strip().upper()
    fmp_key = api_key or os.getenv("FMP_API_KEY")

    # Try FMP first
    if fmp_key:
        if inspect:
            print(f"[DEBUG] Attempting FinancialModelingPrep (key length: {len(fmp_key)})")
        try:
            tk = Toolkit([ticker], api_key=fmp_key, progress_bar=False, quarterly=False, sleep_timer=0.1)
            test_income = _unwrap_statement(tk.get_income_statement(), ticker)
            if test_income is not None and not test_income.empty:
                if inspect:
                    print("[SUCCESS] Using FinancialModelingPrep")
                return tk, "FinancialModelingPrep"
            if inspect:
                print("[WARN] FMP returned empty. Falling back to Yahoo Finance...")
        except Exception as e:
            if inspect:
                print(f"[ERROR] FMP failed: {e}. Falling back to Yahoo Finance...")

    # Fallback to Yahoo
    if inspect:
        print("[DEBUG] Using Yahoo Finance (free, may rate limit)")
    tk = Toolkit([ticker], progress_bar=False)
    return tk, "Yahoo Finance"


# ============================================================
# 1) TIDY SNAPSHOT API (your original behavior, preserved)
# ============================================================
def get_key_metrics_tidy(
    ticker: str,
    mvp_only: bool = True,
    inspect: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Returns a tidy snapshot DataFrame:
    Metric | Value | Period | Unit | Description
    """
    ticker = ticker.strip().upper()
    tk, data_source = _init_toolkit(ticker, api_key=api_key, inspect=inspect)

    income = pd.DataFrame()
    balance = pd.DataFrame()

    try:
        income = _unwrap_statement(tk.get_income_statement(), ticker)
    except Exception as e:
        if inspect:
            print(f"[ERROR] Failed to get income statement: {e}")

    try:
        balance = _unwrap_statement(tk.get_balance_sheet_statement(), ticker)
    except Exception as e:
        if inspect:
            print(f"[ERROR] Failed to get balance sheet: {e}")

    if inspect:
        print("\n========== L1-1 INSPECT ==========")
        print(f"Data Source: {data_source}")
        print("INCOME shape:", getattr(income, "shape", None))
        print("BALANCE shape:", getattr(balance, "shape", None))
        print("INCOME COLUMNS (first 30):", list(getattr(income, "columns", []))[:30])
        print("BALANCE COLUMNS (first 30):", list(getattr(balance, "columns", []))[:30])
        print("INCOME INDEX (first 60):", list(getattr(income, "index", []))[:60])
        print("BALANCE INDEX (first 60):", list(getattr(balance, "index", []))[:60])
        print("=================================\n")

        if income is None or income.empty:
            print("[WARN] Income statement is empty.")
        if balance is None or balance.empty:
            print("[WARN] Balance sheet is empty.")

    # latest period
    period = _latest_period_from_columns(income)
    if period is None:
        period = _latest_period_from_columns(balance)

    # helper to read value safely
    def stmt_value(stmt: pd.DataFrame, row_name: str, col: Any) -> float:
        if stmt is None or stmt.empty:
            return np.nan
        if row_name not in stmt.index:
            return np.nan
        if col not in stmt.columns:
            return np.nan
        s = _clean_missing(stmt.loc[row_name])
        return _as_float(s.get(col, np.nan))

    # MVP computed metrics
    revenue = stmt_value(income, "Revenue", period) if period is not None else np.nan
    gross_profit = stmt_value(income, "Gross Profit", period) if period is not None else np.nan
    gross_margin = (gross_profit / revenue) if (not np.isnan(revenue) and revenue != 0) else np.nan

    total_assets = stmt_value(balance, "Total Assets", period) if period is not None else np.nan
    total_liab = stmt_value(balance, "Total Liabilities", period) if period is not None else np.nan
    if np.isnan(total_liab):
        total_liab = stmt_value(balance, "Total Liabilities Net Minority Interest", period) if period is not None else np.nan
    debt_ratio = (total_liab / total_assets) if (not np.isnan(total_assets) and total_assets != 0) else np.nan

    # Optional ratios (best-effort)
    roe = np.nan
    roic = np.nan
    pe = np.nan

    try:
        prof = _unwrap_statement(tk.get_profitability_ratios(), ticker)
        if prof is not None and not prof.empty:
            p = _latest_period_from_columns(prof) or period
            if "Return on Equity" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["Return on Equity"]).get(p, np.nan))
            elif "ROE" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["ROE"]).get(p, np.nan))
    except Exception:
        pass

    try:
        eff = _unwrap_statement(tk.get_efficiency_ratios(), ticker)
        if eff is not None and not eff.empty:
            p = _latest_period_from_columns(eff) or period
            if "Return on Invested Capital" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["Return on Invested Capital"]).get(p, np.nan))
            elif "ROIC" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["ROIC"]).get(p, np.nan))
    except Exception:
        pass

    try:
        val = _unwrap_statement(tk.get_valuation_ratios(), ticker)
        if val is not None and not val.empty:
            p = _latest_period_from_columns(val) or period
            for candidate in ["Price Earnings Ratio", "P/E", "PE Ratio", "Price to Earnings"]:
                if candidate in val.index:
                    pe = _as_float(_clean_missing(val.loc[candidate]).get(p, np.nan))
                    break
    except Exception:
        pass

    values: Dict[str, float] = {
        "ROE": roe,
        "GrossMargin": gross_margin,
        "DebtRatio": debt_ratio,
        "PE": pe,
        "ROIC": roic,
    }

    if mvp_only:
        mvp_keys = {"GrossMargin", "DebtRatio"}
        selected_metrics = [m for m in METRICS if m.key in mvp_keys]
    else:
        selected_metrics = METRICS

    period_str = str(period) if period is not None else "Latest"

    rows = []
    for m in selected_metrics:
        v = values.get(m.key, np.nan)

        # percent formatting heuristic for tidy table
        if m.unit == "%" and not np.isnan(v):
            if abs(v) <= 1.5:
                v = v * 100.0

        rows.append(
            {
                "Metric": m.display_name,
                "Value": v,
                "Period": period_str,
                "Unit": m.unit,
                "Description": m.description,
            }
        )

    return pd.DataFrame(rows)


# ============================================================
# 2) TIMESERIES API (for line charts)
# ============================================================
def _norm(s: str) -> str:
    return str(s).strip().lower()


def _find_row_key(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
    """Find best matching row name in df.index (case-insensitive)."""
    if df is None or df.empty:
        return None

    idx = [str(x) for x in df.index]
    idx_norm = [_norm(x) for x in idx]
    cand_norm = [_norm(c) for c in candidates]

    # exact
    for c in cand_norm:
        for i, v in enumerate(idx_norm):
            if v == c:
                return idx[i]

    # contains fallback
    for c in cand_norm:
        for i, v in enumerate(idx_norm):
            if c in v:
                return idx[i]

    return None


def _periods_to_year_index(cols: pd.Index) -> List[str]:
    years: List[str] = []
    for col in cols:
        s = str(col)
        if len(s) >= 4 and s[:4].isdigit():
            years.append(s[:4])
        else:
            years.append(s)
    return years


def _series_by_row(df: pd.DataFrame, row_key: Optional[str]) -> pd.Series:
    """Extract numeric series from a statement row, indexed by year string."""
    if df is None or df.empty or row_key is None or row_key not in df.index:
        return pd.Series(dtype=float)

    s = _clean_missing(df.loc[row_key])
    s.index = _periods_to_year_index(s.index)
    s = s[~pd.Index(s.index).duplicated(keep="last")]
    s = pd.to_numeric(s, errors="coerce")
    try:
        s = s.sort_index()
    except Exception:
        pass
    return s


def _safe_divide_series(a: pd.Series, b: pd.Series) -> pd.Series:
    a = pd.to_numeric(a, errors="coerce")
    b = pd.to_numeric(b, errors="coerce")
    out = a / b
    out = out.replace([np.inf, -np.inf], np.nan)
    return out


def get_key_metrics_timeseries(
    ticker: str,
    periods: str = "all",
    inspect: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Return time series metrics:
      index = year (string)
      columns = indicator_key:
        gross_margin, operating_margin, roe, debt_ratio, current_ratio
    """
    ticker = ticker.strip().upper()
    tk, data_source = _init_toolkit(ticker, api_key=api_key, inspect=inspect)

    income = _unwrap_statement(tk.get_income_statement(), ticker)
    balance = _unwrap_statement(tk.get_balance_sheet_statement(), ticker)

    if inspect:
        print("\n========== TIMESERIES INSPECT ==========")
        print(f"Data Source: {data_source}")
        print("INCOME shape:", income.shape)
        print("BALANCE shape:", balance.shape)
        print("INCOME index sample:", list(income.index)[:30])
        print("BALANCE index sample:", list(balance.index)[:30])
        print("INCOME columns sample:", list(income.columns)[:10])
        print("BALANCE columns sample:", list(balance.columns)[:10])
        print("=======================================\n")

    # robust row matching
    k_revenue = _find_row_key(income, ["Revenue", "Total Revenue", "Net Revenue", "Revenues"])
    k_gross_profit = _find_row_key(income, ["Gross Profit", "GrossProfit"])
    k_operating_income = _find_row_key(income, ["Operating Income", "Income From Operations", "OperatingIncome"])
    k_net_income = _find_row_key(income, ["Net Income", "NetIncome", "Net Income Common Stockholders"])

    k_total_assets = _find_row_key(balance, ["Total Assets", "TotalAssets"])
    k_total_liab = _find_row_key(balance, ["Total Liabilities", "Total Liabilities Net Minority Interest", "TotalLiabilities"])
    k_current_assets = _find_row_key(balance, ["Total Current Assets", "Current Assets", "TotalCurrentAssets"])
    k_current_liab = _find_row_key(balance, ["Total Current Liabilities", "Current Liabilities", "TotalCurrentLiabilities"])
    k_total_equity = _find_row_key(balance, ["Total Stockholders Equity", "Total Equity", "Total Shareholders Equity"])

    revenue = _series_by_row(income, k_revenue)
    gross_profit = _series_by_row(income, k_gross_profit)
    operating_income = _series_by_row(income, k_operating_income)
    net_income = _series_by_row(income, k_net_income)

    total_assets = _series_by_row(balance, k_total_assets)
    total_liab = _series_by_row(balance, k_total_liab)
    current_assets = _series_by_row(balance, k_current_assets)
    current_liab = _series_by_row(balance, k_current_liab)
    total_equity = _series_by_row(balance, k_total_equity)

    # union years
    all_years = sorted(
        set(revenue.index)
        | set(gross_profit.index)
        | set(operating_income.index)
        | set(net_income.index)
        | set(total_assets.index)
        | set(total_liab.index)
        | set(current_assets.index)
        | set(current_liab.index)
        | set(total_equity.index)
    )

    if not all_years:
        return pd.DataFrame()

    def r(s: pd.Series) -> pd.Series:
        return s.reindex(all_years)

    revenue = r(revenue)
    gross_profit = r(gross_profit)
    operating_income = r(operating_income)
    net_income = r(net_income)

    total_assets = r(total_assets)
    total_liab = r(total_liab)
    current_assets = r(current_assets)
    current_liab = r(current_liab)
    total_equity = r(total_equity)

    # IMPORTANT: keep as decimals for plotting; formatting later if needed
    gross_margin = _safe_divide_series(gross_profit, revenue)
    operating_margin = _safe_divide_series(operating_income, revenue)
    roe = _safe_divide_series(net_income, total_equity)
    debt_ratio = _safe_divide_series(total_liab, total_assets)
    current_ratio = _safe_divide_series(current_assets, current_liab)

    df = pd.DataFrame(
        {
            "gross_margin": gross_margin,
            "operating_margin": operating_margin,
            "roe": roe,
            "debt_ratio": debt_ratio,
            "current_ratio": current_ratio,
        },
        index=pd.Index(all_years, name="year"),
    )

    # periods handling
    p = str(periods).lower().strip()
    if p not in ("all", ""):
        if p in ("latest", "last", "1"):
            df = df.tail(1)
        else:
            try:
                n = int(periods)
                df = df.tail(n)
            except Exception:
                pass

    return df


# ============================================================
# 3) Unified public wrapper (THIS is what app imports)
# ============================================================
def get_key_metrics(
    ticker: str,
    *,
    output: str = "timeseries",
    periods: str = "all",
    mvp_only: bool = True,
    inspect: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
    """
    Unified API.

    output="timeseries":
      index=year, columns=indicator_key (gross_margin, operating_margin, roe, debt_ratio, current_ratio)

    output="tidy":
      your original snapshot table (Metric/Value/Period/Unit/Description)
    """
    mode = str(output).lower().strip()
    if mode in ("timeseries", "ts", "series"):
        return get_key_metrics_timeseries(ticker, periods=periods, inspect=inspect, api_key=api_key)
    if mode in ("tidy", "snapshot"):
        return get_key_metrics_tidy(ticker, mvp_only=mvp_only, inspect=inspect, api_key=api_key)
    raise ValueError(f"Unknown output={output}. Use 'timeseries' or 'tidy'.")

def get_key_metrics_multi_indicators(
    tickers: list[str],
    *,
    output: str = "timeseries",
    periods: str = "all",
    mvp_only: bool = False,
    inspect: bool = False,
    api_key: str | None = None,
):
    """
    返回格式：
    {
        "GrossMargin": DataFrame,
        "DebtRatio": DataFrame,
        "ROE": DataFrame,
        ...
    }

    每个 DataFrame 结构：
        Year | AAPL | MSFT | NVDA | ...
    """
    if not tickers:
        raise ValueError("tickers must be a non-empty list")

    # 用原函数加载每个 ticker 的 timeseries
    all_data = {}
    for t in tickers:
        df = get_key_metrics(
            t,
            output="timeseries",
            periods=periods,
            mvp_only=mvp_only,
            inspect=inspect,
            api_key=api_key,
        )

        if df is None or df.empty:
            continue

        # Index must be string or int year
        df = df.copy()
        df.index = df.index.astype(str)

        all_data[t] = df

    if not all_data:
        raise ValueError("No valid data for any ticker.")

    # 统一指标列表
    metrics = list(all_data[tickers[0]].columns)

    # final result
    result = {}

    for metric in metrics:
        frames = []
        for t, df in all_data.items():
            if metric not in df.columns:
                continue

            # 取出这个指标并重命名成该公司的列
            s = df[[metric]].rename(columns={metric: t})

            frames.append(s)

        if frames:
            # 合并所有公司该指标的列（按年份对齐）
            merged = pd.concat(frames, axis=1)
            result[metric] = merged

    return result
