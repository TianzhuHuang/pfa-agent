# Chat-Preview 与现有对话融合 · 开发计划

本文档说明如何将 **chat-preview** 页面与现有 **Portfolio 首页对话**、**个股详情 Ask PFA Live** 融合，并给出可执行的开发步骤、依赖与可复用资源。供开发 Agent 按步骤执行。

---

## 一、现有对话体系梳理

### 1.1 三处对话入口

| 入口 | 前端页面 | 历史/会话 | 流式接口 | 存储 |
|------|----------|-----------|----------|------|
| **首页 Portfolio** | `frontend/src/app/page.tsx` | `GET /api/chat/history` | `POST /api/chat/stream` | chat_store（DB/JSON），symbol=null |
| **个股详情** | `frontend/src/app/portfolio/[symbol]/page.tsx` | `GET /api/chat/ticker-history?symbol=xxx` | `POST /api/chat/stream-ticker` | ticker_chat_service（按 symbol+session_id） |
| **统一历史列表** | 首页左侧/抽屉 | `GET /api/chat/all-sessions` | — | 合并 global + 所有 ticker 会话 |

### 1.2 关键 API 与数据流

```
GET  /api/chat/all-sessions     → { sessions: [{ type: "global"|"ticker", session_id, symbol?, first_question, updated_at }] }
GET  /api/chat/history          → { messages: [{ role, content }] }   // 首页全局
POST /api/chat/history          → 保存首页全局消息
GET  /api/chat/ticker-sessions?symbol=xxx  → { sessions: [{ session_id, first_question, updated_at }] }
GET  /api/chat/ticker-history?symbol=xxx&session_id=xxx  → { messages, session_id }
POST /api/chat/ticker-history   → 保存个股会话
POST /api/chat/stream           → SSE，body: { messages }
POST /api/chat/stream-ticker    → SSE，body: { symbol, messages, session_id? }
```

- **stream**：system 由后端用 `build_system_prompt(holdings, val)` 注入持仓；支持 parse_trade_command / confirm 流程。
- **stream-ticker**：针对单标的，会注入该标的的 feed 摘要作为背景。

### 1.3 Chat-preview 当前状态

- **页面**：`frontend/src/app/chat-preview/page.tsx`，三栏布局（左历史、中对话、右持仓）。
- **数据**：全部 Mock（MOCK_HOLDINGS、MOCK_MESSAGES、MOCK_SESSIONS、MOCK_IMPACT_CARD_*）。
- **组件**：StatusBar、ChatHistorySidebar、HoldingsContextPanel、ImpactCard、ChatInputDock、ChatMessage；右侧已做 TradingView 风格自选表 + 选中详情。

---

## 二、融合方案：Chat-Preview 接真实对话

### 2.1 会话模型统一

- **左侧「对话历史」**：直接使用 `GET /api/chat/all-sessions`。  
  - 每条 session 含 `type`（global / ticker）、`session_id`、`symbol`（ticker 时有）、`first_question`、`updated_at`。  
  - Chat-preview 的 ChatHistorySidebar 已支持 `ChatSessionItem`（id, firstQuestion, emotionTag, updatedAt）；**映射**：`id` = type===global ? "global" : `${symbol}/${session_id}`，`firstQuestion` = first_question，`emotionTag` 暂无（见 2.4），`updatedAt` 用 formatTimeAgo(updated_at)。

- **选中会话后加载消息**：  
  - 若 `type === "global"`：`GET /api/chat/history` → 填入中间对话区。  
  - 若 `type === "ticker"`：`GET /api/chat/ticker-history?symbol=xxx&session_id=xxx` → 填入中间对话区。

- **发送新消息**：  
  - 当前选中的是 global → `POST /api/chat/stream`，body `{ messages }`。  
  - 当前选中的是 ticker → `POST /api/chat/stream-ticker`，body `{ symbol, session_id, messages }`。  
  - 流式结束后的保存：global 用 `POST /api/chat/history`，ticker 用 `POST /api/chat/ticker-history`（与首页/个股页逻辑一致）。

### 2.2 右侧持仓数据

