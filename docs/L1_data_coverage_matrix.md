# L1-1 数据覆盖矩阵文档

 版本 : 1.0  
 日期 : 2026-01-09  
 状态 : ✅ 已验证通过  
 测试环境 : Windows 11, Python 3.x, financetoolkit

---

## 📋 执行摘要

本文档记录了 `ft_adapter.py` 模块在 Level 1 阶段的数据源覆盖情况、可用指标清单以及数据质量验证结果。

 核心结论： 

* ✅ 已完成年度三表数据获取链路，并实现"多数据源 + 自动回退 + 调试诊断（inspect）"机制。
* ⚠️ Yahoo Finance 可能因速率限制导致空表；FMP 可能因套餐/接口限制（premium 参数）导致空表。
* ✅ 系统在数据缺失时不会崩溃：指标返回 NaN 且保留一致输出结构，确保 Demo 可运行。
* ✅ MVP 指标（Gross Margin、Debt Ratio）已验证可从三表字段自计算，口径可追溯。
* ✅ 年度覆盖范围以实际返回列为准（通常最近 4–5 年），latest period 自动选取。

 "稳定"的定义：  本项目将"稳定"定义为：即便数据源短暂不可用，系统仍能返回结构化结果（含 NaN）并给出诊断信息，保证 Demo 可运行与可复现。

---

## 1. 数据源策略

### 1.1 数据源优先级与实际表现

| 数据源 | 理论优势 | 实际限制 | 应对策略 |
|--------|----------|----------|----------|
| FinancialModelingPrep (FMP) | 官方 API，数据完整 | 免费/低阶套餐下，部分财报/参数受限（premium query parameter） | 自动检测空表并回退 |
| Yahoo Finance | 免费，无需 API key | 速率限制，频繁请求可能返回空表 | 作为回退方案 |

 关键认知：  两个数据源都不绝对"稳定"；真正稳定的是 容错机制 + 自动回退逻辑 。

### 1.2 自动回退逻辑

```
尝试 FMP (如果有 API key)
    ↓
检测返回数据是否为空
    ↓
    ├─ 有数据 → 使用 FMP
    └─ 无数据 → 自动回退到 Yahoo Finance
         ↓
         检测 Yahoo 返回
         ↓
         ├─ 有数据 → 使用 Yahoo Finance
         └─ 无数据 → 返回 NaN，不崩溃
```

 验证结果  (测试股票: F - Ford Motor Company, 测试时间: 2026-01-09 14:38):

```
[DEBUG] Attempting to use FinancialModelingPrep (API key length: 32)
[WARN] FMP returned empty data (likely free tier limitation)
[INFO] Falling back to Yahoo Finance...
[DEBUG] Using Yahoo Finance (free, but may have rate limits)
Data Source: Yahoo Finance ✅
```

---

## 2. 数据覆盖矩阵

### 2.1 Income Statement 覆盖度

 本次测试维度  (Ford, 2026-01-09): 35 行 × 4 列 (2021-2024)

#### 核心指标 (MVP 使用)

| 指标名称 | Index 名称 | Raw/Derived | 可用性 | 用途 |
|----------|-----------|-------------|--------|------|
| Revenue | `Revenue` | Raw | ✅ | Gross Margin 计算分母 |
| Gross Profit | `Gross Profit` | Raw | ✅ | Gross Margin 计算分子 |
| Gross Margin | - | Derived | ✅ | MVP 核心指标 (Gross Profit / Revenue) |
| Operating Income | `Operating Income` | Raw | ✅ | 可扩展指标 (Operating Margin) |
| Net Income | `Net Income` | Raw | ✅ | 可扩展指标 (ROE) |
| EBIT | `EBIT` | Raw | ✅ | 可扩展指标 |
| EBITDA | `EBITDA` | Raw | ✅ | 可扩展指标 |

#### 完整指标列表 (35 项)

<details>
<summary>点击展开完整列表</summary>

