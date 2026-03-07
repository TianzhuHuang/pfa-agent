# PFA 数据源与实现方式（Data Sources）

本文档列出**支持的渠道类型**及实现方式，供 Phase 2「感官层」开发参考。数据仅拉取**用户在自己配置中添加的源**，不做默认强制。

---

## 1. 支持的渠道类型

| 类型     | 说明                     | 用户配置方式           | 实现方式（Phase 2） |
|----------|--------------------------|------------------------|----------------------|
| RSS      | 新闻/博客订阅            | `channels.rss_urls[]`  | RSS MCP 或 fetcher，增量拉取、去重 |
| 雪球     | 用户关注的雪球博主动态   | `channels.xueqiu_user_ids[]` | Fetcher 或 MCP（AJAX + Cookie），fallback 可用 Playwright |
| Twitter  | 用户关注的 Twitter 账号  | `channels.twitter_handles[]` | Barresider x-mcp 或 API，按列表拉取 |
| 财经 API | 财报、股价、新闻等       | 由系统或用户配置 API Key | financial-datasets/mcp-server 或同类 |

---

## 2. 实现优先级（建议）

1. **RSS**：最标准、易实现；先做通用 RSS Fetcher，按 user-profile 中的 `rss_urls` 拉取，增量去重落库。
2. **财经 API**：集成 financial-datasets 或类似 MCP，提供结构化数据。
3. **复杂网页（雪球、Twitter）**：在 API/RSS 不可用或需登录时，使用 Playwright 等浏览器方案作为 fallback（参考 XiaoHongShuMCP 逻辑）。

---

## 3. 已实现的数据源

### 3.1 东方财富搜索 API（Phase 2 首个实现）

- **脚本**: `scripts/fetch_holding_news.py`
- **API**: `https://search-api-web.eastmoney.com/search/jsonp`
- **覆盖**: A 股、港股均可通过关键词搜索获取新闻
- **特点**: 无需 API Key，返回 JSONP 格式，支持分页
- **存储**: 原始数据存入 `data/raw/fetch_<timestamp>.json`
- **分析**: 可选 `--analyze` 参数调用通义千问 (qwen-plus) 进行深度筛选（需 `DASHSCOPE_API_KEY`）

### 3.2 RSS 抓取器

- **脚本**: `scripts/fetch_rss.py`
- **配置**: `config/my-portfolio.json` 中的 `channels.rss_urls[]`
- **运行**: `python3 scripts/fetch_rss.py`
- **特点**: 使用 `feedparser` 解析 RSS/Atom feeds，通过标题/摘要关键词匹配关联到持仓标的
- **存储**: 统一数据层 `data/store/feeds/`
- **已验证源**: 36kr (`https://36kr.com/feed`)

### 3.3 搜索关键词策略

- 使用持仓标的**名称**作为主搜索词（如「贵州茅台」「中海油」）
- 支持**别名映射**：同一标的可配置多个搜索关键词以扩大覆盖
- 结果经**去重**和**时间窗口过滤**后存储

### 3.4 统一数据层

- **模块**: `pfa/data/store.py`
- **模型**: `FeedItem`（新闻条目）、`AnalysisRecord`（分析记录）
- **存储**: `data/store/feeds/` 和 `data/store/analyses/`
- **查询**: 支持按标的、来源、时间窗口、日期过滤
- 所有抓取脚本（东方财富、RSS）均通过此层统一落库
- **FeedItem 扩展字段**（可选，供个股情绪/概览使用）：`sentiment`（positive/negative/neutral）、`impact_pts`（对情绪分数的影响点数）；见 `docs/ui-design-system.md` §7.6

### 3.5 投研面板

投研面板已迁移至 Next.js + FastAPI（`frontend/` + `backend/`）。

### 3.6 多源价格 API（Phase 2 里程碑）

持仓估值引擎 `pfa/portfolio_valuation.py` 的 `get_realtime_prices()` 聚合多源价格：

