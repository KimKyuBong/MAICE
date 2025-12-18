# 테스트용 학생 테스터 에이전트 컨테이너
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY runner.py /app/runner.py
COPY dataset.jsonl /app/dataset.jsonl

ENV REDIS_URL=redis://redis:6379 \
    NUM_SAMPLES=5 \
    PERSONAS=all \
    OUTPUT_DIR=/app/output \
    DATASET_PATH=/app/data/evaluation_statistics.json \
    PARAPHRASE_WITH_LLM=1 \
    MISTAKE_PROB=0.35 \
    STYLE_INTENSITY=0.8

RUN mkdir -p /app/output

CMD ["python", "-u", "/app/runner.py"]
