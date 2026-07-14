# syntax=docker/dockerfile:1.7
FROM golang:1.24-alpine AS rmapi-builder
ARG RMAPI_VERSION=434da60d178dd04e0659fb502ea1251600c5d6ef
RUN apk add --no-cache git
WORKDIR /src
RUN git init . && git remote add origin https://github.com/ddvk/rmapi.git && \
    git fetch --depth 1 origin "${RMAPI_VERSION}" && git checkout --detach FETCH_HEAD
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/rmapi .

FROM ghcr.io/astral-sh/uv:0.8.3 AS uv

FROM python:3.12-slim-bookworm AS python-builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=never
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

FROM python:3.12-slim-bookworm AS runtime
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    APP_DATA_DIR=/data \
    HOME=/config \
    XDG_CONFIG_HOME=/config \
    XDG_DATA_HOME=/config \
    RMAPI_CONFIG=/config/rmapi.conf
RUN groupadd --system --gid 10001 app && \
    useradd --system --uid 10001 --gid app --home-dir /config --shell /usr/sbin/nologin app && \
    mkdir -p /app /data /config && chown -R app:app /app /data /config
WORKDIR /app
COPY --from=python-builder --chown=app:app /app/.venv /app/.venv
COPY --from=rmapi-builder /out/rmapi /usr/local/bin/rmapi
COPY --chown=app:app remarkable_news ./remarkable_news
USER app
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)"]
CMD ["uvicorn", "remarkable_news.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*"]
