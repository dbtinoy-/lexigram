FROM python:3.12-slim
RUN apt-get update && apt-get install -y ffmpeg imagemagick fonts-dejavu-core && rm -rf /var/lib/apt/lists/*
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/
RUN uv python install 3.11 && ln -sf "$(uv python find 3.11)" /usr/bin/python3.11

# Additional build contexts:
#   framework  → ../../framework/lexigram/   (monorepo root)
#   tools      → ../tools/                   (5.creators/tools/)

# Path deps in pyproject.toml:
#   ../../framework/lexigram/lexigram → /app/framework/lexigram/lexigram
WORKDIR /app/project/shorts-creator

# Framework packages
COPY --from=framework lexigram-contracts/ /app/framework/lexigram/lexigram-contracts/
COPY --from=framework lexigram/ /app/framework/lexigram/lexigram/
COPY --from=framework lexigram-admin/ /app/framework/lexigram/lexigram-admin/
COPY --from=framework lexigram-ai/ /app/framework/lexigram/lexigram-ai/
COPY --from=framework lexigram-ai-feedback/ /app/framework/lexigram/lexigram-ai-feedback/
COPY --from=framework lexigram-ai-mcp/ /app/framework/lexigram/lexigram-ai-mcp/
COPY --from=framework lexigram-ai-memory/ /app/framework/lexigram/lexigram-ai-memory/
COPY --from=framework lexigram-ai-observability/ /app/framework/lexigram/lexigram-ai-observability/
COPY --from=framework lexigram-ai-prompt/ /app/framework/lexigram/lexigram-ai-prompt/
COPY --from=framework lexigram-ai-rag/ /app/framework/lexigram/lexigram-ai-rag/
COPY --from=framework lexigram-ai-session/ /app/framework/lexigram/lexigram-ai-session/
COPY --from=framework lexigram-ai-skills/ /app/framework/lexigram/lexigram-ai-skills/
COPY --from=framework lexigram-ai-workers/ /app/framework/lexigram/lexigram-ai-workers/
COPY --from=framework lexigram-audit/ /app/framework/lexigram/lexigram-audit/
COPY --from=framework lexigram-auth/ /app/framework/lexigram/lexigram-auth/
COPY --from=framework lexigram-cache/ /app/framework/lexigram/lexigram-cache/
COPY --from=framework lexigram-events/ /app/framework/lexigram/lexigram-events/
COPY --from=framework lexigram-graphql/ /app/framework/lexigram/lexigram-graphql/
COPY --from=framework lexigram-monitor/ /app/framework/lexigram/lexigram-monitor/
COPY --from=framework lexigram-multimedia/ /app/framework/lexigram/lexigram-multimedia/
COPY --from=framework lexigram-multimedia-beat/ /app/framework/lexigram/lexigram-multimedia-beat/
COPY --from=framework lexigram-multimedia-interpolate/ /app/framework/lexigram/lexigram-multimedia-interpolate/
COPY --from=framework lexigram-multimedia-upscale/ /app/framework/lexigram/lexigram-multimedia-upscale/
COPY --from=framework lexigram-nosql/ /app/framework/lexigram/lexigram-nosql/
COPY --from=framework lexigram-search/ /app/framework/lexigram/lexigram-search/
COPY --from=framework lexigram-testing/ /app/framework/lexigram/lexigram-testing/
COPY --from=framework lexigram-multimedia-video/ /app/framework/lexigram/lexigram-multimedia-video/
COPY --from=framework lexigram-multimedia-tts/ /app/framework/lexigram/lexigram-multimedia-tts/
COPY --from=framework lexigram-multimedia-music/ /app/framework/lexigram/lexigram-multimedia-music/
COPY --from=framework lexigram-multimedia-image/ /app/framework/lexigram/lexigram-multimedia-image/
COPY --from=framework lexigram-storage/ /app/framework/lexigram/lexigram-storage/
COPY --from=framework lexigram-web/ /app/framework/lexigram/lexigram-web/
COPY --from=framework lexigram-ui/ /app/framework/lexigram/lexigram-ui/
COPY --from=framework lexigram-ai-llm/ /app/framework/lexigram/lexigram-ai-llm/
COPY --from=framework lexigram-cli/ /app/framework/lexigram/lexigram-cli/
COPY --from=framework lexigram-sql/ /app/framework/lexigram/lexigram-sql/
COPY --from=framework lexigram-tasks/ /app/framework/lexigram/lexigram-tasks/
COPY --from=framework lexigram-ai-agents/ /app/framework/lexigram/lexigram-ai-agents/
COPY --from=framework pyproject.toml /app/framework/lexigram/
COPY --from=framework uv.lock /app/framework/lexigram/

# Install deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Source code, config, migrations
COPY src/ ./src/
COPY migrations/ ./migrations/
COPY application.yaml ./
COPY asgi_app.py ./
RUN mkdir -p data/renders data/runs

EXPOSE 8080
ENV DSM_PORT=8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request,sys; urllib.request.urlopen('http://127.0.0.1:8080/api/health/header', timeout=4)" \
    || exit 1
# --reload (dev hot-restart) is opt-in via DSM_RELOAD=1; it would otherwise
# restart in-flight renders on any container filesystem change.
CMD ["sh", "-c", "exec uv run uvicorn asgi_app:app --host 0.0.0.0 --port 8080${DSM_RELOAD:+ --reload}"]