- **列表与详情**：使用 `GET /api/portfolio?display_currency=xxx`（与首页一致）。  
- 返回结构含 `by_account`、持仓项含 `symbol`、`name`、`current_price`、`today_pct`、`position_pct` 等；若后端暂无 `position_pct`，前端可依市值占比自算或隐藏占比条。  
- **行业**：若 API 无 `industry`，可前端用 symbol 前缀或配置表 mock（如 600→白酒、00700→社交），或后续由后端扩展。

### 2.3 高亮「本话关联」与 ImpactCard

- **现有 stream/stream-ticker** 仅返回纯文本（SSE type=chunk/done），无结构化 ImpactCard。  
- **短期**：前端不解析 ImpactCard，只展示纯文本回复；本话关联高亮可先不做，或沿用「最后一条 assistant 的 content 里 @symbol」简单匹配（若产品接受）。  
- **中期**：后端在 LLM 回复中约定「影响评估」JSON 块（或单独 SSE type=impact），前端解析后渲染 ImpactCard；需在 `pfa/ai_chat.py` 或 stream 封装里增加结构化输出与解析（见第五节）。

### 2.4 情绪标签（emotionTag）

- **现状**：all-sessions 与 DB 均无 emotion_tag 字段。  
- **可选方案**：  
  - A) 前端用 first_question 前 15 字作为 emotionTag 占位。  
  - B) 后端在保存会话时或异步任务中，对最后一条 assistant 做摘要（如用 Qwen 一句话），写入 session 元数据；需扩展 DB 或 JSON 的 session 元信息。  
  - C) 若 LLM 未来返回结构化 impact，可从 impact 的 title/sentiment 推导 emotionTag。  
- **建议**：Phase 1 用方案 A，Phase 2 再考虑 B/C。

---

## 三、依赖与运行环境

### 3.1 现有依赖（无需新增即可接真实 API）

| 层级 | 依赖 | 用途 |
|------|------|------|
| 前端 | Next.js 16, React 19 | 路由、SSR/CSR |
| 前端 | Recharts | 右侧行业占比图（已用） |
| 后端 | FastAPI | API、SSE |
| 后端 | pfa/ai_chat.py, DASHSCOPE_API_KEY | 流式对话（Qwen） |
| 后端 | agents.secretary_agent, pfa.portfolio_valuation | 持仓与估值 |
| 存储 | SQLite + backend/services/chat_service.py, ticker_chat_service.py | 对话持久化 |
| 存储 | chat_store.py | 统一 load/save 入口（DB 优先、JSON 回退） |

### 3.2 后续 Phase 可能新增

| 能力 | 依赖/服务 | 说明 |
|------|-----------|------|
| 链接正文提取 | Firecrawl API / Jina Reader (r.jina.ai) / 自建 Readability | 见 docs/pfa-2.0-backend-research.md |
| 截图 OCR（对话上下文） | 已有 pfa/screenshot_ocr.py + POST /api/portfolio/ocr | 复用；若需「对话内上传截图」可再包一层 POST /api/chat/ocr 转 summary 注入 |
| 影响评估结构化 | 无新依赖；需 Prompt + 解析 LLM 输出 JSON | 见第五节 |
| 向量/RAG | Supabase pgvector / Chroma 等 | 仅当要做「新闻→持仓」检索时 |

### 3.3 环境变量

- **已有**：`DASHSCOPE_API_KEY`（必选）、`NEXT_PUBLIC_API_URL` 或 `NEXT_PUBLIC_API_URL`（前端调后端）、`PFA_USE_DB=1`（推荐）。  
- **可选**：Supabase 相关（若多租户）、Firecrawl/Jina 等（若做 link-preview）。

---

## 四、可复用开源与现有代码

### 4.1 项目内可直接复用

| 模块 | 路径 | 用途 |
|------|------|------|
| 对话存储 | backend/services/chat_store.py | load/save 首页历史 |
| 个股会话 | backend/services/ticker_chat_service.py | list/load/save ticker 会话 |
| 首页流式 | backend/api/chat.py → chat_stream | 直接复用 |
| 个股流式 | backend/api/chat.py → chat_stream_ticker | 直接复用 |
| 持仓估值 | GET /api/portfolio | 与首页一致 |
| OCR | pfa/screenshot_ocr.py + POST /api/portfolio/ocr | 截图→持仓；可再包一层供「对话内上传」 |
| AI 系统提示 | pfa/ai_chat.py build_system_prompt | 已含持仓上下文 |

