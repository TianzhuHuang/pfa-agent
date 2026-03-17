# PFA 项目介绍与开发进展

> 本文档汇总 PFA 的产品定位、技术架构、当前开发状态及后续需求，便于新成员上手或对外汇报。  
> 最后更新：基于 2025 年 2–3 月代码与文档整理。

---

## 一、项目介绍

### 1.1 产品定位

**PFA（Personal Finance Agent）** 是一款面向**基金经理与有经验个人投资者**的 AI 投研助理，核心价值是「**基于持仓的信息降噪**」——用 Agent 完成信息收集与整理，让用户把时间用在决策上。

- **一句话**：PFA = 基于你持仓的「新闻相关性智库」，回答「这件事与我何干」。
- **主界面形态**：从 Dashboard 优先演进为 **Chat-First**：主界面为 AI 对话流，顶部极简状态条，左侧对话历史，中间沉浸式对话 + 底部多模态输入坞，右侧持仓知识库（三栏决策室布局）。

**分阶段目标**（见 `docs/product-scope.md`）：

| 阶段 | 目标 |
|------|------|
| **Phase 1** | 新闻与持仓相关性分析（Chat-First）。用户主动粘贴新闻、链接或截图，AI 返回结构化「影响评估」；多模态输入（截图 OCR、链接抓取）已接入。 |
| **Phase 2** | 数据源主动推送。接入 Bloomberg、华尔街见闻、博主等，主动提示与持仓相关的内容。 |

### 1.2 核心功能概览

- **持仓管理**：多方式录入——智能搜索（东方财富 API）、截图 OCR（Qwen-VL）、CSV/JSON 导入、表格编辑、多账户；数据符合 `config/user-profile.schema.json`。
- **数据源**：东方财富新闻、华尔街见闻、RSS（含 RSSHub 财联社/格隆汇/金十）、36kr、FT 中文网等；统一落库 `pfa/data/store.py`（FeedItem / AnalysisRecord）。
- **AI 对话**：全局对话 + 个股会话；流式回复（SSE）；支持自然语言解析交易意图（加/改/删持仓）并走确认流程；系统自动注入持仓与估值上下文。
- **截图与链接**：Chat-Preview 支持上传图片（OCR 持仓/新闻文字）、输入链接（后台抓取正文），识别结果作为上下文一并提交给 AI；上传与识别过程有进度条与耗时展示（含 `PFA_DEBUG_TIMING` 调试）。
- **估值与行情**：多市场实时报价（A/港/美/数字货币/SGX），多源回退（腾讯/新浪/东财/Yahoo/OKX/Binance/CoinGecko）；机房环境可配 `PFA_PROXY_BASE` 代理。
- **晨报与告警**：定时流水线（Scout → Analyst → Auditor）、Telegram 推送、价格/关键词告警与 AI 分析；Scheduler 默认 8:00 CST。

### 1.3 技术架构

- **前端**：Next.js（App Router）+ React，主入口 `frontend/`；Chat-Preview 为 `/chat-preview`，静奢风 UI（背景 `#0A0F1E`，主色 `#D4AF37`）。
- **后端**：FastAPI（`backend/main.py`），端口 8000；API 挂载在 `/api/*`，前端可通过 `NEXT_PUBLIC_API_URL` 直连后端（避免 Next 代理 30s 超时）。
- **数据层**：
  - 对话：SQLite（`data/pfa.db`）+ `backend/services/chat_store.py`、`ticker_chat_service`；可迁移至 Supabase（Phase 4）。
  - 持仓/组合：`PFA_USE_DB=1` 时走 DB（`backend/database/`），否则本地 `config/my-portfolio.json`；Supabase 多用户方案见 `docs/phase4-plan.md`。
  - 新闻/分析：`pfa/data/store.py` 统一 FeedItem、AnalysisRecord，路径 `data/store/`。
- **多 Agent**：Scout（多源抓取）→ Analyst（结构化简报）→ Auditor（跨模型事实核查）→ Secretary（编排 + 持仓 CRUD + 备忘），见 `agents/`。

### 1.4 安全与合规（强制遵循）

- **只读模式**：Agent 仅具备数据读取权限，**无下单/交易/转账**能力；涉及券商时仅实现只读（见 `docs/security-architecture.md`）。
- **敏感数据**：券商明文密码不存云端/日志；持仓与凭证脱敏（日志不输出完整持仓明细）。
- **隐私**：最小必要收集；持仓与渠道配置由用户主动操作，不擅自同步至未授权第三方。

### 1.5 关键文档索引

