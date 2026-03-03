# PFA v2 快速启动

## 分支

开发在 `pfa-v2-dev` 分支进行，可随时切回 `main` 使用旧版 Streamlit/Dash。

## 启动

### 1. 后端（必须在项目根目录）

```bash
cd /path/to/PFA   # 务必在 PFA 根目录
uvicorn backend.main:app --reload --port 8000
```

### 2. 前端

```bash
cd frontend
npm run dev
```

浏览器访问 http://localhost:3000

### 3. 环境变量

- 后端：在项目根目录创建 `.env`，配置 `DASHSCOPE_API_KEY`（OCR 截图识别、AI 对话）
- 前端：`NEXT_PUBLIC_API_URL=http://localhost:8000`（可选，默认即此）

### 4. 排查接口异常

若「股票搜索未找到结果」或「截图识别报错」，先确认后端正常：

```bash
# 直接访问后端（确保 8000 端口）
curl http://localhost:8000/api/ready
curl "http://localhost:8000/api/portfolio/search?q=茅台"
```

`/api/ready` 会返回 `stock_search_ok`、`DASHSCOPE_API_KEY_set` 等，便于定位问题。

## 当前实现

- ✅ Header（Logo + 导航）
- ✅ Dashboard 骨架（Total Wealth、持仓明细、空状态）
- ✅ `/api/portfolio` 持仓估值
- ✅ `/api/chat/stream` AI 流式对话（SSE）
- ⏳ 对话 UI 接入 SSE
- ⏳ Briefing / Analysis / Settings 页面
- ⏳ 录入持仓弹窗
- ⏳ 登录/退出
