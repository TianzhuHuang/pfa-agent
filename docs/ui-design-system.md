# PFA UI 设计系统 (Design System)

## 0. 调研与统一规范（Bloomberg / Sharesight / 雪盈）

### 参考产品结论

| 产品 | 字体/字号 | 布局与层级 | 可借鉴点 |
|------|-----------|------------|----------|
| **Bloomberg Terminal** | 可配置 9×19（默认）、信息密度高 | 紧凑网格、表头/表体层级清晰、数字右对齐 | 表头 12px 大写、表体 14px、单一无衬线、数字 tabular-nums |
| **Sharesight** | Financier 字体、加大字号与间距 | 清爽、表格与图表为主、响应式 | 标签/说明 12px、正文 14px、区域标题 16px、大数字 24–32px |
| **雪盈证券** | 字号与控件尺寸反复打磨 | 信息层级 ≤3 级、日夜模式统一规范 | 统一字号阶梯、减少视觉噪音、强调优先级 |

### 统一字号阶梯（全产品强制）

- **Caption / Label**：`12px`，字重 500，用于表头、卡片标签、辅助说明、占位符。
- **Body**：`14px`，字重 400，用于正文、表格单元格、导航、表单。
- **Title**：`16px`，字重 600，用于区域标题（如「持仓明细」「今日必读」）。
- **Page title**：`20px`，字重 600，用于页面主标题（如「投研晨报」）。
- **Display**：`24px`，字重 700，用于核心指标大数（如总资产）；次要指标可用 20px。

禁止使用 11px、13px、15px、17px、18px、22px、26px、28px 等非阶梯字号，避免视觉杂乱。

### 统一布局与间距

- **4px 网格**：所有间距为 4 的倍数（4、8、12、16、20、24、32）。
- **区块间距**：区块之间统一 `16px` 或 `24px`，卡片内边距统一 `16px`。
- **导航栏**：高度 `48px`，Logo 与导航项统一 `14px`，选中态 2px 底边。
- **表格**：表头 12px、padding 8px 12px；表体 14px、padding 10px 12px；行高一致。

---

## 1. 设计理念

