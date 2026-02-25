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

### 3.2 搜索关键词策略

- 使用持仓标的**名称**作为主搜索词（如「贵州茅台」「中海油」）
- 支持**别名映射**：同一标的可配置多个搜索关键词以扩大覆盖
- 结果经**去重**和**时间窗口过滤**后存储

---

## 4. 数据可信度与噪音过滤（Phase 2 必含）

- **权重管理**：用户可为不同关注对象设置可信度权重；摘要与预警按权重加权。
- **交叉验证**：多源同时提到同一标的/事件时触发高优先级预警；单源仅作背景入库。

详见规划文档 Phase 2 与 §8。