1. Revenue
2. Operating Revenue
3. Cost of Goods Sold
4. Gross Profit
5. Operating Expenses
6. Selling, General and Administrative Expenses
7. Research and Development Expenses
8. Operating Income
9. Net Non Operating Interest Income Expense
10. Interest Income Non Operating
11. Interest Expense Non Operating
12. Total Other Income Expenses
13. Other Non Operating Income Expenses
14. Income Before Tax
15. Income Tax Expense
16. Net Income Common Stockholders
17. Diluted NI Available to Common Stockholders
18. EPS
19. EPS Diluted
20. Weighted Average Shares
21. Weighted Average Shares Diluted
22. Total Operating Income as Reported
23. Cost and Expenses
24. Net Income from Continuing and Discontinued Operation
25. Normalized Income
26. Net Income
27. Interest Income
28. Interest Expense
29. EBIT
30. EBITDA
31. Reconciled Cost of Revenue
32. Reconciled Depreciation
33. Net Income from Continuing Operation Net Minority Interest
34. Normalized EBITDA
35. Tax Rate for Calcs

</details>

### 2.2 Balance Sheet 覆盖度

 本次测试维度  (Ford, 2026-01-09): 73 行 × 4 列 (2021-2024)

#### 核心指标 (MVP 使用)

| 指标名称 | Index 名称 | Raw/Derived | 可用性 | 用途 |
|----------|-----------|-------------|--------|------|
| Total Assets | `Total Assets` | Raw | ✅ | Debt Ratio 计算分母 |
| Total Liabilities | `Total Liabilities` | Raw | ✅ | Debt Ratio 计算分子 |
| Debt Ratio | - | Derived | ✅ | MVP 核心指标 (Total Liabilities / Total Assets) |
| Total Equity | `Total Equity` | Raw | ✅ | 可扩展指标 (ROE) |
| Total Current Assets | `Total Current Assets` | Raw | ✅ | 可扩展指标 (Current Ratio) |
| Total Current Liabilities | `Total Current Liabilities` | Raw | ✅ | 可扩展指标 (Current Ratio) |

#### 完整指标列表 (73 项)

<details>
<summary>点击展开完整列表 (按资产/负债/权益分类)</summary>

 资产类 (Assets) - 31 项 
1. Total Assets
2. Total Current Assets
3. Cash and Short Term Investments
4. Cash and Cash Equivalents
5. Cash Financials
6. Cash Equivalents
7. Short Term Investments
8. Net Receivables
9. Accounts Receivable
10. Other Receivables
11. Inventory
12. Other Current Assets
13. Fixed Assets
14. Goodwill and Intangible Assets
15. Goodwill
16. Intangible Assets
17. Property, Plant and Equipment
18. Gross Property, Plant and Equipment
19. Land and Improvements
20. Machinery, Furniture and Equipment
21. Properties
22. Other Properties
23. Leases
24. Accumulated Depreciation
25. Investments and Advances
26. Investment in Financial Assets
27. Available for Sale Securities
28. Other Investments
29. Non Current Deferred Assets
30. Non Current Deferred Taxes Assets
31. Other Fixed Assets

 负债类 (Liabilities) - 21 项 
32. Total Liabilities
33. Total Current Liabilities
34. Payables and Accrued Expenses
35. Payables
36. Accounts Payable
37. Tax Payables
38. Income Tax Payable
39. Current Debt and Capital Lease Obligations
40. Current Debt
41. Commercial Paper
42. Other Current Borrowings
43. Current Capital Lease Obligation
44. Current Deferred Liabilities
45. Deferred Revenue
46. Other Current Liabilities
47. Total Non Current Liabilities
48. Long Term Debt and Capital Lease Obligation
49. Long Term Debt
50. Long Term Capital Lease Obligation
51. Trade and Other Payables Non Current
52. Other Non Current Liabilities

 权益类 (Equity) - 8 项 
53. Total Equity
54. Total Shareholder Equity
55. Capital Stock
56. Common Stock
57. Preferred Stock
58. Retained Earnings
59. Gains and Losses Not Affecting Retained Earnings
60. Other Equity Adjustments

 其他细分科目  - 13 项

</details>

### 2.3 时间维度

