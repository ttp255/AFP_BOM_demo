# syntax=docker/dockerfile:1

FROM python:3.13-slim AS backend

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


FROM node:22-alpine AS frontend-dependencies

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci


FROM node:22-alpine AS frontend-builder

WORKDIR /app
COPY --from=frontend-dependencies /app/node_modules ./node_modules
COPY frontend/ .

ARG NEXT_PUBLIC_API_URL=http://localhost:8000
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL

RUN npm run build


FROM node:22-alpine AS frontend

ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1

WORKDIR /app

COPY --from=frontend-builder /app/package.json /app/package-lock.json ./
COPY --from=frontend-builder /app/node_modules ./node_modules
COPY --from=frontend-builder /app/.next ./.next
COPY --from=frontend-builder /app/public ./public

EXPOSE 3000

CMD ["npm", "run", "start", "--", "-H", "0.0.0.0"]
