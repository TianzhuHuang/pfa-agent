-- PFA Supabase 完整 Schema 一次性执行
-- 在 Supabase Dashboard → SQL Editor 中执行
-- 执行后到 Settings → API 点击 "Reload schema cache"

-- ========== 1. 表结构（若不存在则创建）==========
CREATE TABLE IF NOT EXISTS holdings (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  symbol TEXT NOT NULL,
  name TEXT,
  market TEXT DEFAULT 'A',
  quantity NUMERIC DEFAULT 0,
  cost_price NUMERIC,
  currency TEXT,
  exchange TEXT,
  account TEXT DEFAULT '默认',
  source TEXT DEFAULT 'manual',
  position_pct NUMERIC,
  memo_history JSONB DEFAULT '[]',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS accounts (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  account_id TEXT NOT NULL,
  name TEXT NOT NULL,
  base_currency TEXT DEFAULT 'CNY',
  broker TEXT,
  account_type TEXT DEFAULT '股票',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, account_id)
);

CREATE TABLE IF NOT EXISTS portfolio_meta (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  meta_key TEXT NOT NULL,
  meta_value JSONB,
  updated_at TIMESTAMPTZ DEFAULT NOW(),
  UNIQUE(user_id, meta_key)
);

CREATE TABLE IF NOT EXISTS chat_messages (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS briefing_reports (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users NOT NULL,
  report_date TIMESTAMPTZ NOT NULL,
  content TEXT NOT NULL,
  summary TEXT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_settings (
  user_id UUID REFERENCES auth.users PRIMARY KEY,
  data_sources JSONB DEFAULT '{}',
  telegram_chat_id TEXT,
  alert_threshold_pct NUMERIC DEFAULT 3.0,
  preferences JSONB DEFAULT '{}',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ========== 2. 补充缺失列（已存在则跳过）==========
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS balance NUMERIC DEFAULT 0;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS currency TEXT;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS exchange TEXT;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS ocr_confirmed BOOLEAN;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS price_deviation_warn BOOLEAN;

-- ========== 3. RLS 与策略 ==========
ALTER TABLE holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_meta ENABLE ROW LEVEL SECURITY;
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE briefing_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users own holdings" ON holdings;
CREATE POLICY "Users own holdings" ON holdings FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users own accounts" ON accounts;
CREATE POLICY "Users own accounts" ON accounts FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users own portfolio_meta" ON portfolio_meta;
CREATE POLICY "Users own portfolio_meta" ON portfolio_meta FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users own chat_messages" ON chat_messages;
CREATE POLICY "Users own chat_messages" ON chat_messages FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users own briefing_reports" ON briefing_reports;
CREATE POLICY "Users own briefing_reports" ON briefing_reports FOR ALL USING (auth.uid() = user_id);

DROP POLICY IF EXISTS "Users own user_settings" ON user_settings;
CREATE POLICY "Users own user_settings" ON user_settings FOR ALL USING (auth.uid() = user_id);

-- ========== 4. 新用户注册时自动创建默认账户 ==========
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.accounts (user_id, account_id, name, base_currency, broker, account_type, balance)
  VALUES (NEW.id, '默认', '默认', 'CNY', NULL, '股票', 0)
  ON CONFLICT (user_id, account_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