| 维度 | 值 | 说明 |
|------|-----|------|
| 数据类型 | 年度报表 (Annual) | 当前实现仅验证年度链路；季度数据尚未纳入覆盖矩阵与指标一致性验证 |
| 时间范围 | 根据返回结果动态确定 | 通常为最近 4–5 年；本次测试为 2021-2024 (4 年) |
| 列格式 | `Period('YYYY', 'Y-DEC')` | Pandas PeriodIndex 对象 |
| 最新期间 | 由 `_latest_period_from_columns()` 自动选取 | 本次测试为 `Period('2024', 'Y-DEC')` |

---

## 3. MVP 指标实现状态

### 3.1 已实现指标 (Stable)

| 指标 | 公式 | 数据源 | Raw/Derived | 状态 |
|------|------|--------|-------------|------|
|  Gross Margin  | Gross Profit / Revenue | Income Statement | Derived | ✅ 稳定 |
|  Debt Ratio  | Total Liabilities / Total Assets | Balance Sheet | Derived | ✅ 稳定 |

#### 验证数据 

 测试对象 : Ford Motor Company (F)  
 数据源 : Yahoo Finance  
 获取时间 : 2026-01-09 14:38 UTC+8  
 财年 : 2024

```
Revenue:            $184,992,000,000
Gross Profit:       $ 15,506,000,000
Gross Margin:       8.38% ✅
                    计算: 15.506B / 184.992B = 0.0838
                    显示: 8.381984085798305%

Total Assets:       $285,196,000,000
Total Liabilities:  $240,338,000,000
Debt Ratio:         84.27% ✅
                    计算: 240.338B / 285.196B = 0.8427
                    显示: 84.271167898568%
```

### 3.2 可扩展指标 (Defined but not in MVP)

| 指标 | 公式 | 数据依赖 | Raw/Derived | 优先级 |
|------|------|----------|-------------|--------|
|  ROE  | Net Income / Total Equity | Income + Balance | Derived | P1 |
|  Current Ratio  | Current Assets / Current Liabilities | Balance | Derived | P1 |
|  Operating Margin  | Operating Income / Revenue | Income | Derived | P2 |
|  Asset Turnover  | Revenue / Total Assets | Income + Balance | Derived | P2 |
|  ROIC  | NOPAT / Invested Capital | Income + Balance | Derived | P3 |
|  P/E Ratio  | Market Price / EPS | Income + Market Data | Derived | P3 |

*注: P1 = 高优先级 (可从现有 Raw 字段直接计算), P2 = 中优先级, P3 = 低优先级 (需额外数据源)*

---

## 4. 数据质量验证

### 4.1 Period 类型处理

 测试场景 : 确保 Period 对象正确匹配列名

```python
# 列名类型
INCOME COLUMNS: [Period('2021', 'Y-DEC'), Period('2022', 'Y-DEC'), 
                 Period('2023', 'Y-DEC'), Period('2024', 'Y-DEC')]

# 提取逻辑
period = _latest_period_from_columns(income)  # 返回 Period 对象
# Result: Period('2024', 'Y-DEC') ✅

# 值提取
revenue = stmt_value(income, "Revenue", period)
# 使用原始 Period 对象匹配列，成功取值 ✅
```

 验证结果 : ✅ 通过 - Period 对象类型保持一致，列匹配成功

### 4.2 百分比单位转换

 规则 : 如果原始值 ≤ 1.5，视为比率，乘以 100 转为百分比

| 原始值 | 判断 | 转换后 | 显示 |
|--------|------|--------|------|
| 0.0838 | ≤ 1.5 → 比率 | 8.38 | 8.38% ✅ |
| 0.8427 | ≤ 1.5 → 比率 | 84.27 | 84.27% ✅ |
| 25.5 | > 1.5 → 已是百分比 | 25.5 | 25.5% |

 验证结果 : ✅ 通过 - 适用于当前 MVP 指标 (Gross Margin, Debt Ratio)

 已知限制 : 此启发式规则可能不适用于所有指标（如 ROE 超过 150% 的情况），需在扩展指标时按指标类型分别处理。

### 4.3 缺失值处理

 策略 :
