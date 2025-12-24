# 배포용 Dockerfile - 소스 코드가 이미지에 포함됨
# 개발용은 Dockerfile.dev 사용
FROM python:3.11-slim

WORKDIR /app

# 빌드 인수 정의
ARG OPENAI_CHAT_MODEL=gpt-5-mini
ARG ORCHESTRATOR_MODE=decentralized
ARG FORCE_NON_STREAMING=1
ARG AUTO_PROMOTE_AFTER_CLARIFICATION=0
ARG DATABASE_URL=postgresql://postgres:postgres@localhost:5432/maice_web
ARG GEMINI_API_KEY=""

# 환경 변수로 설정
ENV OPENAI_CHAT_MODEL=${OPENAI_CHAT_MODEL}
ENV ORCHESTRATOR_MODE=${ORCHESTRATOR_MODE}
ENV FORCE_NON_STREAMING=${FORCE_NON_STREAMING}
ENV AUTO_PROMOTE_AFTER_CLARIFICATION=${AUTO_PROMOTE_AFTER_CLARIFICATION}
ENV DATABASE_URL=${DATABASE_URL}
ENV GEMINI_API_KEY=${GEMINI_API_KEY}
ENV PYTHONUNBUFFERED=1

# Set timezone to Asia/Seoul
ENV TZ=Asia/Seoul
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir bcrypt==4.0.1

# Static files are not needed for API-only backend

# Copy application source code
COPY . .

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--workers", "4", "--timeout-keep-alive", "30"] 