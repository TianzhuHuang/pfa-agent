# PFA v2 阶段开发里程碑

> 本文档记录 PFA v2（Next.js + FastAPI + Supabase 多用户）阶段的功能交付、开发节点、未完善项与风险点，便于后续开发与交接。

---

## 一、功能与里程碑

### 1.1 架构升级（2025-02）

| 里程碑 | 说明 | 关键提交 |
|--------|------|----------|
| **PFA v2 架构** | 前后端分离：Next.js (App Router) + FastAPI，对标 Stake + Gemini 深色风格 | `12e2e8c` |
| **Supabase 多用户** | 认证、RLS、持仓/账户/对话按 `user_id` 隔离 | `947452d`、`484e32e` |
| **本地模式** | 点击 Logo 或按钮跳过 Supabase 认证，使用 admin + JSON 持仓 | `11f9aa0`、`9368248` |

### 1.2 持仓与录入

| 里程碑 | 说明 | 关键提交 |
|--------|------|----------|
| **智能搜索添加** | 东方财富 API 搜索标的，支持交易所标签、成本价/数量/日期录入 | `57adf1a` |
| **EntryModal 优化** | 搜索项 Avatar、交易所标签、表单校验、FX 估算 | 近期 |
| **账户管理** | 多账户、删除账户 | `641f263` |
| **OCR 截图识别** | Qwen-VL 多模态识别持仓截图 | `e66dcab` |

### 1.3 新用户与引导

| 里程碑 | 说明 | 关键提交 |
|--------|------|----------|
| **Empty State Onboarding** | 新用户渐进式引导，三个入口（添加持仓/晨报/设置） | `26a5d9c` |
| **新用户持仓隔离修复** | 新用户不再自动加载 admin 的 JSON 持仓，避免生产泄露测试数据 | `5b8c876` |

### 1.4 部署与运维

| 里程碑 | 说明 | 关键提交 |
|--------|------|----------|
| **Docker 部署** | docker-compose 构建 Next.js + FastAPI，阿里云 ECS 部署 | `995bc38`、`f625418` |
| **部署 .env 修复** | rsync 排除 .env、构建显式 `--env-file .env`，新增 `scripts/deploy-ecs.sh` | `9cf551d` |

### 1.5 Phase 3 与数据源

| 里程碑 | 说明 | 参考文档 |
|--------|------|----------|
| **知识库设计** | 统一 FeedItem 存储、AnalysisRecord、Skill 系统 | `docs/phase3-design.md` |
| **数据源配置** | RSS / URL / 雪球 动态管理，写入 `config/data-sources.json` | `docs/data-sources.md` |
| **Apple 配置** | Phase 3 相关配置与前端入口 | 近期 |

---

## 二、未完善功能

### 2.1 高优先级

| 项 | 说明 | 参考 |
|----|------|------|
| **晨报流水线分阶段** | 当前一次性抓取全量，持仓多时超 2 分钟；需 Scout 落库 + Analyst 可单独重跑 | `docs/pfa-待优化大项清单.md` §4 |
| **user_id 传递链审计** | 部分 API 未显式传 `user_id`，依赖 `get_current_user_id()`；多租户需全面审计 | 同上 §3 |
| **生产 .env 首次创建** | 新部署 ECS 需手动创建 `/opt/pfa/.env`，rsync 已排除 .env 不再覆盖 | `docs/deployment-aliyun.md` 4.3 |

### 2.2 中优先级

| 项 | 说明 | 参考 |
|----|------|------|
| **情绪 Tab 占位** | 「7-Day Trend」「Sentiment by Source」等为占位，暂无数据源 | 待优化清单 §8 |
| **移动端验证** | 基础响应式已有，未在 375px/414px 真机完整走查 | 同上 §7 |
| **Next.js 代理超时** | 生产若前后端同域，需 Nginx 提高 `proxy_read_timeout` | 同上 §1 |

### 2.3 低优先级

| 项 | 说明 |
|----|------|
| **券商凭证存储** | 按 security-architecture，密码不得明文；Xueqiu 等需登录时的存储策略待定 |
| **日志脱敏** | 异常日志中 `str(e)` 可能含持仓片段，生产需脱敏 |
| **向量化检索** | Phase 3 规划，当前为关键词匹配 |

---

## 三、风险点

### 3.1 数据与安全

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| **新用户误加载 admin 数据** | 已修复：Supabase 不再迁移 JSON；SQLite 仅 admin 空数据时迁移 | `pfa/portfolio_store.py` |
| **已受影响用户数据** | 若此前新用户已拿到 admin 持仓，需在 Supabase 手动清理 | 见下方 SQL |
| **.env 被 rsync 覆盖** | 已修复：rsync 增加 `--exclude .env` | `docs/deployment-aliyun.md` |

**Supabase 清理受影响用户示例：**
```sql
DELETE FROM holdings WHERE user_id = '<affected_user_uuid>';
DELETE FROM accounts WHERE user_id = '<affected_user_uuid>';
DELETE FROM portfolio_meta WHERE user_id = '<affected_user_uuid>';
```

### 3.2 多租户与认证

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| **未登录默认 user_id=admin** | 与 Supabase 多用户模式冲突；是否强制登录后使用核心功能待决策 | 待优化清单 §4 |
| **JWT 解析失败回退** | `get_current_user_id()` 失败时回退 admin，需确保 RLS 与后端逻辑一致 | 审计 API 路由 |

### 3.3 部署与运维

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| **构建时 .env 未加载** | Docker Compose 在部分环境不自动加载 .env | 使用 `docker compose --env-file .env build` 或 `scripts/deploy-ecs.sh` |
| **首次部署无 .env** | ECS 上需手动创建 .env | 按 `docs/deployment-aliyun.md` 4.3 执行 |

### 3.4 性能与稳定性

| 风险 | 说明 | 缓解措施 |
|------|------|----------|
| **晨报 30s 超时** | Next.js rewrites 代理硬超时 | 配置 `NEXT_PUBLIC_API_URL` 直连后端 |
| **行情批量请求延迟** | Sina API 按标的串行，约 1.8s | 考虑东方财富批量或 WebSocket |
| **新闻+情绪串行** | 个股页刷新先 fetch-news 再 sentiment，耗时长 | 可改为 fetch 完成后先展示，情绪异步更新 |

---

## 四、关键文件索引

| 类别 | 文件 | 用途 |
|------|------|------|
| 产品与架构 | `docs/product-scope.md` | MVP 范围、Phase 边界 |
| 安全 | `docs/security-architecture.md` | 只读模式、脱敏、隐私 |
| 数据模型 | `config/user-profile.schema.json` | 持仓、账户 Schema |
| 部署 | `docs/deployment-aliyun.md` | 阿里云 ECS 部署 |
| 部署 | `scripts/deploy-ecs.sh` | 一键部署（校验 .env + build） |
| 待优化 | `docs/pfa-待优化大项清单.md` | 架构瓶颈、性能、逻辑决策 |
| 认证 | `docs/auth-supabase.md` | 邮件确认、SMTP 配置 |

---

## 五、后续开发建议

1. **优先**：完成 user_id 传递链审计，确保所有 `/api/*` 读写均带 user_id 或 RLS 等效隔离。
2. **其次**：晨报流水线分阶段缓存，Scout 落库后 Analyst 可单独重跑，支持增量晨报。
3. **部署**：新环境首次部署务必按 `docs/deployment-aliyun.md` 创建 .env，使用 `bash scripts/deploy-ecs.sh` 构建。
4. **文档**：每完成一个 Phase 或重要功能，更新本文档与对应 `docs/` 文件。