- ✅ 空 DataFrame → 返回 NaN
- ✅ 缺失行名 → 返回 NaN
- ✅ 缺失列名 → 返回 NaN
- ✅ 值为 0（可能是占位符） → 清洗为 NaN（当存在非零值时）

 用户体验 : 在 `inspect=False` 模式下不打印警告，避免 Streamlit 刷屏 ✅

---

## 5. 工程化特性

### 5.1 错误处理

| 场景 | 处理策略 | 状态 |
|------|----------|------|
| FMP API 失败 | 自动回退到 Yahoo Finance | ✅ |
| Yahoo Finance 限流 | 返回空 DataFrame，不崩溃 | ✅ |
| 网络超时 | 捕获异常，返回空 DataFrame | ✅ |
| 无效 ticker | 返回 NaN，不崩溃 | ✅ |
| 列不存在 | 返回 NaN，不崩溃 | ✅ |

### 5.2 调试模式 (inspect=True)

 输出内容 :
1. 数据源信息（FMP / Yahoo Finance）
2. DataFrame shape (行数 × 列数)
3. 列名列表（前 30 个）
4. 索引列表（前 60 个）
5. 中间计算值（Revenue, Gross Profit, 等）
6. 最终指标值

 用途 : 
- ✅ 验证数据覆盖
- ✅ 调试计算逻辑
- ✅ 诊断数据源问题

### 5.3 类型安全

```python
from typing import Optional, List, Dict, Any

def _latest_period_from_columns(df: pd.DataFrame) -> Optional[Any]
def stmt_value(stmt: pd.DataFrame, row_name: str, col: Any) -> float
def get_key_metrics(...) -> pd.DataFrame
```

 验证结果 : ✅ 所有类型标注正确，使用 `Any` (正确的类型) 而非 `any` (内置函数)

### 5.4 副作用控制

 当前状态 :
- ✅ 业务函数不修改业务数据结构
- ✅ 调试输出受 `inspect` 参数控制
- ⚠️ 缓存行为由第三方库（FinanceToolkit）决定，会写入 `cached/*.pickle` 文件
- ⚠️ 依赖环境变量 `FMP_API_KEY`（需在应用入口调用 `load_dotenv()`）

 工程化方向 : 缓存路径和环境变量管理可在后续统一配置。

---

## 6. 已知限制

### 6.1 数据源限制

| 限制 | 影响 | 当前缓解措施 | 长期方向 |
|------|------|-------------|----------|
| Yahoo Finance 速率限制 | 频繁请求可能被拒绝 | 自动回退机制 | 添加持久化缓存 |
| FMP 免费版参数限制 | 部分接口不可用 | 自动回退到 Yahoo | 升级套餐或自建数据源 |
| 仅年度数据 | 无季度财报 | - | 验证季度数据一致性后扩展 |
| 依赖第三方库缓存 | 缓存污染问题 | 已禁用缓存避免跨 ticker 污染 | 实现应用层缓存 |

### 6.2 功能限制

| 限制 | 说明 | 计划 |
|------|------|------|
| MVP 仅 2 个指标 | Gross Margin, Debt Ratio | Level 2 扩展更多 Derived 指标 |
| 无历史趋势分析 | 仅返回最新期间 | Level 2 添加时间序列 |
| 无行业对比 | 仅单一公司数据 | Level 3 添加 Peer 对比 |
| 百分比转换启发式 | 可能不适用所有指标 | 扩展时按指标类型分别处理 |

---

## 7. 测试覆盖

### 7.1 已测试场景

| 测试用例 | 股票代码 | 数据源 | 结果 | 备注 |
|----------|----------|--------|------|------|
| 汽车制造业 | F (Ford) | Yahoo Finance | ✅ 通过 | Gross Margin 8.38%, Debt Ratio 84.27% |
| 数据源回退 | F (Ford) | FMP → Yahoo | ✅ 通过 | FMP 失败自动回退 |
| Period 类型处理 | F (Ford) | Yahoo Finance | ✅ 通过 | 正确匹配 Period('2024', 'Y-DEC') |
| 百分比转换 | F (Ford) | Yahoo Finance | ✅ 通过 | 0.0838 → 8.38% |

### 7.2 待测试场景