### 4.2 第三方/开源（按需引入）

| 能力 | 方案 | 说明 |
|------|------|------|
| 链接正文提取 | Jina Reader | `https://r.jina.ai/<url>`，无需 key，适合快速验证 |
| 链接正文提取 | Firecrawl | API 需 key，功能更全 |
| 链接正文提取 | readability-lxml / goose3 | Python 库，自建服务 |
| 表格/正文解析 | 已有 pfa/screenshot_ocr (Qwen-VL) | 截图→JSON 已实现 |

---

## 五、分步开发计划（可交开发 Agent 执行）

### Phase 1：Chat-Preview 接真实 API（不改后端协议）

**目标**：chat-preview 页面左侧历史、中间对话、右侧持仓全部用真实接口；发送/接收与首页、个股页一致，不要求 ImpactCard 结构化。

1. **数据层**  
   - 1.1 在 chat-preview 页面增加：`loadSessions()` → `GET /api/chat/all-sessions`，映射为 ChatHistorySidebar 所需 `sessions`（id, firstQuestion, emotionTag←first_question 截断, updatedAt）。  
   - 1.2 选中会话时：若 global，`GET /api/chat/history`；若 ticker，`GET /api/chat/ticker-history?symbol=...&session_id=...`，将 `messages` 填入 state。  
   - 1.3 右侧持仓：`GET /api/portfolio?display_currency=...`，映射为 HoldingsContextPanel 所需列表（symbol, name, industry←可先 mock 或从配置来）, current_price, today_pct, position_pct, currency, sentiment 等；无则省略。

2. **发送与流式**  
   - 2.1 输入框发送：若当前为 global，请求 `POST /api/chat/stream`，body `{ messages }`；若为 ticker，请求 `POST /api/chat/stream-ticker`，body `{ symbol, session_id, messages }`。  
   - 2.2 解析 SSE（与 page.tsx 一致）：`data: { type, content }`，chunk 拼接到最后一条 assistant，done 后保存历史（global 用 POST /api/chat/history，ticker 用 POST /api/chat/ticker-history）。  
   - 2.3 新建会话：global 清空后发即新会话；ticker 侧若无 session_id 则先不传，由后端返回或前端生成 UUID 再保存。

3. **UI 与路由**  
   - 3.1 无持仓时展示「先录入持仓」并跳转或打开录入入口（与现有逻辑一致）。  
   - 3.2 左侧历史点击切换会话时，重新拉取该会话 messages 并清空「当前输入」的临时状态。  
   - 3.3 可选：从首页「Chat 2.0」入口进入 chat-preview 时，若 URL 带 `?session=global` 或 `?symbol=xxx&session_id=xxx`，自动选中对应会话并加载。

4. **验收**  
   - 在 chat-preview 能看见与首页一致的全局对话历史，能发送并收到流式回复并保存。  
   - 能看见与个股页一致的某标的会话列表，能切换并加载该标的的某次会话，能发送并收到 stream-ticker 回复并保存。  
   - 右侧持仓展示真实持仓与价格（若 API 有）。

---

### Phase 2：ImpactCard 与「本话关联」高亮（需后端扩展）

**目标**：在部分回答中返回「影响评估」结构化数据，前端渲染 ImpactCard；右侧面板根据最后一条 impact 高亮对应标的。

1. **后端**  
   - 2.1 在 `pfa/ai_chat.py` 或 stream 处理中，对「新闻/宏观对持仓影响」类问题，增加二次调用或单次 Prompt 要求输出 JSON 块，格式如：  
     `{"title":"...", "impacts":[{"symbol","name","level","levelLabel","sentiment"}], "summary":"..."}`。  
   - 2.2 在 SSE 中增加事件类型，例如 `type: "impact"`，payload 为上述 JSON；或在 `type: "done"` 时附带 `impact?: {...}`。  
   - 2.3 若采用「done 时带 impact」：前端在 done 时把 impact 挂到当前 assistant 消息上，并驱动右侧 highlightedSymbols。

