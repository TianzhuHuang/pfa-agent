# PFA 项目审计与修复报告

**审计日期**：2025-02  
**审计角色**：Senior PM + Lead QA  
**视觉基准**：Stake / Gemini 风格，`docs/ui-design-system.md` 统一规范

---

## 一、[已修复] 本次直接修改项

### 1. 色彩与边框（theme_v2.py）

| 修改项 | 说明 |
|--------|------|
| `.fin-table .up` / `.down` | 修正 A 股语义：涨=红(#E53935)，跌=绿(#43A047) |
| `.fin-table td.up` / `td.down` | Pill 背景色与 A 股一致：涨=红底，跌=绿底 |
| 全站 `#2D2D2D` → `#2D3139` | 统一边框 token，符合 design system |
| `.metric-card`、`.pfa-card`、`.chart-panel`、`.fin-table` 等 | 边框统一为 `#2D3139` |

### 2. 字号阶梯（design system 12/14/16/20/24）

| 修改项 | 原值 | 新值 |
|--------|------|------|
| `.fin-table .ai-tag` | 10px | 12px |
| `.direction-pill` | 11px | 12px |
| `.settings-row-cell .cat` | 11px | 12px |
| `.timeline-tag` (pfa_dashboard) | 11px | 12px |
| 持仓管理页 metric 标签 | 11px | 使用 `.pfa-caption` (12px) |

### 3. 功能鲁棒性

| 修改项 | 说明 |
|--------|------|
| 行情加载失败 (pfa_dashboard) | `calculate_portfolio_value` / `get_realtime_prices` 异常时使用 fallback `val`，并 `st.toast` 提示 |
| DASHSCOPE_API_KEY 缺失 | 在 Portfolio 页顶部增加提示条，说明配置方式，不阻塞使用 |
| 0_新用户引导 返回链接 | 使用 `st.page_link("pfa_dashboard.py", ...)` 替代 `<a href="/">`，确保 Streamlit 路由正确 |

### 4. 其他 UI 细节

| 修改项 | 说明 |
|--------|------|
| 持仓管理页 metric 卡片 | 使用 `.pfa-caption`、`.pfa-display` 等设计 token，替代内联 11px |

---

## 二、[待批准] 需确认后再修改项

### 1. 主题与架构

| 项目 | 说明 |
|------|------|
| **theme.py 与 theme_v2 并存** | `pages/1_持仓管理.py`、`page_utils.py` 仍使用 `theme.py`（NBOT 绿 #c8ff00），与主站 theme_v2（品牌蓝 #4285F4）不一致。建议统一迁移到 theme_v2，或明确 theme.py 的保留范围。 |

### 2. FAB 与导航

| 项目 | 说明 |
|------|------|
| **FAB 仅 Portfolio 页** | Ask PFA 悬浮按钮仅在首页显示。Briefing、Analysis、Settings、Ticker 详情页无 FAB。是否需要在全站展示？ |
| **FAB URL 跨页** | `?open_pfa_chat=1` 在子页面可能无法正确回到主入口并打开对话。需确认多页场景下的行为。 |

### 3. 视觉语义

| 项目 | 说明 |
|------|------|
| **stake-equity 箭头色** | `.arrow.up` 绿、`.arrow.down` 红（欧美习惯）。是否改为 A 股（涨红跌绿）？ |
| **Emoji 在 st.success/error** | 数据源配置等页使用 ✅❌⚠️。设计系统未明确，是否保留？ |

### 4. 体验与策略

| 项目 | 说明 |
|------|------|
| **Loading UX** | 当前用 `st.spinner`。是否引入 skeleton/shimmer 以符合 Stake 级体验？ |
| **错误信息截断** | `str(e)[:80]` 可能丢失关键信息。是否放宽或改为可展开？ |

---

## 三、审计范围与结论

### 审计范围

- **UI 视觉一致性**：theme_v2、theme、各 page 的 CSS 与 Streamlit 组件
- **交互流畅度**：登录→持仓→AI 对话链路，按钮反馈、弹窗定位
- **功能鲁棒性**：数据加载失败占位、API 缺失提示

### 结论

- **已修复**：约 15 处 UI 细节（色彩、字号、边框、鲁棒性、链接）
- **待批准**：6 项需产品/UX 决策（主题统一、FAB 范围、箭头色、Loading、错误策略、Emoji）

---

## 四、参考文档

- `docs/ui-design-system.md` — 字号阶梯、色彩 token、4px 网格
- `docs/product-scope.md` — MVP 范围
- `config/user-profile.schema.json` — 用户与持仓模型
