# PFA 持仓明细逻辑与行编辑规范

本文档定义持仓表格的**货币展示逻辑**与**行级编辑**功能，确保「现价看原始，市值看统一」。

## 1. 货币展示逻辑 (Table Data Logic)

### 现价列 (Current Price)

- **规则**：必须保持标的**原始币种**的价格，禁止任何汇率折算。
- **格式**：数字前强制带上币种符号。例如：长江电力 `¥26.57`，蔚来 `$4.87`，T14 `HK$3.55`。

### 市值列 (Market Value)

- **规则**：此列为**统一折算列**，根据右上角 Toggle 的选择进行实时汇率换算。
- **对齐**：若用户选「统一折算(CNY)」，则该列所有数值均显示为人民币金额，并带上 `¥` 符号。
- **精度**：汇率计算保留 4 位小数，最终显示市值保留 2 位小数，使用千分位分隔符（如 `¥14,002.12`）。

### 币种一致性

- 同一账户下的资产应继承账户的 `base_currency` 逻辑。
- 新建持仓时，默认币种强制继承自 `InvestmentAccount.defaultCurrency`。
- 支持在行编辑中手动修正标的的 `currency` 与 `exchange`（如 T14 多地上市时的纠偏）。

### 空状态处理

- 若标的因币种配置错误导致无法获取汇率，市值列显示 `--`，变红提示，并引导用户点击右侧「编辑」进行修正。

## 2. 行级编辑功能 (Row-Level Actions)

### 交互

- 每行最右侧增加「编辑」图标。
- 点击后弹出编辑弹窗。

### 编辑弹窗字段

- 标的代码、标的名称
- 持仓数量、买入成本
- **原始币种** (Currency Dropdown)：CNY / USD / HKD，允许用户手动修正（如 T14 从 HKD 改为 USD）。
- **交易所** (Exchange)：NYSE、HKEX、SGX、SSE、SZSE 等，用于 T14 等多地上市标的的区分。

### 数据生效

- 修改后立即触发重新计算，更新该行市值与顶部总资产看板。

## 3. 数据契约 (Data Contract)

见 `frontend/src/types/portfolio.ts`：

- `currentPrice`：永远存储标的原始价格，禁止折算。
- `marketValue`：根据 `displayCurrencyMode` 动态计算。
- `originalCurrency`：标的原始币种，录入时确定。
- `currencyError`：币种配置错误时无法计算市值。

## 4. 相关实现

| 模块 | 说明 |
|------|------|
| `pfa/portfolio_valuation.py` | `get_holding_currency()`、FX 精度、`currency_error` |
| `backend/api/portfolio.py` | `PATCH /portfolio/holdings` 行级更新 |
| `agents/secretary_agent.py` | `update_holding()`、`update_holdings_bulk` 保留 currency/exchange |
| `frontend/src/components/EditHoldingModal.tsx` | 行编辑弹窗 |
| `frontend/src/app/page.tsx` | 表头、现价/市值渲染、编辑按钮 |
