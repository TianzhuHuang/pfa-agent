-- 为 holdings 表添加 ocr_confirmed、price_deviation_warn 列。若使用 Supabase 需执行此迁移。
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS ocr_confirmed BOOLEAN;
ALTER TABLE holdings ADD COLUMN IF NOT EXISTS price_deviation_warn BOOLEAN;
