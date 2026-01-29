from src.ft_adapter import get_key_metrics_multi_indicators

res = get_key_metrics_multi_indicators(["AAPL", "MSFT", "NVDA"])

for k, df in res.items():
    print("=== ", k, " ===")
    print(df)
