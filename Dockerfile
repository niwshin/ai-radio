FROM python:3.12-slim

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ai_radio ./ai_radio
COPY static ./static

EXPOSE 8000

CMD ["uvicorn", "ai_radio.main:app", "--host", "0.0.0.0", "--port", "8000"]
