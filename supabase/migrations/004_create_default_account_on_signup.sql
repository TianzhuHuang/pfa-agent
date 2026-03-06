-- 新用户注册时自动创建默认账户
-- 在 Supabase Dashboard SQL Editor 中执行，或使用 supabase db push

CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
  INSERT INTO public.accounts (user_id, account_id, name, base_currency, broker, account_type, balance)
  VALUES ($1, '默认', '默认', 'CNY', NULL, '股票', 0)
  ON CONFLICT (user_id, account_id) DO NOTHING;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();