| 资产类型 | market 值 | 数据源 | 模块 |
|----------|-----------|--------|------|
| A 股 | A | 腾讯优先（机房首选），东方财富/新浪回退 | pfa/realtime_quote.py |
| 港股 | HK | 腾讯优先，新浪/Yahoo 回退 | pfa/realtime_quote.py |
| 美股 | US | 新浪优先，Yahoo 回退 | pfa/realtime_quote.py |
| 数字货币 | OT / CRYPTO / account_type=数字货币 | OKX 优先，Binance/CoinGecko 回退 | pfa/crypto_quote.py |
| 新加坡股 | SGX | Yahoo Finance (T14.SI) | pfa/sgx_quote.py |

- **OKX**: `https://www.okx.com/api/v5/market/ticker?instId={SYM}-USDT`，数字货币首选，直连
- **Binance**: `https://api.binance.com/api/v3/ticker/price`，机房易被墙，配置代理后经 Worker
- **CoinGecko**: `https://api.coingecko.com/api/v3/simple/price`，支持主流币种，可经代理
- **Yahoo Finance**: `https://query1.finance.yahoo.com/v8/finance/chart/{symbol}`，SGX 标的使用 `.SI` 后缀（如 T14.SI）
- **传统代理**: 未配置 `PFA_PROXY_BASE` 时，可配置 `HTTP_PROXY` / `HTTPS_PROXY` 以访问 Binance、CoinGecko、Yahoo

#### 机房代理（Cloudflare Workers）

在阿里云等机房环境下，新浪/东财/Yahoo/Binance/CoinGecko 常返回 403 或不可达，**腾讯**通常可用。通过 Cloudflare Workers 做 HTTP 代理可打通上述接口：

- **环境变量**: `PFA_PROXY_BASE`，例如 `https://pfa-proxy.huangtianzhu5746.workers.dev/`（末尾斜杠可选）
- **行为**: 设置后，东财/新浪/Yahoo/Binance/CoinGecko 的请求经 Worker 转发（`GET {PFA_PROXY_BASE}?url={encoded_target_url}`）；**腾讯 A/港股保持直连**
- **实现**: `pfa/proxy_fetch.py` 提供 `get(url, params=..., headers=..., timeout=...)`，未设置 `PFA_PROXY_BASE` 时与 `requests.get` 行为一致

#### PFAIntelEngine（双轨制行情引擎）

- **模块**: `pfa/market_data_engine.py`
- **用途**: 标准化价格接口，返回 `{ symbol, price, source, updated_at }`，便于「高净值资产追踪」等扩展
- **双轨**: 数字货币走 **OKX**；港/美/SGX 走 **Yahoo**（经 `PFA_PROXY_BASE` 代理）
- **接口**: `PFAIntelEngine().get_multiple_prices(symbols_list)`，`symbols_list` 每项为 `{ symbol, market }`，失败项为 `None`
- **与估值衔接**: 配置了 `PFA_PROXY_BASE` 时，`get_realtime_prices` 会对仍缺失的 HK/US/SGX/数字货币 用 PFAIntelEngine 补全，无需改前端即可在机房获得实时盈亏

### 3.7 价格接口探测脚本（机房环境选源）

阿里云等机房 IP 常被新浪等接口拦截，部署前可运行探测脚本评估各数据源可用性与速度：

```bash
python3 scripts/probe_price_apis.py
```

- **代理模式**: 若设置了 `PFA_PROXY_BASE`，除腾讯外所有探测请求（网易/新浪/东财/Yahoo/Binance/CoinGecko）均经 Worker 发起；腾讯仍直连。输出标题会标注「经 PFA_PROXY_BASE 代理」。
- 探测接口：腾讯财经、网易财经、新浪、东方财富、Yahoo、Binance、CoinGecko。输出按速度排序的成功接口，便于选择主/备数据源。

---

## 4. 数据可信度与噪音过滤（Phase 2 必含）

- **权重管理**：用户可为不同关注对象设置可信度权重；摘要与预警按权重加权。
- **交叉验证**：多源同时提到同一标的/事件时触发高优先级预警；单源仅作背景入库。

详见规划文档 Phase 2 与 §8。
