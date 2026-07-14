#
# CloudScope NiceGUI listens on port 8080 inside the image.
#
# Stamped web deploy (recommended; macOS or Oracle host):
#   ./packaging/deploy_cloudscope_web.sh
# That wrapper writes src/cloudscope/_build_info.py before `docker compose
# up --build`, so App Info shows commit/version identity. This Dockerfile
# fails the build if that stamp file is missing.
#
# Build image only (requires a prior stamp):
#   python3 packaging/write_build_info.py
#   docker build -t cloudscope:latest .
#
# Run locally and open in browser:
#   docker run --rm -p 8080:8080 cloudscope:latest
#   then visit http://localhost:8080
#
# Run locally with a mounted data folder available to the server/container:
#   docker run --rm -p 8080:8080 -v "$PWD/data:/data" cloudscope:latest
#   then load files from /data inside the CloudScope UI
#
# Deploy on a remote host or cloud service:
#   set CLOUDSCOPE_REMOTE=1 and CLOUDSCOPE_NATIVE=0
#   expose the platform-provided PORT, or default to 8080
#

FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV CLOUDSCOPE_REMOTE=1
ENV CLOUDSCOPE_NATIVE=0
ENV CLOUDSCOPE_SINGLE_WINDOW=1
ENV CLOUDSCOPE_RELOAD=0
ENV CLOUDSCOPE_HOST=0.0.0.0
ENV PORT=8080

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Fail fast when the image was built without a host-side stamp. Use:
#   ./packaging/deploy_cloudscope_web.sh
RUN test -f src/cloudscope/_build_info.py || ( \
    echo "ERROR: missing src/cloudscope/_build_info.py" >&2; \
    echo "Run ./packaging/deploy_cloudscope_web.sh (or packaging/write_build_info.py) before building." >&2; \
    exit 1 \
  )

RUN uv sync --frozen --no-dev --no-editable

EXPOSE 8080

CMD ["uv", "run", "python", "src/cloudscope/app.py"]
