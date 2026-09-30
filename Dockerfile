# 多阶段构建：Node 构建前端 → 产物拷入 Python 运行镜像
FROM node:20-alpine AS frontend
WORKDIR /build
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DB_PATH=/app/data/app.db \
    PRONOUNCE_CACHE_DIR=/app/data/cache/pronounce \
    STATIC_DIR=/app/frontend/dist

WORKDIR /app
COPY backend/pyproject.toml ./
COPY backend/src ./src
COPY backend/alembic ./alembic
COPY backend/alembic.ini ./
COPY backend/seeds ./seeds
RUN pip install --no-cache-dir .

COPY --from=frontend /build/dist /app/frontend/dist

EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
