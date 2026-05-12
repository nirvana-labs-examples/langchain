FROM python:3.12-slim

WORKDIR /app

# System deps for psycopg + fastembed onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .
COPY docs/ ./docs/

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
