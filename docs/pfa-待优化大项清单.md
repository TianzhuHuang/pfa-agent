# PFA 待优化大项清单

> 基于 2025-03 本地全量 QA 测试结果整理。包含架构瓶颈、性能问题及需人工确认的逻辑决策。

---

## 一、架构与数据层

### 1. Next.js 代理 30s 硬超时

**问题**：Next.js `rewrites` 代理有硬编码 30 秒超时，晨报生成等长耗时请求（通常 60–120s）会触发 Socket hang up。

**现状**：已通过 `NEXT_PUBLIC_API_URL` 直连后端绕过代理。需在 `frontend/.env.local` 配置：
```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**待优化**：
- 生产部署时需配置 `NEXT_PUBLIC_API_URL` 指向后端 API 域名。
- 若前后端同域部署（反向代理），需在 Nginx/Cloudflare 等层提高 `proxy_read_timeout`。

### 2. 多数据源切换（SQLite vs Supabase）

**问题**：`PFA_USE_DB`、Supabase 相关环境变量控制数据层切换，但部分模块（如 `load_portfolio`）仍依赖本地 `config/my-portfolio.json`，与 Supabase 持仓表未完全统一。

**待优化**：
- 明确「单机模式」与「多用户模式」的切换路径。
- 持仓 CRUD 统一走 `portfolio_store`，避免直接读写 JSON。

### 3. user_id 传递链不完整

**问题**：部分 API（如 `fetch-news`、`sentiment`）未显式传递 `user_id`，依赖 `get_current_user_id()` 从 JWT 解析。未登录时默认为 `admin`，多租户隔离需人工确认。

**待优化**：审计所有 `/api/*` 路由，确保读写均带 `user_id` 或 RLS 等效隔离。

---

## 二、性能与稳定性

### 4. 晨报流水线单次全量执行

**问题**：`run_full_pipeline_streaming` 一次性抓取所有持仓新闻、RSS、宏观，再调用 Analyst。持仓多时（如 20+）耗时可超 2 分钟，且无断点续传。

**待优化**：
- 分阶段缓存：Scout 抓取结果落库，Analyst 可单独重跑。
- 增量晨报：仅对「今日有新闻」的标的做分析。

### 5. 实时行情批量请求延迟

**问题**：Sina Finance API 按标的逐个请求，约 1.8s 完成全量。持仓多时首屏加载慢。

**待优化**：考虑东方财富批量接口或 WebSocket 订阅，减少串行请求。

### 6. 新闻抓取与情绪分析串行

**问题**：个股页「刷新数据」先 `fetch-news`（约 20–30s），再 `loadFeed` + `sentiment`。用户需等待全部完成才看到结果。

**待优化**：`fetch-news` 完成后先展示 Feed，情绪分析可异步进行并单独更新。

---

## 三、UI/UX 与响应式

### 7. 移动端布局未充分验证

**现状**：已做基础响应式（历史面板 `max-w-[280px]`、抽屉 `sm:max-w-[400px]`），但未在真机或 Chrome 移动模拟下完整走查。

**待优化**：
- 在 375px、414px 视口下验证：侧边栏、对话窗口、持仓表格横向滚动。
- 考虑移动端将 Ask PFA 改为底部浮层，避免遮挡主内容。

### 8. 情绪 Tab 占位内容

**现状**：情绪 Tab 中「7-Day Trend」「Sentiment by Source」「Sentiment Alerts」为占位，暂无数据源。

**待优化**：接入历史情绪序列或明确标注「即将推出」。

---

## 四、安全与合规

### 9. 券商凭证存储策略

**问题**：按 `docs/security-architecture.md`，券商密码不得明文存储。当前 Xueqiu 等渠道若需登录，凭证存储方式需人工确认（本地 Vault / 用户自管）。

**待优化**：文档化「只读模式」与「需登录模式」的边界，避免误存敏感信息。

### 10. 日志与脱敏

**问题**：异常日志中 `str(e)` 可能包含持仓片段或 API 响应。需确保生产环境不输出完整持仓或用户标识。

**待优化**：统一异常处理，对 `portfolio`、`holdings` 等关键词做脱敏或截断。

---

## 五、需人工确认的逻辑决策

| 序号 | 决策点 | 说明 |
|------|--------|------|
| 1 | 交易确认后的 Portfolio 刷新时机 | 当前 `onConfirm` 内同步调用 `refreshPortfolio()`，若后端写入延迟，可能短暂不一致。是否加轮询或乐观更新？ |
| 2 | 晨报「今日已生成」判断 | 按 `date === today` 判断，时区依赖客户端。多时区用户需确认。 |
| 3 | 情绪 API 的 symbol 误匹配 | 600900 可能匹配到「京能电力」等新闻，Analyst 返回的 reason 中曾出现标的混淆。需人工复核 prompt 或增加 symbol 校验。 |
| 4 | 未登录时的默认 user_id | 当前为 `admin`，与 Supabase 多用户模式冲突。是否强制登录后再使用核心功能？ |

---

## 六、本次 QA 已修复项

- 情绪 Tab：`Overall Sentiment` 展示 `label` + `reason`，有 `score` 时显示。
- API_BASE：支持 `NEXT_PUBLIC_API_URL` 直连后端，解决晨报 30s 超时。
- `.env.example`：根目录与 `frontend/` 各一份，便于部署与协作。
- 响应式：历史面板、对话抽屉增加 `max-w` / `sm:` 断点。

---

## 七、建议优先级

| 优先级 | 项 | 理由 |
|--------|-----|------|
| P0 | Next.js 30s 超时（已规避） | 晨报生成必配 `NEXT_PUBLIC_API_URL` |
| P1 | 晨报流水线分阶段 / 缓存 | 提升长耗时场景体验 |
| P1 | user_id 传递链审计 | 多租户前置条件 |
| P2 | 移动端真机验证 | 提升移动端可用性 |
| P2 | 情绪 Tab 占位完善 | 降低用户困惑 |
| P3 | 券商凭证与日志脱敏 | 安全合规收尾 |
