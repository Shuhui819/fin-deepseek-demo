# docs/test_plots.py
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics
from src.plots import plot_two_metrics_bar

if __name__ == "__main__":
    df = get_key_metrics("AAPL")  # 默认 MVP only
    fig = plot_two_metrics_bar(df, title="AAPL Metrics")

    out_path = "docs/aapl_metrics.png"
    fig.savefig(out_path, dpi=200)
    print(f"Saved plot to: {out_path}")
