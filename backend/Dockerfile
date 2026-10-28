FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TRUSTTRACE_DB_PATH=/data/trusttrace.db \
    TRUSTTRACE_KEY_PATH=/data/.trusttrace-signing-key.pem

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . ./
RUN useradd --system --uid 10001 --create-home trusttrace \
    && mkdir -p /data \
    && chown trusttrace:trusttrace /data

USER trusttrace
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
