# PFA 2.0 Chat-Preview 产品审计与重构方案

> 角色：PFA 首席产品经理（静奢风 Quiet Luxury · 高净值数字化产品）  
> 范围：`/chat-preview` 页面及关联组件（React/Next.js，无 Streamlit）  
> 参考：`docs/pfa-2.0-chat-first-spec.md`、`docs/pfa-2.0-backend-research.md`

---

## 一、当前 UI 深度审计

### 1.1 现状结构

| 区域 | 实现 | 问题摘要 |
|------|------|----------|
| 顶部 | `StatusBar`（32px） | 与下方三栏视觉割裂；无「持仓语境」入口 |
| 左侧 | `ChatHistorySidebar`（240px） | 仅 Mock；与中间对话无「情绪标签 → 高亮右侧资产」联动 |
| 中间 | 对话流 + `ChatInputDock` | 对话与 ImpactCard 层级清晰，但空状态与有内容状态过渡生硬 |
| 右侧 | `HoldingsContextPanel`（300px） | 仅「高亮 symbol」联动，未区分「未激活 / 激活」两种展示逻辑 |

**核心矛盾**：顶部标签栏已在 spec 中由 Context Bar 替代为「持仓标签」，但当前页面**未使用 ContextBar**，仅保留 StatusBar；若将来在顶部再加一层，会与三栏产生重叠与层级混乱。

### 1.2 最高优先级优化点（3–5 项）

| 优先级 | 问题 | 影响 | 建议方向 |
|--------|------|------|----------|
| **P0** | 顶部与三栏层级不清晰 | 用户不知「状态条」与「对话 / 资产」从属关系 | 明确三段式：顶条 = 全局状态；左中右 = 决策室，顶条不承载持仓标签 |
| **P0** | 右侧资产面板「未激活 / 激活」无差异 | 对话未提及资产时，右侧与对话中提及时视觉一致，缺少「知识库待命」与「本话关联」的区分 | 定义两种状态：默认「知识库摘要」、激活时「本话关联资产」突出 + 可折叠摘要 |
| **P1** | 情绪色彩仅 ImpactCard 使用，未体系统一 | 静奢红绿（鼠尾草绿 / 深珊瑚红）未下沉到 HoldingCard、StatusBar、历史项 | 建立全局情绪 token，ImpactCard / 右侧卡片 / 历史情绪标签一致使用 |
| **P1** | 输入源管道未落地 | 截图 OCR、链接清洗无 API，前端只能占位 | 后端提供 OCR（Gemini Vision / Qwen-VL）与 Link Preview（Firecrawl/Jina）接口规格 |
| **P2** | 首进无「资产扫描与收纳」引导 | 冷启动无仪式感，用户无法感知「持仓已纳入知识库」 | 首进播放轻量「资产扫描 → 收纳完成」动画，再进入三栏主界面 |

---

## 二、三段式布局与层级（左 · 中 · 右）

### 2.1 目标结构

```
┌─────────────────────────────────────────────────────────────────────────┐
│ StatusBar（仅：连接状态、最后更新）  高度 32px，不展示持仓标签            │
├──────────────┬─────────────────────────────────────┬───────────────────┤
│ 左 240px     │ 中 flex-1                            │ 右 300px          │
│ 对话历史     │ 沉浸式对话流                          │ 资产 Summary      │
│              │ · 空状态：欢迎 + 示例问题              │ · 未激活：Top 5   │
│ 情绪标签     │ · 有内容：消息 + ImpactCard           │ · 激活：关联资产  │
│ 首问截断     │ · 输入坞 sticky bottom                │   高亮 + 摘要     │
└──────────────┴─────────────────────────────────────┴───────────────────┘
```

- **顶部**：仅保留 `StatusBar`，不再增加 Context Bar；持仓语境完全由**右侧面板**承担，避免顶部与对话流重叠。
- **左侧**：对话历史为「情报记录」列表，点击切换会话并驱动中间 + 右侧内容。
- **中间**：唯一主操作区，滚动仅发生在该区，输入坞始终贴底。
- **右侧**：资产 Summary 知识库，见下节「未激活 / 激活」双态。

### 2.2 实现要点（可直接执行）

- 页面根布局：`flex h-[calc(100vh-48px)] flex-col`，第一子节点 `StatusBar`，第二子节点 `flex flex-1 min-h-0` 内左/中/右。
- 中间列：`flex flex-1 flex-col min-w-0`，内部：`flex-1 overflow-y-auto`（对话流）+ `sticky bottom-0`（ChatInputDock）。
- 左/右侧栏在 `< lg` 为抽屉，逻辑保持现有 `leftOpen` / `rightOpen`，无需改动逻辑，仅确保 z-index 与遮罩顺序正确。

---

## 三、右侧资产 Summary 面板逻辑

### 3.1 双态定义

