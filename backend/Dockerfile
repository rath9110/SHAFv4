FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# Install Chromium only (no chromedriver)
RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    fonts-liberation fonts-dejavu-core fonts-noto-color-emoji \
    ca-certificates curl unzip \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY . .
ENV PORT=8000
EXPOSE 8000
# Use shell form to allow variable expansion
CMD uvicorn fetching_service:app --host 0.0.0.0 --port ${PORT:-8000}
