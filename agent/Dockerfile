# 배포용 Dockerfile - 소스 코드가 이미지에 포함됨
# 개발용은 Dockerfile.dev 사용
FROM python:3.11-slim

WORKDIR /app

# 빌드 인수 정의
ARG OPENAI_CHAT_MODEL=gpt-5-mini
ARG ORCHESTRATOR_MODE=decentralized
ARG FORCE_NON_STREAMING=1
ARG AUTO_PROMOTE_AFTER_CLARIFICATION=0
ARG MCP_API_KEY=default-key

# 환경 변수로 설정 (빌드 타임에 설정되는 것들)
ENV OPENAI_CHAT_MODEL=${OPENAI_CHAT_MODEL}
ENV ORCHESTRATOR_MODE=${ORCHESTRATOR_MODE}
ENV FORCE_NON_STREAMING=${FORCE_NON_STREAMING}
ENV AUTO_PROMOTE_AFTER_CLARIFICATION=${AUTO_PROMOTE_AFTER_CLARIFICATION}
ENV MCP_API_KEY=${MCP_API_KEY}
ENV PYTHONUNBUFFERED=1

# LLM_PROVIDER는 런타임 환경변수로 주입 (Dockerfile에 포함하지 않음)

# 시스템 패키지 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY . .

# 워커 실행
CMD ["python", "worker.py"] 