| 文档 | 说明 |
|------|------|
| `docs/product-scope.md` | 产品目标、MVP 范围、Phase 1/2 对应关系 |
| `docs/security-architecture.md` | 只读模式、脱敏与存储、隐私原则 |
| `docs/data-sources.md` | 数据源类型、实现方式、价格接口与代理 |
| `docs/pfa-2.0-chat-first-spec.md` | Chat-First UI 规范、三栏布局、情绪色彩 |
| `config/user-profile.schema.json` | 用户配置与持仓数据模型 |
| `AGENTS.md` | 运行方式、关键模块、环境变量、Phase 4 简述 |

---

## 二、目前开发进展

### 2.1 Phase 1（Chat-First · 新闻与持仓相关性）

- **已完成**：
  - Chat-Preview 三栏布局（左历史、中对话、右持仓），接**真实**会话与持仓 API。
  - 左侧：`GET /api/chat/all-sessions`，支持全局会话与个股会话切换；选中后加载 `GET /api/chat/history` 或 `GET /api/chat/ticker-history`。
  - 中间：流式对话，发送走 `POST /api/chat/stream`（全局）或 `POST /api/chat/stream-ticker`（个股）；保存走 `POST /api/chat/history` 或 `POST /api/chat/ticker-history`。
  - 右侧：`GET /api/portfolio` 估值数据，HoldingsContextPanel 展示持仓卡片（含 logo/交易所），与 ImpactCard 高亮联动（本话关联）。
  - 多模态输入：图片上传 → `POST /api/portfolio/ocr`（持仓/新闻截图识别）；链接抓取 → `POST /api/chat/fetch-links`（trafilatura 正文提取）；上传/识别过程有进度条，发送按钮在附件未完成时禁用；支持 OCR/链接耗时展示与 `debug_timings` 调试。
  - 交易意图解析与确认卡（加/改/删持仓），后端 `pfa/ai_chat.py` + `execute_trade_payload`；估值/解析中 None 安全已处理（如 `total_pnl_cny`、`pnl_cny`、`confidence`）。

### 2.2 Phase 2（数据源与估值）

- **已完成**：
  - 东方财富搜索、RSS 抓取、统一数据层（FeedItem/store）；多源价格（A/港/美/数字货币/SGX）与机房代理（`PFA_PROXY_BASE`）；价格接口探测脚本 `scripts/probe_price_apis.py`。
- **进行中/待深化**：
  - 数据源主动推送（Bloomberg、华尔街见闻、博主等）为 Phase 2 下一阶段目标；当前仍以用户主动输入（粘贴/截图/链接）为主。

### 2.3 Phase 3（知识库与 Skills）

- **设计**：见 `docs/phase3-design.md`。知识库基于 `pfa/data/store.py`，Skill 如持仓新闻摘要（`holding_news_digest`）逻辑已在 `scripts/fetch_holding_news.py --analyze` 中；规划将 Skill 抽成独立模块、引入向量检索。
- **实现**：部分通过现有脚本与 Analyst 流水线落地，尚未完全模块化为 `pfa/skills/` 标准接口。

### 2.4 Phase 4（Supabase 多用户）

- **设计**：见 `docs/phase4-plan.md`。目标为多用户 SaaS：Supabase Auth + PostgreSQL + RLS；表结构（holdings、analyses、user_settings）与迁移路径已文档化。
- **实现**：数据库与部分服务（如 `backend/database/supabase_store.py`）存在；未全面切换为「仅 Supabase」模式，单机 JSON/DB 仍为主路径。

### 2.5 对话体系与 Chat-Preview 融合

- **三处对话入口**（见 `docs/chat-preview-development-plan.md`）：
  - 首页 Portfolio：`/api/chat/history` + `POST /api/chat/stream`。
  - 个股详情：`/api/chat/ticker-history` + `POST /api/chat/stream-ticker`。
  - Chat-Preview：复用上述 API，左侧 all-sessions 统一入口，中/右为对话流 + 持仓面板。
- **ImpactCard / 情绪标签**：当前 stream 返回纯文本；若需结构化影响评估卡片或历史项情绪标签，需后端扩展（如 SSE type=impact 或会话元数据摘要），产品审计见 `docs/pfa-2.0-chat-preview-pm-audit.md`。

### 2.6 已知问题与待优化（摘要）

- **架构**：Next.js 代理 30s 超时已通过 `NEXT_PUBLIC_API_URL` 直连规避；多数据源（SQLite vs Supabase）与 `user_id` 传递链需在多租户前审计。
- **性能**：晨报流水线全量执行耗时长，建议分阶段缓存与增量晨报；实时行情串行请求约 1.8s；新闻抓取与情绪分析可改为先展示 Feed、情绪异步更新。
- **UI/UX**：移动端需真机验证；情绪 Tab 部分占位（7-Day Trend 等）待接数据或标注「即将推出」。
- **安全**：券商凭证存储策略、生产日志脱敏需收尾（见 `docs/pfa-待优化大项清单.md`）。

