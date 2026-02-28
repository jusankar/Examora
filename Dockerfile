FROM node:20-alpine AS ui-builder
WORKDIR /ui
COPY frontend-shadcn/package.json frontend-shadcn/yarn.lock ./
RUN corepack enable && yarn install --frozen-lockfile
COPY frontend-shadcn/ ./
RUN yarn build

FROM python:3.11-slim AS runtime
WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY core ./core
COPY infrastructure ./infrastructure
COPY frontend ./frontend
COPY --from=ui-builder /ui/dist ./frontend-shadcn/dist
COPY --from=ui-builder /ui/public ./frontend-shadcn/public

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
