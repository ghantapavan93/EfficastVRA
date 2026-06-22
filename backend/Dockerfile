FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
WORKDIR /app

COPY pyproject.toml ./
COPY app ./app
RUN pip install --no-cache-dir -e ".[postgres]"

EXPOSE 8000
# The app seeds the synthetic scenario on first startup (lifespan) when the DB is empty.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
