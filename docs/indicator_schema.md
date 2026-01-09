# L1-2｜指标规范化说明书（Indicator Schema）

 版本 ：v1.0  
 所属阶段 ：Level 1（数据与指标层）  
 适用项目 ：FinanceToolkit 财务分析与可视化 Demo  

---

## 一、文档目的（Purpose）

本文件用于对项目中使用的 财务指标进行统一、规范、可追溯的定义 ，以解决以下问题：

1. 避免指标含义、单位、口径分散在代码中  
2. 确保不同指标在计算、展示与解释上的一致性  
3. 为后续绘图自动化（L1-3）和分析扩展（L2+）提供元信息支持  
4. 支持“先完成、后扩展”的工程与研究路径  

---

## 二、设计原则（Design Principles）

1.  可追溯性（Traceability）   
   - 每个指标必须明确其来源字段（Raw fields）与计算公式  
   - 派生指标（Derived）不得作为黑盒存在  

2.  可解释性（Interpretability）   
   - 指标的经济含义应清晰，避免在同一图中混合不同分析层级的指标  

3.  可扩展性（Extensibility）   
   - 新增指标时，不应修改绘图或前端逻辑  
   - 仅需在本 schema 中补充定义  

4.  稳健性（Robustness）   
   - 数据缺失或除零情况统一返回 NaN  
   - 系统不得因个别指标失败而中断运行  

---

## 三、Schema 字段定义（Field Definition）

| 字段名 | 含义说明 |
|---|---|
| `indicator_key` | 指标唯一标识（snake_case，用于代码） |
| `indicator_name` | 指标名称（英文，用于展示） |
| `category` | 指标类别（盈利 / 偿债 / 流动性 等） |
| `unit` | 指标单位（`%` / `ratio` / `currency`） |
| `primary_chart` | 默认图表类型（当前统一为 `line`） |
| `plot_mode` | 绘图模式（是否允许多指标同图） |
| `group_key` | 指标分组，用于多指标叠加绘图 |
| `data_freq` | 数据频率（annual / quarterly / ttm） |
| `source_fields` | 依赖的原始字段（来自财务三表） |
| `formula` | 指标计算公式（文本描述） |
| `notes` | 口径说明或使用限制 |

---

## 四、绘图模式说明（Plot Mode Definition）

### 4.1 `line_single`
- 单指标趋势图  
- 一个指标一张图  
- 适用于不同经济层级或语义差异较大的指标  

### 4.2 `line_multi_same_unit`
- 同一张图叠加多个指标  
-  硬性约束：unit 必须一致   
- 适用于同一经济含义层级的指标（如多种利润率）

> 注：  
> - 当前版本（V1） 不支持双轴图   
> - 不同单位或不同经济层级的指标不得强行混图  

---

## 五、指标分组与经济含义说明

### 设计说明（重要）

在本项目的 V1 阶段，指标分组遵循 经济含义优先于数据形式 的原则：

- 即使单位相同（如 `%`），  
   若指标反映的经济层级不同，也不应放在同一张图中   
- 例如：  
  - 利润率（经营效率）  
  - ROE（股东回报，受杠杆影响）  

二者不在 V1 中混合绘制，以避免解释歧义。

---

## 六、指标清单（Indicators）

### 6.1 经营效率 / 利润率（Profitability Margins）

> 反映公司在经营层面每单位收入所能产生的利润能力  
> 属于同一经济分析层级，允许同图展示

| indicator_key | indicator_name | category | unit | primary_chart | plot_mode | group_key | data_freq | source_fields | formula | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| gross_margin | Gross Margin | profitability | % | line | line_multi_same_unit | profitability_margins | annual | revenue, gross_profit | gross_profit / revenue | Derived from income statement |
| operating_margin | Operating Margin | profitability | % | line | line_multi_same_unit | profitability_margins | annual | operating_income, revenue | operating_income / revenue | P1 indicator |

---

### 6.2 股东回报（Return to Equity）

> 反映股东投入资本的回报率  
> 受盈利能力、杠杆与资本结构共同影响  
> 在 V1 中不与利润率混图

| indicator_key | indicator_name | category | unit | primary_chart | plot_mode | group_key | data_freq | source_fields | formula | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| roe | Return on Equity (ROE) | profitability | % | line | line_single | profitability_returns | annual | net_income, total_equity | net_income / total_equity | Influenced by leverage (DuPont logic) |

---

### 6.3 偿债能力（Solvency）

> 反映公司整体资产负债结构与长期偿债风险

| indicator_key | indicator_name | category | unit | primary_chart | plot_mode | group_key | data_freq | source_fields | formula | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| debt_ratio | Debt Ratio | solvency | ratio | line | line_single | solvency | annual | total_liabilities, total_assets | total_liabilities / total_assets | Balance sheet based |

---

### 6.4 流动性（Liquidity）

> 反映公司短期偿债能力与流动资产覆盖情况

| indicator_key | indicator_name | category | unit | primary_chart | plot_mode | group_key | data_freq | source_fields | formula | notes |
|---|---|---|---|---|---|---|---|---|---|---|
| current_ratio | Current Ratio | liquidity | ratio | line | line_single | liquidity | annual | current_assets, current_liabilities | current_assets / current_liabilities | Short-term solvency |

---

## 七、单位与缺失值约定（Consistency Rules）

- `%` 类指标  
  - 内部计算使用小数形式（如 0.25）  
  - 前端展示统一格式化为百分比（25%）

- `ratio` 类指标  
  - 直接展示比值（如 1.8）

- 缺失值 / 除零  
  - 统一返回 `NaN`  
  - 前端显示为 `N/A` 或 `—`  
  - 系统不得抛异常  

---

## 八、与系统模块的关系（Module Responsibility）

-  数据获取层（FinanceToolkit / 数据源）   
  → 提供 Raw financial fields  

-  指标计算层（ft_adapter / metrics）   
  → 按本 schema 中定义的公式计算指标  

-  绘图层（L1-3）   
  → 仅读取 `plot_mode` 与 `group_key`，不关心指标经济含义  

-  展示层（Streamlit）   
  → 不直接参与指标计算  

---

## 九、完成态说明（Completion Status）

- 当前项目中所有已实现与 P1 计划指标均已在本文件中定义  
- 指标计算、分组与绘图规则具有一致性  
- 新增指标无需修改绘图逻辑，仅需补充本 schema  

### ✅ L1-2 状态： 已完成（Complete） 

---

