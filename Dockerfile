# Dockerfile
FROM python:3.10-slim

WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 9898

CMD ["sh", "-c", "gunicorn -k uvicorn.workers.UvicornWorker \
    -w ${WORKERS:-4} \
    --threads 6 \
    -b 0.0.0.0:${PORT:-9898} \
    --timeout 1800 \
    --keep-alive 100 \
    --preload \
    main:app"]