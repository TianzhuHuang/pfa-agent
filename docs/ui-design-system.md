# PFA UI 设计系统 (Design System)

## 1. 设计理念

**参考产品**: Sharesight (克制专业) + Bloomberg (数据密度) + Robinhood (易用性)

**核心原则**:
- **数据优先**: 数字和图表是主角，UI 是配角
- **色彩克制**: 只在涨跌和关键操作上用颜色，其余黑白灰
- **信息密度**: 专业用户需要在一屏内看到尽可能多的有效信息
- **安静界面**: 没有渐变、阴影极淡、无不必要动画

---

## 2. 色彩系统

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

## 3. 字体

```css
font-family: 'Inter', -apple-system, 'SF Pro Display', 'Segoe UI', sans-serif;
```

| 层级 | 大小 | 字重 | 行高 | 用途 |
|---|---|---|---|---|
| Display | 32px | 700 | 1.2 | 总资产数字 |
| H1 | 20px | 600 | 1.3 | 页面标题 |
| H2 | 16px | 600 | 1.4 | 区域标题 |
| Body | 14px | 400 | 1.5 | 正文 |
| Caption | 12px | 400 | 1.4 | 辅助说明 |
| Mono | 14px | 500 | 1.3 | 数字/价格 (tabular-nums) |

**数字排版规则**:
- 所有价格和金额使用 `font-variant-numeric: tabular-nums` 保证对齐
- 金额带千分位逗号: `¥1,234,567`
- 涨跌百分比带符号: `+1.23%` / `-0.45%`

---

## 4. 间距系统

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

## 5. 组件规范

### 指标卡片 (Metric Card)

```
┌─────────────────────┐
│ TOTAL PORTFOLIO      │  ← caption, 12px, text-muted, uppercase
│ ¥1,234,567          │  ← display, 32px, text-primary, tabular-nums
│ +¥12,345 (+1.23%)   │  ← body, 14px, color-up
└─────────────────────┘
背景: bg-secondary
边框: 1px solid border
圆角: 8px
内边距: 20px
```

### 持仓表格

```
Symbol    Name      Price     Cost      Qty    Value       Return
─────────────────────────────────────────────────────────────────
600519    贵州茅台   1,466.21  1,457.91  400    ¥586,484   +¥3,320  +0.6%
000858    五粮液     103.88    144.41    600    ¥62,328    -24,320  -28.0%

表头: 12px, text-muted, uppercase, letter-spacing: 0.5px
行: 14px, text-primary
行高: 44px
分割线: 1px solid border (仅水平线)
hover: bg-tertiary
代码列: color-accent, 可点击
盈亏列: color-up / color-down
```

### 导航栏

```
┌──────────────────────────────────────────────────────────────┐
│  PFA    Portfolio  Briefing  Analysis  Settings    user@x.com│
└──────────────────────────────────────────────────────────────┘
背景: bg-secondary
底边线: 1px solid border
高度: 52px
Logo: 18px, 600, text-primary
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

---

## 6. 交互规范

- **加载态**: 数字区域显示 `--` 占位，不用 spinner
- **空状态**: 居中图标 + 标题 + 说明 + CTA 按钮
- **涨跌色**: A 股标准 (红涨绿跌)，数字前带 +/- 符号
- **链接**: 蓝色 (#4285F4)，hover 下划线
- **按钮**: Primary (accent填充), Secondary (border), Danger (红色border)
- **表格排序**: 点击表头排序，箭头指示方向

---

## 7. 响应式

| 断点 | 布局 |
|---|---|
| ≥1200px | 三栏 (holdings + chat) |
| 800-1199px | 两栏 (holdings 上, chat 下) |
| <800px | 单栏堆叠, chat 折叠为底部按钮 |
