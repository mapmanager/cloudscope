#
# CloudScope NiceGUI listens on port 8080 inside the image.
#
# Build image locally:
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
# Run with Docker Compose:
#   docker compose up --build cloudscope
#   then visit http://localhost:8080
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
ENV CLOUDSCOPE_RELOAD=0
ENV CLOUDSCOPE_HOST=0.0.0.0
ENV PORT=8080

COPY pyproject.toml uv.lock README.md ./
COPY src ./src

RUN uv sync --frozen --no-dev --no-editable

EXPOSE 8080

CMD ["uv", "run", "python", "src/cloudscope/app.py"]