---

## 三、后续开发需求

以下按「产品规划」「性能与架构」「功能完善」「安全与合规」分类，便于排期与迭代。

### 3.1 产品与体验（来自 product-scope、chat-first-spec、PM 审计）

- **Phase 2 数据源主动推送**：接入 Bloomberg、华尔街见闻、博主等，主动提示与持仓相关的内容，而非仅被动等待用户粘贴。
- **结构化影响评估**：AI 回复中返回结构化 ImpactCard（标的、影响方向、程度、逻辑），前端解析后渲染；左侧历史项带情绪标签（来自 impact 或会话摘要）。
- **深度分析页（Deep Dive）**：从 ImpactCard 进入，全屏展示「新闻 → 宏观因子 → 行业 → 标的」推演链。
- **首进引导**：冷启动时轻量「资产扫描 → 收纳完成」动画或引导，强化「持仓已纳入知识库」的感知。
- **情绪体系统一**：静奢红绿（鼠尾草绿/深珊瑚红）与香槟金下沉到 HoldingCard、StatusBar、历史项，并统一为 CSS 变量（如 `--pfa-sentiment-positive`）。

### 3.2 性能与架构

- **晨报流水线**：分阶段缓存（Scout 落库后 Analyst 可单独重跑）；增量晨报（仅对今日有新闻的标的分析）；避免单次全量 2 分钟级阻塞。
- **行情与请求**：评估东方财富批量接口或 WebSocket，降低首屏延迟；个股页「刷新数据」后先展示 Feed，情绪分析异步更新。
- **多租户与数据层**：明确「单机模式」与「多用户模式」切换路径；持仓 CRUD 统一走 portfolio_store；API 与 RLS 全面带 `user_id` 或等效隔离。

### 3.3 功能完善

- **Phase 3 知识库与 Skills**：将 `holding_news_digest` 等抽成 `pfa/skills/` 标准模块；支持多数据源混合输入；可选向量检索按语义排序。
- **Phase 4 多用户落地**：完成 Supabase 迁移、登录/注册与 RLS 全量覆盖；Telegram 按 user_id 绑定与推送。
- **移动端**：375px/414px 下侧栏、对话、持仓表格完整走查；可选将 Ask PFA 改为底部浮层。
- **情绪 Tab**：接入历史情绪序列或明确标注「即将推出」，减少占位困惑。

### 3.4 安全与合规

- **券商凭证**：文档化「只读模式」与「需登录模式」边界；若需持久化，仅本地或 Vault，不落云端。
- **日志与脱敏**：生产环境统一异常处理，对 `portfolio`、`holdings`、用户标识做脱敏或截断。

### 3.5 需人工确认的决策

- 交易确认后 Portfolio 刷新时机：是否加轮询或乐观更新。
- 晨报「今日已生成」的时区与多时区用户策略。
- 情绪 API 的 symbol 误匹配（如 600900 与京能电力）的 prompt 或 symbol 校验。
- 未登录时默认 `user_id=admin` 与 Supabase 多用户的策略（是否强制登录后使用核心功能）。

---

## 四、本地运行与验证（速查）

```bash
# 环境
python3 scripts/init_pfa_env.py   # 依赖、data/config 等
pip install -r requirements.txt

# 后端
uvicorn backend.main:app --reload --port 8000

# 前端（直连后端避免 30s 超时）
# frontend/.env.local: NEXT_PUBLIC_API_URL=http://localhost:8000
cd frontend && npm run dev   # http://localhost:3000

# 校验持仓
python3 scripts/validate_portfolio.py config/my-portfolio.json

# 抓取与分析（可选）
python3 scripts/fetch_holding_news.py --hours 24
python3 scripts/fetch_holding_news.py --hours 72 --analyze
```

环境变量要点：`DASHSCOPE_API_KEY`（对话/OCR/Analyst）、`OPENAI_API_KEY`（Auditor 优先）、`TELEGRAM_*`（推送）、`PFA_DEBUG_TIMING=1`（OCR/链接耗时调试）、`PFA_PROXY_BASE`（机房代理）、`SUPABASE_*`（Phase 4）。

---

*文档基于现有 `docs/`、`AGENTS.md`、`.cursorrules` 及代码结构整理，后续大功能上线或 Phase 推进后建议同步更新本文档。*
