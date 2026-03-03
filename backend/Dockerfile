# PFA Backend — FastAPI
# 构建上下文为项目根目录，需在根目录执行: docker build -f backend/Dockerfile .
FROM python:3.12-slim

WORKDIR /app

# 安装后端依赖（backend/requirements.txt）+ 根目录依赖（含 sqlalchemy 等）
COPY requirements.txt backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt -r backend/requirements.txt

# 复制整个项目（backend 需导入 pfa/ agents/）
COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
