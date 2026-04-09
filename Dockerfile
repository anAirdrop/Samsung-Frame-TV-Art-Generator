FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/

# Create directories for tokens and config
RUN mkdir -p /data/tokens

EXPOSE 8000

CMD ["uvicorn", "frame_art.main:app", "--host", "0.0.0.0", "--port", "8000"]