| 状态 | 触发条件 | 展示内容 | 视觉 |
|------|----------|----------|------|
| **未激活** | 当前会话无 ImpactCard，或用户未发送过与本轮相关的消息 | Top 5 持仓极简卡片（名称、行业）；可选：总仓位占比条 | 默认边框 `border-white/10`，无高亮 |
| **激活** | 当前消息流中最近一条 AI 回复带有 ImpactCard | 同 Top 5，但被 ImpactCard.impacts 提及的 symbol 高亮（香槟金边框 + 轻量光晕）；面板顶部可展示一句「本话关联：X 只」 | 高亮卡片使用现有 `highlighted` 样式；可增加「本话关联」小标题 |

### 3.2 联动规则

- **左侧历史项点击**：切换 `activeSessionId` → 中间展示该会话消息 → 若该会话最后一条 assistant 带 ImpactCard，则 `highlightedSymbols` 来自该 ImpactCard，右侧对应 HoldingCard 高亮。
- **中间 ImpactCard 内资产标签点击**：可选：滚动右侧面板并高亮该 symbol，或打开该标的的 Deep Dive（保持现有 deepDiveHref 行为）。
- **重仓展示**：右侧始终以「持仓列表」为数据源；重仓可依 `position_pct` 或市值排序取 Top 5；若后端暂无占比，保持按列表顺序前 5 即可。

### 3.3 可执行改动

- 在 `HoldingsContextPanel` 增加 prop：`activeSummary?: string`（如「本话关联：2 只」）。当 `highlightedSymbols.length > 0` 时显示在标题下方。
- 保持 `highlightedSymbols` 与 `industryGlowIndustries` 现有逻辑，确保数据来自当前会话最后一条带 ImpactCard 的 assistant。

---

## 四、金融情绪分级系统（静奢红绿）

### 4.1 配色规范

| 语义 | 色名 | 色值 | 用途 |
|------|------|------|------|
| 正面/利好 | 鼠尾草绿 Sage Green | `#748E63` | 受益、利好、正面情绪；ImpactCard 正面标签、右侧卡片正面角标 |
| 负面/利空 | 深珊瑚红 Deep Coral | `#B85450` | 利空、警示、负面情绪；ImpactCard 负面标签、警示条 |
| 中性/高关联 | 香槟金 | `#D4AF37` | 中度关联、无方向、中性；ImpactCard 中性、StatusBar 连接态、高亮边框 |

说明：与 spec 中 Dusty Rose `#C58B8B` 二选一；深珊瑚红更偏「静奢」警示感，Dusty Rose 偏柔和。本方案采用 **Deep Coral** 作为负面主色，若需更柔可切回 `#C58B8B`。

### 4.2 使用范围

- **ImpactCard**：`ImpactItem.sentiment` → positive / negative / neutral 已对应样式，确保 positive=鼠尾草绿、negative=深珊瑚红、neutral=香槟金。
- **HoldingCard**：若后端返回「该资产在本话中的情绪」，可在卡片右下角增加小圆点或角标（鼠尾草绿 / 深珊瑚红）。
- **ChatHistorySidebar**：历史项可带情绪角标（左缘竖条或小点），便于扫视「负面分析」「中性解读」等。
- **StatusBar**：连接态绿点已用 `#748E63`，保持；离线可用深珊瑚红。

### 4.3 实现建议

- 在 `frontend/src/app/globals.css` 或 chat-preview 专用 scoped 样式中定义 CSS 变量：
  - `--pfa-sentiment-positive: #748E63`
  - `--pfa-sentiment-negative: #B85450`
  - `--pfa-sentiment-neutral: #D4AF37`
- ImpactCard、HoldingCard、ChatHistorySidebar 统一引用上述变量，便于后续主题或 A/B 切换色值。

---

## 五、输入源管道设计（与后端协作）

### 5.1 截图录入（OCR）

- **前端**：ChatInputDock 的「附件」按钮支持选择图片；上传后调用 `POST /api/portfolio/ocr`（或 `/api/chat/ocr`）传入 `multipart/form-data`（file）。
- **后端**：建议复用/扩展 `pfa/screenshot_ocr.py`，输出与 `config/user-profile.schema.json` 对齐的结构化持仓 JSON；模型选型：**Gemini Vision** 或现有 **Qwen-VL**（DASHSCOPE），优先 Qwen-VL 以统一密钥与延迟。
- **接口约定**：请求：`file: image/*`；响应：`{ "holdings": [...], "raw_text?: string" }`，若为「对话上下文」用途可额外返回 `{ "summary": "用户上传了持仓截图，识别到 3 只标的" }` 供 LLM 上下文注入。

### 5.2 新闻链接粘贴（清洗）

- **前端**：用户粘贴 URL 或输入框检测到 URL 时，可先调用 `POST /api/chat/link-preview`，body `{ "url": "https://..." }`，获取标题 + 正文摘要后再填入输入或作为附件上下文。
- **后端**：正文提取可选 **Firecrawl**、**Jina Reader**（`r.jina.ai`）等；返回结构建议：`{ "title", "description", "content_plain", "source?", "fetched_at" }`，便于 LLM 做「新闻 + 持仓」相关性推理。
- **安全**：仅允许 HTTPS；域名 allowlist 或限流，防止滥用。

### 5.3 与对话流的衔接

