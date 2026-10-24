# Production Dockerfile for Wind Forecast Decision Portal — FastAPI Backend
FROM python:3.12-slim

# Set environment variables for clean container execution
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    PORT=8000

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code and cached datasets
COPY app ./app
COPY main.py .
COPY data ./data

# Expose backend service port
EXPOSE 8000

# Container healthcheck using Python urllib to avoid curl dependency and verify dataset loading
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request, json, os; port = os.environ.get('PORT', '8000'); res = urllib.request.urlopen(f'http://127.0.0.1:{port}/api/health'); exit(0 if (res.status == 200 and json.loads(res.read()).get('data_loaded') is True) else 1)"

# Start uvicorn server listening on configured PORT with fallback to 8000
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