2. **前端**  
   - 2.4 消息列表项：若某条 assistant 带 `impactCard`，则在其下渲染 ImpactCard 组件；并计算 `highlightedSymbols` 来自当前选中会话的最后一条带 impact 的 assistant。  
   - 2.5 右侧 HoldingsContextPanel 已支持 `highlightedSymbols` 与 `activeSummary`，无需改组件，只需从消息数据传入。

3. **存储**  
   - 2.6 若需持久化 impact：在 ChatMessage 表或 JSON 中增加可选字段 `impact_snapshot`（JSON）；或仅前端展示不落库，按需再定。

---

### Phase 3：输入源扩展（链接预览 + 截图注入对话）

**目标**：用户可粘贴链接或上传截图，后端做正文提取/OCR，并将结果作为上下文参与当轮对话。

1. **链接预览**  
   - 3.1 后端新增 `POST /api/chat/link-preview`，body `{ url }`。  
   - 3.2 实现：调用 Jina Reader（`https://r.jina.ai/<url>`）或 Firecrawl，返回 `{ title, description, content_plain, source?, fetched_at }`。  
   - 3.3 前端：输入框支持「粘贴链接」或检测 URL，先请求 link-preview，将 title+content_plain 摘要拼入当前输入或作为附件展示；发送时 body 增加 `attachments: [{ type: "url", payload: url }]` 或把摘要写入首条 user 消息。

2. **截图注入对话**  
   - 3.4 复用 `POST /api/portfolio/ocr`（或新增 `POST /api/chat/ocr`）：上传图片 → 返回 `{ holdings, raw_text?, summary? }`。  
   - 3.5 发送时 body 增加 `attachments: [{ type: "image", payload: base64_or_url }]`；后端将 OCR 的 summary 或 raw_text 注入 system/首条 user，再调 stream。

3. **后端 stream 入参**  
   - 3.6 扩展 ChatRequest：`attachments?: [{ type: "url"|"image", payload: string }]`。  
   - 3.7 若存在 attachments，先处理（link-preview / OCR），再构建 system 或首条 user 内容，然后调用现有 `call_ai_stream`。

---

### Phase 4：情绪标签与 Onboarding（可选）

- **情绪标签**：为 all-sessions 的每条会话增加 emotion_tag；可从 first_question 摘要或后续从 assistant 摘要生成（后端异步或保存时调 LLM 一句摘要）。  
- **Onboarding**：首次进入 chat-preview 且有持仓时，播放「资产扫描与收纳」动画（见 pfa-2.0-chat-preview-pm-audit.md 第六节），localStorage 控制只播一次。

---

## 六、文件与接口清单（便于 Agent 定位）

| 类型 | 路径或接口 | 说明 |
|------|------------|------|
| 页面 | frontend/src/app/chat-preview/page.tsx | 接 API、状态、发送/保存 |
| 组件 | frontend/src/components/chat-preview/* | 已存在，仅需接真实 props |
| API | GET/POST /api/chat/* | backend/api/chat.py |
| API | GET /api/portfolio | backend/api/portfolio.py |
| 存储 | backend/services/chat_store.py | 首页历史 |
| 存储 | backend/services/ticker_chat_service.py | 个股会话 |
| AI | pfa/ai_chat.py | build_system_prompt, call_ai_stream |
| OCR | pfa/screenshot_ocr.py, POST /api/portfolio/ocr | 截图→持仓 |

---

## 七、执行顺序建议

1. **Phase 1** 全部完成后再做 Phase 2，避免同时改协议与前端。  
2. Phase 2 需与后端约定好 impact 的 SSE 形状或 done 附带字段。  
3. Phase 3 的 link-preview 可先接 Jina（无需 key），OCR 已存在可先复用。  
4. Phase 4 可在 1/2 稳定后按需排期。

文档完成后，开发 Agent 可按 **Phase 1 → 2 → 3 → 4** 的顺序执行；每 Phase 验收通过再进入下一 Phase。
