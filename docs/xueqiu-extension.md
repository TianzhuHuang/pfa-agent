# PFA 雪球 Chrome 扩展

雪球 Web 端 API 有严格的防爬机制和动态 Token。通过扩展程序直接读取用户已登录的浏览器环境是最稳定的方案。

## 安装

1. 在 Chrome 中打开 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择项目根目录下的 `chrome-extension/` 文件夹

## 使用

1. 在浏览器中打开 [xueqiu.com](https://xueqiu.com) 并登录
2. 打开 PFA 设置页 → 社交与监控 → 雪球
3. 点击「同步 Cookie」，扩展会将 Cookie 同步到后端
4. 同步成功后即可在「雪球用户」中添加监控账号

## 安全

- Cookie 仅存储在本地 `config/xueqiu-auth.json`，不提交到 git
- 后端不会在日志中明文打印 Cookie
