# Phase 4 设计：Supabase 多用户架构

## 目标

将 PFA 从「单机工具」升级为「多用户 SaaS」。

## 技术方案

### 1. Supabase 集成

| 组件 | 用途 |
|---|---|
| **Auth** | 邮箱/Google 登录，Streamlit 侧边栏集成 |
| **PostgreSQL** | 替代本地 JSON 存储 |
| **Row Level Security** | 每个用户只能读写自己的数据 |

### 2. 数据库 Schema

```sql
-- 用户持仓
CREATE TABLE holdings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  symbol TEXT NOT NULL,
  name TEXT,
  market TEXT CHECK (market IN ('A', 'HK', 'US', 'OTHER')),
  cost_price NUMERIC,
  quantity NUMERIC,
  account TEXT,
  source TEXT,
  memo_history JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 分析记录
CREATE TABLE analyses (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  analysis_time TIMESTAMPTZ DEFAULT NOW(),
  model TEXT,
  holdings_analyzed TEXT,
  news_count_input INTEGER,
  analysis JSONB,
  token_usage JSONB,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 用户配置（数据源、Telegram 绑定等）
CREATE TABLE user_settings (
  user_id UUID REFERENCES auth.users PRIMARY KEY,
  telegram_chat_id TEXT,
  alert_threshold_pct NUMERIC DEFAULT 3.0,
  data_sources JSONB DEFAULT '{}',
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Users own holdings" ON holdings
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users own analyses" ON analyses
  FOR ALL USING (auth.uid() = user_id);
CREATE POLICY "Users own settings" ON user_settings
  FOR ALL USING (auth.uid() = user_id);
```

### 3. 迁移路径

1. 安装 `supabase-py` SDK
2. 创建 `pfa/data/supabase_store.py`（与 `store.py` 相同接口）
3. 侧边栏增加登录/注册组件
4. `store.py` 检测：有 Supabase 连接 → 用云端，否则 → 本地 JSON
5. 迁移现有 JSON 数据到 Supabase

### 4. 环境变量

| 变量 | 说明 |
|---|---|
| `SUPABASE_URL` | Project URL |
| `SUPABASE_ANON_KEY` | Anon Key (公开) |
| `SUPABASE_SERVICE_KEY` | Service Role Key (私密，仅后端) |

### 5. Telegram 绑定

每个用户在 `user_settings.telegram_chat_id` 中绑定自己的 Chat ID。
定时调度器按 user_id 遍历，分别推送。
