# docs/test_ft_adapter.py
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from src.ft_adapter import get_key_metrics

if __name__ == "__main__":
    df = get_key_metrics("AAPL")
    print(df)
