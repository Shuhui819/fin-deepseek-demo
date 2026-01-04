from financetoolkit import Toolkit

# 先不填 api_key，能跑就直接跑；如果报错再加 key
companies = Toolkit(["AAPL"])

# 任选一种：财务报表（最符合 T1.2）
income = companies.get_income_statement()
balance = companies.get_balance_sheet_statement()
cashflow = companies.get_cash_flow_statement()

print("=== Income Statement ===")
print(income.head())

print("\n=== Balance Sheet ===")
print(balance.head())

print("\n=== Cash Flow ===")
print(cashflow.head())
