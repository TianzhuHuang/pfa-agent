# Supabase 认证配置与邮件问题排查

## 注册后收不到确认邮件

### 1. 先检查

- **垃圾箱 / 推广邮件**：Supabase 默认发件方易被标记为垃圾邮件
- **等待几分钟**：邮件可能延迟送达
- **邮箱是否正确**：确认注册时填写的邮箱无误

### 2. 方案 A：关闭邮件确认（适合开发 / 内测）

注册后可直接登录，无需点击邮件链接：

1. 打开 [Supabase Dashboard](https://supabase.com/dashboard) → 选择项目
2. **Authentication** → **Providers** → **Email**
3. 关闭 **Confirm email**

关闭后，新注册用户会视为已确认，可直接登录。

### 3. 方案 B：配置自定义 SMTP（适合生产）

Supabase 默认邮件有频率限制且易进垃圾箱，建议接入 Resend、SendGrid 等：

1. 在 [Resend](https://resend.com) 注册并获取 API Key
2. Supabase Dashboard → **Project Settings** → **Authentication** → **SMTP Settings**
3. 启用 **Custom SMTP**，填写：
   - Host: `smtp.resend.com`
   - Port: `465`
   - Username: `resend`
   - Password: Resend API Key

### 4. 相关文档

- [Supabase Email Auth](https://supabase.com/docs/guides/auth/auth-email)
- [Supabase Custom SMTP](https://supabase.com/docs/guides/auth/auth-smtp)
