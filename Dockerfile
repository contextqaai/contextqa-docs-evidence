FROM node:22-bookworm-slim AS web
WORKDIR /build
COPY apps/web/package*.json apps/web/
RUN npm ci --prefix apps/web --ignore-scripts
COPY apps/web apps/web
COPY cqa_artifacts/loop_ui cqa_artifacts/loop_ui
RUN npm run build --prefix apps/web

FROM python:3.12-slim AS runtime
WORKDIR /app
COPY pyproject.toml README.md ./
COPY cqa_artifacts ./cqa_artifacts
COPY requirements-hosted.lock ./
RUN pip install --no-cache-dir -r requirements-hosted.lock && pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home docs && mkdir /data && chown docs:docs /data
COPY migrations ./migrations
COPY --from=web /build/apps/web/dist ./apps/web/dist
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
USER docs
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2).status == 200 else 1)"]
CMD ["uvicorn", "cqa_artifacts.hosted.server:create_app", "--factory", "--app-dir", "/app", "--host", "0.0.0.0", "--port", "8080", "--no-access-log", "--no-proxy-headers"]
