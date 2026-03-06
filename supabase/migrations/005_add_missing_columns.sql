-- 修复 PGRST204：补充 Supabase 表缺失列
-- 在 Supabase Dashboard → SQL Editor 中执行
-- 执行后若仍报错，到 Settings → API 点击 "Reload schema cache"

-- accounts: balance（003 可能未执行）
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS balance NUMERIC DEFAULT 0;

-- holdings: currency, exchange（若表由旧 schema 创建可能缺失）
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS currency TEXT;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS exchange TEXT;

-- holdings: ocr_confirmed, price_deviation_warn（OCR 批量录入需要，002 可能未执行）
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS ocr_confirmed BOOLEAN;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS price_deviation_warn BOOLEAN;
