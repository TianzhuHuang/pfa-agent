-- PFA Phase 4: Multi-user tables
-- Run this in Supabase Dashboard → SQL Editor → New Query

-- 1. Holdings
CREATE TABLE IF NOT EXISTS public.holdings (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT DEFAULT '',
    market TEXT CHECK (market IN ('A', 'HK', 'US', 'OTHER')) DEFAULT 'A',
    cost_price NUMERIC DEFAULT 0,
    quantity NUMERIC DEFAULT 0,
    position_pct NUMERIC DEFAULT 0,
    account TEXT DEFAULT '',
    source TEXT DEFAULT 'manual',
    memo_history JSONB DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Analyses
CREATE TABLE IF NOT EXISTS public.analyses (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    analysis_id TEXT,
    analysis_time TIMESTAMPTZ DEFAULT NOW(),
    model TEXT DEFAULT '',
    holdings_analyzed TEXT DEFAULT '',
    news_count_input INTEGER DEFAULT 0,
    analysis JSONB,
    token_usage JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. User Settings
CREATE TABLE IF NOT EXISTS public.user_settings (
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE PRIMARY KEY,
    telegram_chat_id TEXT DEFAULT '',
    alert_threshold_pct NUMERIC DEFAULT 3.0,
    data_sources JSONB DEFAULT '{}'::jsonb,
    preferences JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Row Level Security
ALTER TABLE public.holdings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.analyses ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_settings ENABLE ROW LEVEL SECURITY;

-- Policies: users can only access their own data
CREATE POLICY "holdings_user_policy" ON public.holdings
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "analyses_user_policy" ON public.analyses
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "settings_user_policy" ON public.user_settings
    FOR ALL USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

-- 5. Indexes
CREATE INDEX IF NOT EXISTS idx_holdings_user ON public.holdings(user_id);
CREATE INDEX IF NOT EXISTS idx_holdings_symbol ON public.holdings(symbol);
CREATE INDEX IF NOT EXISTS idx_analyses_user ON public.analyses(user_id);
CREATE INDEX IF NOT EXISTS idx_analyses_time ON public.analyses(analysis_time DESC);
