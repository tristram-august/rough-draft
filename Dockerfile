# Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY alembic.ini /app/alembic.ini
COPY app /app/app
COPY scripts /app/scripts

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "app.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]