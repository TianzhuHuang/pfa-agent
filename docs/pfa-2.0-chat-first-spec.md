# PFA 2.0 Chat-First 需求规格书

## 1. 核心定位

**愿景**：PFA 不再是展示「我有多少钱」的账本，而是分析「这件事与我何干」的智库。

**核心逻辑**：将用户的持仓数据转化为 AI 的 RAG（检索增强生成）背景。用户粘贴新闻、链接或截图后，AI 基于持仓分析相关性并给出影响评估。

**一句话**：PFA = 基于你持仓的「新闻相关性智库」，回答「这件事与我何干」。

---

## 2. 用户旅程

1. 用户看到新闻（战争、宏观、国际动荡等），不知道与持仓有何关系
2. 来到 PFA，首次录入持仓（截图 OCR / 手动 / 文件）
3. 主界面为 AI 对话（三栏决策室布局），右侧为持仓知识库
4. 用户粘贴新闻、链接或截图
5. AI 返回结构化「影响评估卡片」，指出哪些持仓受影响、程度如何、逻辑拆解；可进入「深度分析」页查看推演链

---

## 3. UI 视觉规范（静奢风 Quiet Luxury）

### 配色方案

| 用途 | 色值 | 说明 |
|------|------|------|
| 背景 | `#0A0F1E` | 深海蓝黑 |
| 磨砂背景 | `#0A0F1E` + 透明度 + backdrop-blur | 顶部状态条、侧栏、输入坞 |
| 主色/点缀 | `#D4AF37` | 香槟金，关键线条、CTA |
| 主文字 | `#E8EAED` | 高对比白 |
| 辅助文字 | `#9AA0A6` | 钛金灰 |
| 正面情绪 | `#748E63` | Sage Green，利好、受益 |
| 负面情绪 | `#C58B8B` | Dusty Rose，利空、警示 |
| 中性 | `#D4AF37` | 香槟金，中度关联 |

### 排版

- 大留白，增加呼吸感
- 消除金融 App 常见的焦虑感
- 字体：Inter / 系统无衬线

---

## 4. 布局：三栏决策室（Chat 2.0）

### 4.1 整体结构

| 区域 | 宽度 | 内容 |
|------|------|------|
| **顶部** | 全宽 | 极窄状态条（约 32px）：连接状态、最后更新时间 |
| **左侧** | 240px | 对话历史侧边栏，每项带「情绪标签」 |
| **中间** | flex-1 | 极简对话流 + 底部输入坞（含智能示例问题） |
| **右侧** | 300px | 持仓知识库面板，Top 5 极简卡片，支持高亮联动 |

### 4.2 顶部状态条（StatusBar）

- 替代原顶部持仓标签栏
- 内容：系统连接状态、最后更新时间

### 4.3 左侧：对话历史（ChatHistorySidebar）

- 每项为「情报记录」：情绪标签（如「关于美联储降息的负面分析」）+ 首条问题截断 + 更新时间
- 点击切换当前会话

### 4.4 右侧：持仓知识库（HoldingsContextPanel）

- 默认展示 Top 5 持仓极简卡片（名称、行业，无价格）
- 联动：当对话中 ImpactCard 提及某标的时，对应 HoldingCard 高亮（香槟金边框）
- 行业热力（可选）：当话题涉及某行业时，该行业卡片可加金色流光

### 4.5 中部：对话流 + 输入坞

- 空状态时输入框上方显示 3 条智能示例问题
- 输入坞：药丸型、glassmorphism、香槟金阴影、[+] 上传图片/链接

### 4.6 深度分析页（Deep Dive）

- 从 ImpactCard 底部「深度分析」进入
- 全屏沉浸式展示逻辑推演链：新闻 → 宏观因子 → 行业影响 → 具体标的预期

---

## 5. 情绪色彩与 ImpactCard

- **ImpactItem** 支持 `sentiment?: "positive" | "negative" | "neutral"`
- 正面：Sage Green `#748E63`
- 负面：Dusty Rose `#C58B8B`
- 中性/高关联无方向：香槟金 `#D4AF37`

---

## 6. 响应式

| 断点 | 布局 |
|------|------|
| ≥1024px (lg) | 三栏完整展示 |
| <1024px | 左侧/右侧折叠为抽屉，通过顶部按钮打开；中央为对话主区 |

---

## 7. 分阶段目标

| 阶段 | 目标 |
|------|------|
| **Phase 1** | 新闻与持仓相关性分析。Chat-First 三栏决策室，用户主动粘贴新闻/链接/截图，AI 返回影响评估卡片。 |
| **Phase 2** | 数据源主动推送。接入 Bloomberg、华尔街见闻、博主等，主动提示用户与持仓相关的内容。 |

---

## 8. 实现索引

| 组件/页面 | 路径 |
|-----------|------|
| StatusBar | `frontend/src/components/chat-preview/StatusBar.tsx` |
| ChatHistorySidebar | `frontend/src/components/chat-preview/ChatHistorySidebar.tsx` |
| HoldingsContextPanel | `frontend/src/components/chat-preview/HoldingsContextPanel.tsx` |
| HoldingCard | `frontend/src/components/chat-preview/HoldingCard.tsx` |
| Impact Card | `frontend/src/components/chat-preview/ImpactCard.tsx` |
| Chat Input Dock | `frontend/src/components/chat-preview/ChatInputDock.tsx` |
| 静态预览页 | `frontend/src/app/chat-preview/page.tsx` |
| 深度分析页 | `frontend/src/app/chat-preview/deep-dive/page.tsx` |

访问 `/chat-preview` 可查看静态原型（Mock 数据）。后端调研见 `docs/pfa-2.0-backend-research.md`。
