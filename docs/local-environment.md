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

1. **确认在项目根目录运行**（不要在其他目录执行 `streamlit run`）：
   ```bash
   cd /path/to/PFA
   streamlit run app/pfa_dashboard.py --server.port 8501
   ```
2. **清除 Python 缓存**（避免旧 .pyc 覆盖新代码）：
   ```bash
   cd /path/to/PFA
   rm -rf pfa/__pycache__ pfa/data/__pycache__ app/__pycache__ agents/__pycache__
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

### Streamlit（原有）

务必在**项目根目录**启动 Streamlit，这样 `app/pfa_dashboard.py` 里插入的 `ROOT` 和 `sys.path` 才会正确：

```bash
cd /path/to/PFA
streamlit run app/pfa_dashboard.py --server.port 8501
```

浏览器打开：http://localhost:8501

### Dash（新 UI）

Dash 版本提供传统 AI Chat 风格对话页，运行：

```bash
cd /path/to/PFA
python3 app_dash/app.py
```

浏览器打开：http://127.0.0.1:8050  

若需「执行分析」中的深度分析与 Auditor 审核，请设置环境变量：`DASHSCOPE_API_KEY`（必选）、`OPENAI_API_KEY`（可选，用于 Auditor 首选模型）。参见 `AGENTS.md` 中 Environment variables 小节。

### Next.js 前端 + FastAPI 后端

```bash
cd /path/to/PFA
uvicorn backend.main:app --reload --port 8000   # 后端
cd frontend && npm run dev                        # 前端
```

浏览器打开：http://localhost:3000

**晨报卡住时**：Next.js rewrites 代理有约 30 秒超时。在 `frontend/.env.local` 中设置 `NEXT_PUBLIC_API_URL=http://localhost:8000` 可直连后端，绕过代理超时。

## 多 Agent 架构与入口说明

- 控制中心入口是 **`app/pfa_dashboard.py`**，不是 `agents/secretary.py`。  
- 持仓与流水线编排由 **`agents/secretary_agent.py`** 提供，Streamlit 页面通过 `agents.secretary_agent` 调用。  
- 若你看到「用 `streamlit run agents/secretary.py` 启动」的说明，那是通用模板；本仓库请使用上面的 `app/pfa_dashboard.py` 命令。
