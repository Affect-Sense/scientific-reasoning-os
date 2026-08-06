FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ src/
COPY config/ config/
ENV PYTHONUNBUFFERED=1
# Cloud Run injects PORT; default 8080 for local docker runs.
CMD exec uvicorn src.api.app:app --host 0.0.0.0 --port ${PORT:-8080}
