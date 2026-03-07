# 本地环境与「云端对、本地错」说明

## 为什么云端 Cursor 浏览器测试正常，本地打开网页报错？

常见原因对比如下：

| 维度 | 云端 Cursor | 本地 checkout 后 |
|------|-------------|------------------|
| **工作目录** | 一般为仓库根目录，`sys.path` 和 `Path(__file__).parent.parent` 能正确找到 `pfa`、`agents`、`config` | 若在别的目录启动 Streamlit 或脚本，会找不到模块或配置文件 |
| **依赖** | 环境已预装 `requirements.txt` 及 pandas 等 | 未执行 `pip install -r requirements.txt` 会报 `ModuleNotFoundError` |
| **配置与目录** | `config/my-portfolio.json`、`config/data-sources.json` 和 `data/raw` 等通常存在 | 新 clone 可能缺少这些文件或目录，导致读写报错 |
| **代码分支** | 云端可能跑的是带完整 store API 的分支（如 `FeedItem`、`save_feed_items`、`load_all_analyses`） | 本地若是 main 或旧分支，`pfa.data.store` 可能缺少这些导出，导致 ImportError |
| **环境变量** | `DASHSCOPE_API_KEY` / `OPENAI_API_KEY` 可能已配置 | 未设置时，仅「深度分析 / 审核」会报错，基础抓取与面板仍可运行 |

## 若出现 ImportError: cannot import name 'FeedItem' / 'load_all_feed_items' / 'load_all_analyses'

1. **确认在项目根目录运行**（不要在其他目录执行后端或脚本）：
   ```bash
   cd /path/to/PFA
   uvicorn backend.main:app --reload --port 8000
   ```
2. **清除 Python 缓存**（避免旧 .pyc 覆盖新代码）：
   ```bash
   cd /path/to/PFA
    rm -rf pfa/__pycache__ pfa/data/__pycache__ agents/__pycache__
   ```
3. **确认 store 已正确导出**（在项目根目录执行）：
   ```bash
   python3 -c "from pfa.data.store import FeedItem, save_feed_items, load_all_feed_items, load_all_analyses; print('store OK')"
   ```
   若这里就报错，说明当前 `pfa/data/store.py` 缺少上述 API，需要保证使用带完整 store 的分支或已合并的代码。

## 推荐：本地一次性初始化

在**项目根目录**执行：

```bash
cd /path/to/PFA
python3 scripts/init_pfa_env.py
```

脚本会：

1. 安装 `requirements.txt` 依赖，并确保有 pandas  
2. 创建 `data/raw`、`data/store`、`config`（若不存在）及 `data/raw/.gitkeep`  
3. 若不存在则创建占位 `config/my-portfolio.json`、`config/data-sources.json`（不覆盖已有）  
4. 可选：安装 Playwright Chromium 驱动（用于本地浏览器 E2E 测试）

## 正确启动控制中心

### Next.js 前端 + FastAPI 后端

```bash
cd /path/to/PFA
uvicorn backend.main:app --reload --port 8000   # 后端
cd frontend && npm run dev                        # 前端
```

浏览器打开：http://localhost:3000

**晨报卡住时**：Next.js rewrites 代理有约 30 秒超时。在 `frontend/.env.local` 中设置 `NEXT_PUBLIC_API_URL=http://localhost:8000` 可直连后端，绕过代理超时。

## 本地 Supabase 调试

当需要本地调试 OCR 导入、持仓保存等与生产相同的数据流时，可配置 localhost 使用 Supabase（与生产同一数据库），避免每次部署到 ECS 才能验证。

### 1. 项目根目录 `.env`

从 `.env.production.example` 复制并填入（或沿用 ECS 上的值）：

- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `SUPABASE_JWT_SECRET`（JWKS 失败时 HS256 回退）
- `DASHSCOPE_API_KEY`（OCR 需要）

可选调试变量：

- `PFA_DEBUG_ERRORS=1`：保存失败时弹窗显示具体错误（如 schema 字段缺失、JWT 无效），便于排查「数据保存失败，请稍后重试」

### 2. 前端 `frontend/.env.local`

创建或编辑 `frontend/.env.local`：

```
NEXT_PUBLIC_SUPABASE_URL=https://你的项目.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...（anon key）
NEXT_PUBLIC_API_URL=http://localhost:8000
```

- `NEXT_PUBLIC_API_URL`：直连本地后端，避免代理超时
- Supabase 变量：与生产一致，用于登录和 JWT

### 3. 启动命令

```bash
# 终端 1：后端
cd /path/to/PFA
uvicorn backend.main:app --reload --port 8000

# 终端 2：前端
cd frontend && npm run dev
```

访问 http://localhost:3000，使用 Supabase 账号登录后，持仓、OCR 导入等操作会写入 Supabase。

### 常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 添加持仓提示「数据保存失败」 | Supabase schema 与代码不一致、JWT 解析失败 | 设置 `PFA_DEBUG_ERRORS=1` 查看具体错误；检查 `SUPABASE_JWT_SECRET` 与 Supabase Dashboard 一致 |
| storage-status 返回 `user_id: admin` | 未登录或 JWT 未正确传递 | 确保已登录；检查 `frontend/.env.local` 中 Supabase 变量已配置 |
| JWT 解析失败 | JWKS 不可达或 Legacy Secret 不匹配 | 本地网络可访问 Supabase JWKS；或配置 `SUPABASE_JWT_SECRET`（Settings → API → JWT Secret） |

### 快速初始化

执行 `bash scripts/init_local_supabase.sh` 可自动从模板复制 `.env` 和 `frontend/.env.local`（不覆盖已有文件），然后按提示填入 Supabase 变量。

## 机房部署与价格代理（阿里云等）

在阿里云等机房中，新浪/东财/Yahoo/Binance/CoinGecko 等价格接口常被拦截（403 或不可达），而腾讯 A/港股接口通常可用。为在机房环境正常获取实时行情与估值，可配置 **Cloudflare Workers 代理**：

- **环境变量**: `PFA_PROXY_BASE`，例如 `https://pfa-proxy.huangtianzhu5746.workers.dev/`
- 设置后，东财/新浪/Yahoo/Binance/CoinGecko 的请求经该 Worker 转发；腾讯 A/港股保持直连；数字货币优先走 OKX（直连），再经代理回退 Binance/CoinGecko
- 价格探测脚本在配置代理后会自动经 Worker 发起（除腾讯外）：`python3 scripts/probe_price_apis.py`

详见 **docs/data-sources.md** §3.6（机房代理与 PFAIntelEngine）。

## 多 Agent 架构与入口说明

- 控制中心入口是 **`app/pfa_dashboard.py`**，不是 `agents/secretary.py`。  
- 持仓与流水线编排由 **`agents/secretary_agent.py`** 提供，Streamlit 页面通过 `agents.secretary_agent` 调用。  
- 若你看到「用 `streamlit run agents/secretary.py` 启动」的说明，那是通用模板；本仓库请使用上面的 `app/pfa_dashboard.py` 命令。
