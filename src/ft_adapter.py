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
- Inspect statements:  get_key_metrics("AAPL", inspect=True)   -> prints columns/index for L1-1

Note: Ensure load_dotenv() is called in your application entry point (app.py or test scripts)
      before importing this module if using .env files.
"""

from __future__ import annotations
from dotenv import load_dotenv
load_dotenv()  # 这会自动加载 .env 文件中的环境变量

from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import os

import numpy as np
import pandas as pd

from financetoolkit import Toolkit


@dataclass(frozen=True)
class MetricSpec:
    key: str                # internal metric id
    display_name: str       # name shown in UI
    unit: str               # "%", "x", etc.
    description: str        # short explanation


# 统一口径指标清单（后续扩展只改这里 + values 的计算/获取）
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


def _latest_period_from_columns(df: pd.DataFrame) -> Optional[Any]:
    """
    Pick the latest period column, preserving its original type (Period/Datetime/etc).
    This ensures we can match it against the actual DataFrame columns.
    """
    if df is None or df.empty:
        return None
    
    cols = df.columns
    
    try:
        # For PeriodIndex/DatetimeIndex, max() works directly
        return cols.max()
    except Exception:
        # Fallback: return last column as-is
        return cols[-1] if len(cols) > 0 else None


def get_key_metrics(
    ticker: str,
    mvp_only: bool = True,
    inspect: bool = False,
    api_key: Optional[str] = None,
) -> pd.DataFrame:
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
    inspect : bool
        If True, print statement shapes/columns/index (for L1-1 data coverage inspection).
    api_key : str, optional
        FinancialModelingPrep API key. If not provided, will try to read from 
        environment variable FMP_API_KEY. If still not available, will fall back 
        to Yahoo Finance (which may have rate limits).
    """
    ticker = ticker.strip().upper()
    
    # Get API key from parameter or environment variable
    fmp_key = api_key or os.getenv("FMP_API_KEY")
    
    # Try FMP first if key is available, but be ready to fallback to Yahoo
    tk = None
    data_source = "Unknown"
    
    if fmp_key:
        if inspect:
            print(f"[DEBUG] Attempting to use FinancialModelingPrep (API key length: {len(fmp_key)})")
        
        try:
            tk = Toolkit(
                [ticker],
                api_key=fmp_key,
                progress_bar=False,
                quarterly=False,
                sleep_timer=0.1,
            )
            
            # Quick test to see if FMP works (try to get a small piece of data)
            test_income = tk.get_income_statement()
            if test_income is None or test_income.empty:
                if inspect:
                    print("[WARN] FMP returned empty data (likely free tier limitation)")
                    print("[INFO] Falling back to Yahoo Finance...")
                tk = None  # Trigger fallback
            else:
                data_source = "FinancialModelingPrep"
                if inspect:
                    print("[SUCCESS] Using FinancialModelingPrep")
        except Exception as e:
            if inspect:
                print(f"[ERROR] FMP failed: {e}")
                print("[INFO] Falling back to Yahoo Finance...")
            tk = None
    
    # Fallback to Yahoo Finance if FMP not available or failed
    if tk is None:
        if inspect:
            print("[DEBUG] Using Yahoo Finance (free, but may have rate limits)")
        
        tk = Toolkit(
            [ticker],
            progress_bar=False,
        )
        data_source = "Yahoo Finance"

    # 1) Pull statements (reliable for ratios we can compute ourselves)
    income = pd.DataFrame()
    balance = pd.DataFrame()
    
    # If we already tested income in the FMP check, reuse it
    if data_source == "FinancialModelingPrep" and 'test_income' in locals():
        income = test_income
    else:
        try:
            income = tk.get_income_statement()
        except Exception as e:
            if inspect:
                print(f"[ERROR] Failed to get income statement: {e}")
    
    try:
        balance = tk.get_balance_sheet_statement()
    except Exception as e:
        if inspect:
            print(f"[ERROR] Failed to get balance sheet: {e}")

    # --- L1-1: data coverage inspection (only when inspect=True) ---
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

        # Only print warnings in inspect mode (avoid Streamlit console spam)
        if income is None or income.empty:
            print("[WARN] Income statement is empty. Possible reasons:")
            print("       - Yahoo Finance rate limits (if no API key)")
            print("       - Invalid API key")
            print("       - Network issues")
            print("       - Invalid ticker symbol")

        if balance is None or balance.empty:
            print("[WARN] Balance sheet is empty. See reasons above.")

    # 2) Determine period (latest year) - keep original type (Period/Datetime)
    # Explicitly check None to avoid relying on truthiness of Period objects
    period = _latest_period_from_columns(income)
    if period is None:
        period = _latest_period_from_columns(balance)
    
    if inspect and period is not None:
        print(f"[DEBUG] Latest period: {period} (type: {type(period).__name__})")

    # Helper to safely read a value from a statement table
    def stmt_value(stmt: pd.DataFrame, row_name: str, col: Any) -> float:
        """
        Extract value from statement, using the original column object (not string).
        """
        if stmt is None or stmt.empty:
            return np.nan
        if row_name not in stmt.index:
            return np.nan
        if col not in stmt.columns:
            return np.nan
        s = _clean_missing(stmt.loc[row_name])
        return _as_float(s.get(col, np.nan))

    # 3) Compute / retrieve core metrics (MVP: compute from statements where possible)

    # --- Gross Margin = Gross Profit / Revenue
    revenue = stmt_value(income, "Revenue", period) if period else np.nan
    gross_profit = stmt_value(income, "Gross Profit", period) if period else np.nan
    gross_margin = (gross_profit / revenue) if (not np.isnan(revenue) and revenue != 0) else np.nan

    # --- Debt Ratio = Total Liabilities / Total Assets
    total_assets = stmt_value(balance, "Total Assets", period) if period else np.nan

    # Some datasets may use "Total Liabilities" or "Total Liabilities Net Minority Interest"
    total_liab = stmt_value(balance, "Total Liabilities", period) if period else np.nan
    if np.isnan(total_liab):
        total_liab = stmt_value(balance, "Total Liabilities Net Minority Interest", period) if period else np.nan

    debt_ratio = (total_liab / total_assets) if (not np.isnan(total_assets) and total_assets != 0) else np.nan

    # Debug values if requested
    if inspect:
        print(f"[DEBUG] Revenue: {revenue}")
        print(f"[DEBUG] Gross Profit: {gross_profit}")
        print(f"[DEBUG] Gross Margin: {gross_margin}")
        print(f"[DEBUG] Total Assets: {total_assets}")
        print(f"[DEBUG] Total Liabilities: {total_liab}")
        print(f"[DEBUG] Debt Ratio: {debt_ratio}\n")

    # 4) Try to get ROE / ROIC / PE from FinanceToolkit if available
    roe = np.nan
    roic = np.nan
    pe = np.nan

    # ROE sometimes available via profitability ratios
    try:
        prof = tk.get_profitability_ratios()
        if prof is not None and not prof.empty:
            p = _latest_period_from_columns(prof)
            if p is None:
                p = period
            if "Return on Equity" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["Return on Equity"]).get(p, np.nan))
            elif "ROE" in prof.index:
                roe = _as_float(_clean_missing(prof.loc["ROE"]).get(p, np.nan))
    except Exception:
        pass

    # ROIC sometimes available via efficiency ratios
    try:
        eff = tk.get_efficiency_ratios()
        if eff is not None and not eff.empty:
            p = _latest_period_from_columns(eff)
            if p is None:
                p = period
            if "Return on Invested Capital" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["Return on Invested Capital"]).get(p, np.nan))
            elif "ROIC" in eff.index:
                roic = _as_float(_clean_missing(eff.loc["ROIC"]).get(p, np.nan))
    except Exception:
        pass

    # P/E sometimes available via valuation ratios
    try:
        val = tk.get_valuation_ratios()
        if val is not None and not val.empty:
            p = _latest_period_from_columns(val)
            if p is None:
                p = period
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

    # MVP only: 只返回稳定的两个指标，避免页面/图表出现 NaN
    if mvp_only:
        mvp_keys = {"GrossMargin", "DebtRatio"}
        selected_metrics = [m for m in METRICS if m.key in mvp_keys]
    else:
        selected_metrics = METRICS

    # Format period for display (convert to string for output)
    period_str = str(period) if period else "Latest"

    rows = []
    for m in selected_metrics:
        v = values.get(m.key, np.nan)

        # Percent display: standardize to percentage number (0.23 -> 23)
        # Note: This heuristic works for current MVP metrics (Gross Margin, Debt Ratio)
        # May need per-metric handling when expanding to other metrics
        if m.unit == "%" and not np.isnan(v):
            # Heuristic: if value <= 1.5, treat as ratio; else already in percent
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