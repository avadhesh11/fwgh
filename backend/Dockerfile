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
  CMD python -c "import urllib.request, json; res = urllib.request.urlopen('http://127.0.0.1:8000/api/health'); exit(0 if (res.status == 200 and json.loads(res.read()).get('data_loaded') is True) else 1)"

# Start uvicorn server bound to 0.0.0.0
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
