# Python pinned to .python-version; uv copied in from Astral's official image
# per their documented multi-stage pattern (https://docs.astral.sh/uv/guides/integration/docker/).
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /workspace

# The gmsh wheel loads X and GL libraries at import and raises OSError without
# them; the push gate requires Gmsh, as CI does (.knowledge/07-software-stack.md
# section 5).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libglu1-mesa libxft2 libxinerama1 libxcursor1 \
    && rm -rf /var/lib/apt/lists/*