- [ ] 科技行业 (MSFT, GOOGL)
- [ ] 金融行业 (JPM, BAC)
- [ ] 零售行业 (WMT, TGT)
- [ ] 小盘股
- [ ] 网络异常恢复
- [ ] 并发请求（如有必要）

---

## 8. Level 1 交付清单

### 8.1 核心功能 ✅

- [x] 双数据源策略（FMP + Yahoo Finance）
- [x] 自动回退机制
- [x] 2 个稳定 MVP 指标 (Derived from Raw fields)
- [x] Period 类型正确处理
- [x] 百分比单位自动转换
- [x] 调试模式（inspect=True）
- [x] 错误处理（不崩溃，返回 NaN）
- [x] 类型标注完整

### 8.2 工程化 ✅

- [x] 代码结构清晰（MetricSpec 定义）
- [x] 可扩展接口（mvp_only 参数）
- [x] 文档完整（docstring）
- [x] 副作用可控（inspect 参数控制输出）

### 8.3 待优化项（Level 2+）

- [ ] 添加应用层持久化缓存
- [ ] 添加单元测试
- [ ] 添加 Logging 替代 print
- [ ] 添加配置文件管理 API key
- [ ] 验证季度数据一致性

---

## 9. 下一步行动 (Level 2)

### 9.1 指标扩展

 优先级 P1  (从现有 Raw 字段计算):
```python
Current Ratio = Current Assets / Current Liabilities
Operating Margin = Operating Income / Revenue  
ROE = Net Income / Total Equity
```

### 9.2 时间序列

 功能 : 返回多期数据而非仅最新期
```python
get_key_metrics("AAPL", periods="all")
# 返回 2021-2024 所有年份的指标
```

### 9.3 数据可视化

 需求 : 支持前端图表展示
```python
# 输出格式友好化
{
  "ticker": "F",
  "metrics": {
    "Gross Margin": {
      "2021": 7.2,
      "2022": 7.8,
      "2023": 8.1,
      "2024": 8.4
    }
  }
}
```

---

## 10. 附录

### 10.1 完整测试输出 (2026-01-09 14:38)

```
[DEBUG] Attempting to use FinancialModelingPrep (API key length: 32)
[WARN] FMP returned empty data (likely free tier limitation)
[INFO] Falling back to Yahoo Finance...
[DEBUG] Using Yahoo Finance (free, but may have rate limits)

========== L1-1 INSPECT ==========
Data Source: Yahoo Finance
INCOME shape: (35, 4)
BALANCE shape: (73, 4)
INCOME COLUMNS (first 30): [Period('2021', 'Y-DEC'), Period('2022', 'Y-DEC'), 
                            Period('2023', 'Y-DEC'), Period('2024', 'Y-DEC')]
BALANCE COLUMNS (first 30): [Period('2021', 'Y-DEC'), Period('2022', 'Y-DEC'), 
                             Period('2023', 'Y-DEC'), Period('2024', 'Y-DEC')]
=================================

[DEBUG] Latest period: 2024 (type: Period)
[DEBUG] Revenue: 184992000000.0
[DEBUG] Gross Profit: 15506000000.0
[DEBUG] Gross Margin: 0.08381984085798305
[DEBUG] Total Assets: 285196000000.0
[DEBUG] Total Liabilities: 240338000000.0
[DEBUG] Debt Ratio: 0.84271167898568

         Metric             Value Period Unit                        Description
0  Gross Margin 8.381984085798305   2024    %            Gross Profit / Revenue.
1    Debt Ratio   84.271167898568   2024    %  Total Liabilities / Total Assets.
```

### 10.2 参考资料

- [FinanceToolkit Documentation](https://github.com/JerBouma/FinanceToolkit)
- [Yahoo Finance API](https://pypi.org/project/yfinance/)
- [FinancialModelingPrep API](https://financialmodelingprep.com/developer/docs/)
- [Pandas Period Objects](https://pandas.pydata.org/docs/user_guide/timeseries.html#time-span-representation)

---

 文档维护者: Project Team  
 最后更新 : 2026-01-09  
 版本 : 1.0 (Level 1 MVP)  
 可复现性 : 本文档所有数据均可通过 `get_key_metrics('F', inspect=True)` 在相同环境下复现