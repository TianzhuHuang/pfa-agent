-- 为 accounts 表添加 balance 列。若使用 Supabase 需执行此迁移。
ALTER TABLE accounts ADD COLUMN IF NOT EXISTS balance NUMERIC DEFAULT 0;