**参考产品**: Sharesight (克制专业) + Bloomberg (数据密度) + 雪盈 (层级清晰) + [TradingView](https://cn.tradingview.com/) (图表与信息结构)

**核心原则**:
- **数据优先**: 数字和图表是主角，UI 是配角
- **色彩克制**: 只在涨跌和关键操作上用颜色，其余黑白灰
- **信息密度**: 专业用户需要在一屏内看到尽可能多的有效信息
- **安静界面**: 没有渐变、阴影极淡、无不必要动画

---

## 2. 品牌与主色

### Logo

- **图形**：简洁上升趋势线 + 终点圆点，象征投研与增长；主色绘制。
- **文件**：`app/static/logo.svg`（单图标）、`app/static/logo-with-wordmark.svg`（图标 + 字标 PFA）。
- **使用**：导航栏、登录页、关于页等；单图标建议 24–32px 高，字标版按需缩放。

### 主色调（品牌色）

| 用途 | 色值 | 说明 |
|------|------|------|
| **主色** | `#4285F4` | 品牌蓝，用于 Logo、主按钮、链接、选中态、关键图标 |
| **主色浅底** | `rgba(66,133,244,0.12)` | 徽章/标签背景、高亮区块 |

全产品统一使用上述主色作为品牌色，与语义色（涨跌红绿）区分；避免再引入其他蓝色系以免稀释品牌感。

---

## 3. 色彩系统

### 基础色板

| Token | 色值 | 用途 |
|---|---|---|
| `--bg-primary` | `#0F1116` | 页面深色背景 |
| `--bg-secondary` | `#1A1D26` | 卡片/容器背景 |
| `--bg-tertiary` | `#242832` | 表格行 hover / 次级区域 |
| `--border` | `#2D3139` | 分割线、边框 |
| `--text-primary` | `#E8EAED` | 主文字 |
| `--text-secondary` | `#9AA0A6` | 辅助说明 |
| `--text-muted` | `#5F6368` | 占位符、禁用态 |

### 语义色

| Token | 色值 | 用途 |
|---|---|---|
| `--color-up` | `#E53935` | 涨 (A股红) |
| `--color-down` | `#43A047` | 跌 (A股绿) |
| `--color-accent` | `#4285F4` | 品牌蓝 / 链接 / 选中态 |
| `--color-warning` | `#FB8C00` | 警告 |
| `--color-info` | `#29B6F6` | 提示 |

### 亮色模式（备选）

| Token | 色值 |
|---|---|
| `--bg-primary` | `#FFFFFF` |
| `--bg-secondary` | `#F8F9FA` |
| `--bg-tertiary` | `#F1F3F4` |
| `--border` | `#E0E0E0` |
| `--text-primary` | `#202124` |
| `--text-secondary` | `#5F6368` |

---

## 4. 字体与字号（统一阶梯）

```css
font-family: 'Inter', -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif;
```

| 层级 | 大小 | 字重 | 行高 | 用途 |
|------|------|------|------|------|
| Display | 24px | 700 | 1.2 | 总资产等核心大数 |
| Page title (H1) | 20px | 600 | 1.3 | 页面主标题 |
| Section (H2) | 16px | 600 | 1.4 | 区域标题 |
| Subsection (H3) | 14px | 600 | 1.4 | 小节标题（可 uppercase） |
| Body | 14px | 400 | 1.5 | 正文、表格、导航 |
| Caption | 12px | 500 | 1.4 | 表头、标签、辅助说明 |

**数字排版规则**:
- 所有价格和金额使用 `font-variant-numeric: tabular-nums` 保证对齐
- 金额带千分位逗号: `¥1,234,567`
- 涨跌百分比带符号: `+1.23%` / `-0.45%`

---

## 5. 间距系统

基于 4px 网格:

| Token | 值 | 用途 |
|---|---|---|
| `xs` | 4px | 内联元素间距 |
| `sm` | 8px | 紧凑间距 |
| `md` | 16px | 标准间距 |
| `lg` | 24px | 区域间距 |
| `xl` | 32px | 大区域间距 |
| `2xl` | 48px | 页面级间距 |

---

## 6. 组件规范

### 指标卡片 (Metric Card)

```
┌─────────────────────┐
│ TOTAL PORTFOLIO      │  ← caption, 12px, 500, text-muted, uppercase
│ ¥1,234,567          │  ← display, 24px, 700, text-primary, tabular-nums
│ +¥12,345 (+1.23%)   │  ← body, 14px, color-up
└─────────────────────┘
背景: bg-secondary
边框: 1px solid border
圆角: 8px
内边距: 16px
```

### 持仓表格

```
Symbol    Name      Price     Cost      Qty    Value       Return
─────────────────────────────────────────────────────────────────
600519    贵州茅台   1,466.21  1,457.91  400    ¥586,484   +¥3,320  +0.6%

表头: 12px, 600, text-muted, uppercase, letter-spacing: 0.5px, padding: 8px 12px
行: 14px, 400, text-primary, padding: 10px 12px
分割线: 1px solid border (仅水平线)
hover: bg-tertiary
代码列: color-accent, 可点击
盈亏列: color-up / color-down
```

### TradingView 借鉴（信息结构）

- **标的徽章**：代码列使用 `.ticker-badge`，蓝底圆角，一目了然区分标的。
- **方向标签**：`.direction-pill` 做多(红)/做空(绿)/中性(灰)，与 TradingView 观点卡片一致。
- **观点卡片**：`.tv-view-card` 结构为：标的 + 方向 + 标题 + 摘要 + 元信息（时间/来源/链接）。
- **图表面板**：`.chart-panel` + `.chart-panel-title` 作为图表区块标题栏，与正文分隔清晰。
- **今日异动**：`.market-movers` 内 `.mover-badge` 展示涨跌 ≥3% 的标的，紧凑横向排列。

### 导航栏

```
┌──────────────────────────────────────────────────────────────┐
│  PFA    Portfolio  Briefing  Analysis  Settings    user@x.com│
└──────────────────────────────────────────────────────────────┘
背景: bg-secondary
底边线: 1px solid border
高度: 48px
Logo: 16px, 600, text-primary
链接: 14px, 500, text-secondary
选中态: color-accent + 底部 2px accent 线
```

### AI 对话框

```
右侧固定宽度 360px
背景: bg-secondary
消息气泡:
  - User: bg-accent (淡蓝), text-primary, 右对齐
  - AI: bg-tertiary, text-primary, 左对齐
  - 圆角: 12px
输入框: 底部固定, border, 圆角 8px
```

### 登录页

```
居中卡片, max-width: 420px
背景: bg-secondary
Logo: 居中, 24px, 700
副标题: 居中, 14px, text-muted
表单: 标准间距
按钮: accent 色, 圆角 6px, 全宽
```

### 控制台/表单面板（分析控制台、设置区等）

```
┌─────────────────────────────────────────────────────────────┐
│ 分析控制台                                    ← 标题 16px 600 │
├─────────────────────────────────────────────────────────────┤
│ 时间窗口    [72 小时 ▼]    启用 Auditor ☑    标的 [贵州茅台▼]  │  ← 标签 12px Caption
│ [Scout: 抓取该标的]              [运行完整流水线]              │  ← 主操作 Primary，次操作 Secondary
└─────────────────────────────────────────────────────────────┘
```

- **容器**：`.pfa-control-panel`，背景 bg-secondary，边框 1px solid border，圆角 8px，内边距 0（标题与内容分区）。
- **标题栏**：`.pfa-control-panel-title`，16px 600，padding 12px 16px，底部分割线 1px solid border。
- **内容区**：`.pfa-control-panel-body`，padding 16px，表单项间距 12px 或 16px。
- **标签**：表单项标签 12px、500、text-muted（与 Caption 一致）。
- **下拉/输入**：14px、背景 bg-tertiary、边框 border、圆角 6px。
- **按钮**：主操作 Primary（accent 填充），次操作 Secondary（描边），14px 500，统一圆角 6px。

### 设置页（数据源配置等）

- **摘要条**：顶部 `.settings-summary-strip` 展示各类型数量（RSS / API / 社交 / 监控），12px Caption。
- **Tab 分组**：「订阅与 API」「社交与监控」分 Tab，减少长列表滚动。
- **卡片分区**：每类一块 `.settings-card`（标题 + body），列表行 `.settings-row-cell`（名称/URL/分类 + 测试·删除）。
- **行内操作**：每行右侧测试/删除并排，删除可用 danger 样式（红描边）区分。

---

## 7. 交互规范

- **加载态**: 数字区域显示 `--` 占位，不用 spinner
- **空状态**: 居中图标 + 标题 + 说明 + CTA 按钮
- **涨跌色**: A 股标准 (红涨绿跌)，数字前带 +/- 符号
- **链接**: 蓝色 (#4285F4)，hover 下划线
- **按钮**: Primary (accent填充), Secondary (border), Danger (红色border)
- **表格排序**: 点击表头排序，箭头指示方向

---

## 8. 个股概览 / 个股分析（参考 NBot 截图）

### 7.1 圆点规范（Round Dots）

- **尺寸**：统一 `6px` 直径实心圆，与一行小写字母等高，作为列表项或状态指示。
- **颜色语义**：
  - **绿色** `#43A047`：看多/积极/活跃 Tab/「Bullish sentiment」。
  - **红色** `#E53935`：看空/消极/风险。
  - **橙色** `#FB8C00`：中性/分歧/预警（如 Twitter divergence）。
  - **黄/橙** `#E6A23C` 或 `#F5A623`：Feed 列表项前的装饰圆点（非涨跌语义）。

### 7.2 个股页头部（Ticker Header）

- **面包屑**：`Portfolio / {标的代码}`，12px，`text-secondary`。
- **标的**：代码 20px bold 主色，名称 14px 副色。
- **当日涨跌**：徽章形式，如 `+2.4% today`，绿底白字（涨）或红底白字（跌），圆角 6px。
- **情绪行**：`• Bullish sentiment · 47 articles today`，前为绿色圆点，12px 副色。
- **更新时间**：`Updated 15 min ago`，12px muted。

### 7.3 子 Tab（概览 / 情绪 / 财报 / 逆向）

- **未选中**：14px 副色，无背景。
- **选中**：亮绿底 `#43A047` + 白字 + 可选前导绿点，圆角 6px。

### 7.4 Feed 列表（个股概览）

- **区块标题**：「Feed」+ 右侧「Filter」按钮。
- **每条**：左侧黄/橙圆点 → 标题（14px 主色）→ 来源 + 时间（12px muted）→ 摘要（14px 副色）→ 操作：Dig deeper（蓝）、Save、Not relevant。

### 7.5 情绪 Tab 卡片（个股分析）

- **Overall Sentiment**：大数字分数（如 72）+ 标签 BULLISH（绿色）+ 横向分布条（Bullish 绿 / Neutral 灰 / Bearish 红），圆角条。
- **7-Day Trend**：折线图 + 「↑ +14 pts over 7 days」绿色文案。
- **Sentiment by Source**：News/Twitter/Reddit/YouTube 各一行，品牌色横条 + 分数 + 条数。
- **Sentiment Alerts**：每条前圆点（绿/橙/红）+ 描述。
- **Sentiment Drivers**：标题 + 每条「↑ 事件描述」+ 小字「+12 pts 来源 2h ago」。

### 7.6 数据结构扩展（可选）

- **FeedItem**：可增加 `sentiment?: "positive"|"negative"|"neutral"`、`impact_pts?: number`。
- **个股情绪**：可增加 `overall_sentiment_score`、`sentiment_distribution`、`sentiment_by_source`、`sentiment_alerts`、`sentiment_drivers` 等结构，见产品需求再落库。

---

## 9. 响应式

| 断点 | 布局 |
|---|---|
| ≥1200px | 三栏 (holdings + chat) |
| 800-1199px | 两栏 (holdings 上, chat 下) |
| <800px | 单栏堆叠, chat 折叠为底部按钮 |