- 用户发送「文字 + 链接」或「文字 + 截图」时，请求体结构建议：`{ "messages": [...], "attachments?: [{ type: "url" | "image", payload: string }]" }`。
- 后端先处理 attachments（OCR / link-preview），将结果注入 system 或首条 user 消息，再调用现有 `pfa/ai_chat.py` 流式接口；若需「影响评估」结构化输出，可在后端增加一步：解析 LLM 输出中的 JSON 块，映射为 ImpactCard 所需结构。

---

## 六、用户引导（Onboarding）：资产扫描与收纳

### 6.1 目标

首次进入 chat-preview（或首次从「录入持仓」完成）时，让用户感知「你的持仓已被纳入知识库」，减少冷启动焦虑。

### 6.2 动画逻辑（建议）

1. **触发条件**：`localStorage.getItem("pfa_chat_preview_onboarding_done") !== "true"` 且当前有持仓（或刚完成一笔录入）。
2. **流程**：
   - 全屏遮罩，背景 `#0A0F1E`，中央展示「正在将你的持仓纳入知识库…」+ 乌龟 Logo 轻量呼吸动画。
   - 模拟进度：3–5 个持仓标签依次从左侧飞入到「收纳盒」图标或右侧面板轮廓内（可 CSS 动画 + 简单 stagger）。
   - 约 2–3 秒后，文案变为「收纳完成」，1 秒后遮罩淡出，进入三栏主界面。
3. **完成后**：`localStorage.setItem("pfa_chat_preview_onboarding_done", "true")`，之后不再展示。

### 6.3 实现要点

- 独立组件如 `AssetScanOnboarding.tsx`，在 `chat-preview/page.tsx` 内根据条件渲染；完成动画后回调 `onComplete()` 关闭遮罩并写 localStorage。
- 动画优先 CSS（transform + opacity），避免重布局；可选 Lottie 或 SVG 序列帧，量力而行。

---

## 七、可直接执行的代码重构计划

### Phase 1：布局与层级（1–2 天）

1. **确认顶栏唯一**：保证页面顶部仅有 `StatusBar`，不渲染 ContextBar；若某处仍引用 ContextBar，移除或改为在右侧面板内表达「当前持仓」。
2. **中间列滚动**：检查 `chat-preview/page.tsx` 中间列结构，确保对话流区域 `flex-1 overflow-y-auto`，输入坞 `sticky bottom-0`，无溢出导致的层级重叠。
3. **z-index 与抽屉**：左/右抽屉 `z-40`，遮罩 `z-30`，避免与 Header（若有）重叠。

### Phase 2：右侧面板双态与联动（1 天）

4. **HoldingsContextPanel**：新增 `activeSummary?: string`；当 `highlightedSymbols.length > 0` 时在标题下展示「本话关联：N 只」。
5. **数据流**：`highlightedSymbols` 继续由当前会话最后一条带 ImpactCard 的 assistant 推导；左侧切换会话时重新计算并传入右侧。

### Phase 3：情绪系统统一（0.5 天）

6. **CSS 变量**：在 `globals.css` 或 chat-preview 布局内定义 `--pfa-sentiment-positive`、`--pfa-sentiment-negative`、`--pfa-sentiment-neutral`。
7. **ImpactCard**：将硬编码的 `#748E63` / `#C58B8B` 改为使用上述变量；负面色若产品确认改为 Deep Coral，则用 `#B85450`。
8. **HoldingCard / ChatHistorySidebar**：若有情绪角标需求，在本 Phase 或后续迭代中接入同一 token。

### Phase 4：输入管道对接（依赖后端，1–2 天）

9. **OCR**：与后端约定 `POST /api/portfolio/ocr` 或 `POST /api/chat/ocr` 的请求/响应格式；前端 ChatInputDock 选择图片后调用并展示解析结果或错误。
10. **Link Preview**：与后端约定 `POST /api/chat/link-preview`；前端在粘贴 URL 或点击「添加链接」时调用，将返回的 title/description 展示或注入输入上下文。

### Phase 5：Onboarding 动画（1 天）

11. **AssetScanOnboarding**：实现 2–3 秒「资产扫描与收纳」动画组件，条件渲染 + localStorage 控制只展示一次。
12. **接入 chat-preview 页**：在 `hasHoldings && !onboardingDone` 时先渲染 Onboarding，完成后再展示三栏。

---

## 八、总结

| 优先级 | 内容 | 产出 |
|--------|------|------|
| P0 | 三段式布局与顶栏唯一 | 无重叠、滚动仅在中列、顶栏仅 StatusBar |
| P0 | 右侧面板未激活/激活双态 | 本话关联提示 + 高亮联动 |
| P1 | 静奢情绪配色体系统一 | CSS 变量 + ImpactCard/HoldingCard/历史项一致 |
| P1 | 输入管道（OCR + Link Preview） | 后端接口规格 + 前端对接方案 |
| P2 | 首进资产扫描收纳动画 | AssetScanOnboarding 组件 + 一次展示逻辑 |

按 Phase 1 → 2 → 3 顺序执行可先解决层级与右侧面板逻辑；Phase 4 与后端并行；Phase 5 可在主流程稳定后接入。以上方案均基于 **React/Next.js** 技术栈，不涉及 Streamlit。
