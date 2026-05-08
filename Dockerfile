# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
COPY app /app/app
COPY scripts /app/scripts
COPY start.sh /app/start.sh

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir . && chmod +x /app/start.sh

EXPOSE 8000
CMD ["/app/start.sh"]