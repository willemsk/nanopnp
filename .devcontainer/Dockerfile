# Python pinned to .python-version; uv copied in from Astral's official image
# per their documented multi-stage pattern (https://docs.astral.sh/uv/guides/integration/docker/).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /workspace
