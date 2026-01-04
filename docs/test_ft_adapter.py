# docs/test_ft_adapter.py

from src.ft_adapter import get_key_metrics

if __name__ == "__main__":
    df = get_key_metrics("AAPL")
    print(df)
