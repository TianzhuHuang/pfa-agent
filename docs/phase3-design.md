# Phase 3 设计：知识库与 Skills

本文档定义 Phase 3 的核心架构——基于统一数据层的知识库与 Skill 系统。

---

## 1. 目标

将 Phase 2 抓取的原始数据（东方财富新闻、RSS 订阅等）转化为**可检索的知识**，
支撑 Skill 系统生成结构化的投研输出。

---

## 2. 知识库结构

### 2.1 数据流

```
RSS / 东方财富 / 雪球
        ↓
  scripts/fetch_*.py  (抓取)
        ↓
  pfa/data/store.py   (统一 FeedItem 存储)
        ↓
  pfa/knowledge/      (知识库: 索引 + 检索)
        ↓
  pfa/skills/          (Skill: 基于知识库输出分析)
```

### 2.2 存储模型

| 层级 | 存储位置 | 格式 | 说明 |
|------|----------|------|------|
| 原始数据 | `data/store/feeds/` | JSON (FeedItem) | 按来源 + 时间戳分文件 |
| 分析记录 | `data/store/analyses/` | JSON (AnalysisRecord) | 每次 LLM 分析一条记录 |
| 知识索引 | `data/store/index/` | JSON (未来: 向量数据库) | 标的 → FeedItem 映射、关键词索引 |

### 2.3 查询接口 (pfa/data/store.py 已实现)

- `load_all_feed_items(symbol, source, since_hours, date_str)` — 按标的/来源/时间过滤
- `load_all_analyses()` / `load_analysis_by_date(date)` — 分析记录查询
- `save_feed_items(items, label)` — 统一落库

---

## 3. 第一个 Skill：持仓新闻摘要

### 3.1 定义

| 属性 | 值 |
|------|-----|
| **Skill 名称** | `holding_news_digest` |
| **输入** | 持仓列表 (from `config/my-portfolio.json`) + 时间窗口 |
| **数据来源** | `pfa/data/store.py` 中的 FeedItem（东方财富 + RSS） |
| **处理** | 通义千问 qwen-plus，从 FeedItem 中筛选 top-3 |
| **输出** | Markdown 格式分析报告 (AnalysisRecord) |

### 3.2 当前实现

`scripts/fetch_holding_news.py --analyze` 已包含此 Skill 的核心逻辑：
1. 加载持仓 → 2. 抓取新闻 → 3. 写入统一数据层 → 4. 调用 Qwen 分析 → 5. 存储分析结果

### 3.3 后续迭代

- 将 Skill 逻辑从脚本中抽取为独立模块 `pfa/skills/news_digest.py`
- 支持多数据源混合输入（东方财富 + RSS + 雪球）
- 引入向量检索，按语义相关性排序而非仅关键词匹配

---

## 4. RSS 数据源

### 4.1 实现

- 脚本: `scripts/fetch_rss.py`
- 读取 `config/my-portfolio.json` 中的 `channels.rss_urls[]`
- 使用 `feedparser` 解析 RSS/Atom feeds
- 输出写入 `pfa/data/store.py` 的 FeedItem

### 4.2 与持仓关联

RSS 条目通过**标题 / 摘要中的标的名称匹配**关联到持仓：
- 遍历每条 RSS 条目
- 检查标题 + 摘要是否包含任一持仓标的的名称/别名
- 匹配到的条目标记对应的 symbol

---

## 5. 向量化检索（后续迭代）

当前阶段使用关键词匹配；后续计划：
- 使用 DashScope 文本嵌入 API 生成向量
- 本地存储向量（FAISS 或 Chroma）
- 支持语义检索：「与我持仓相关的宏观政策变化」
