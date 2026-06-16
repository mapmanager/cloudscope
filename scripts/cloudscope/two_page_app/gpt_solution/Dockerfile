FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN pip install --no-cache-dir nicegui

COPY multi_window_demo.py /app/multi_window_demo.py

ENV CLOUDSCOPE_DEMO_MODE=web
ENV CLOUDSCOPE_HOST=0.0.0.0
ENV PORT=8080

EXPOSE 8080

CMD ["python", "/app/multi_window_demo.py"]
