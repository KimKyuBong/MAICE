#!/bin/bash

# 에이전트 Docker 빌드 스크립트
# 환경 변수 주입 및 이미지 빌드

set -e

echo "🤖 에이전트 Docker 이미지 빌드 시작..."

# 필수 환경 변수 검증
if [ -z "$AGENT_IMAGE" ]; then
    echo "❌ AGENT_IMAGE 환경 변수가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$BUILD_NUMBER" ]; then
    echo "❌ BUILD_NUMBER 환경 변수가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$DB_HOST" ]; then
    echo "❌ DB_HOST 환경 변수가 설정되지 않았습니다"
    exit 1
fi

# 빌드 인수 구성
BUILD_ARGS=""
if [ "$FORCE_REBUILD" = "true" ]; then
    BUILD_ARGS="--no-cache"
fi

# 환경 변수 기반 빌드 인수 설정
if [ -z "${AGENT_DATABASE_URL}" ]; then
    AGENT_DATABASE_URL="postgresql://postgres:postgres@${DB_HOST}:5432/maice_agent"
fi

echo "📋 빌드 설정:"
echo "  - 이미지명: ${AGENT_IMAGE}"
echo "  - 빌드번호: ${BUILD_NUMBER}"
echo "  - DB_HOST: ${DB_HOST}"
echo "  - AGENT_DATABASE_URL: ${AGENT_DATABASE_URL}"
echo "  - 강제재빌드: ${FORCE_REBUILD:-false}"
echo "  - LLM_PROVIDER는 런타임 환경변수로 주입됩니다"

# Docker 이미지 빌드 (기본값만 설정, 실제 환경 변수는 배포 시 주입)
echo "🔨 Docker 이미지 빌드 중..."
docker build -f agent/Dockerfile \
    --build-arg OPENAI_CHAT_MODEL="${OPENAI_CHAT_MODEL:-gpt-5-mini}" \
    --build-arg ORCHESTRATOR_MODE="${ORCHESTRATOR_MODE:-decentralized}" \
    --build-arg FORCE_NON_STREAMING="${FORCE_NON_STREAMING:-1}" \
    --build-arg AUTO_PROMOTE_AFTER_CLARIFICATION="${AUTO_PROMOTE_AFTER_CLARIFICATION:-0}" \
    --build-arg AGENT_DATABASE_URL="${AGENT_DATABASE_URL}" \
    --build-arg OPENAI_EMBED_MODEL="${OPENAI_EMBED_MODEL:-text-embedding-3-small}" \
    --build-arg REDIS_URL="${REDIS_URL:-redis://redis:6379}" \
    --build-arg MCP_API_KEY="${MCP_API_KEY:-default-mcp-key}" \
    ${BUILD_ARGS} \
    -t "${AGENT_IMAGE}:${BUILD_NUMBER}" agent/ || {
    echo "❌ 에이전트 Docker 이미지 빌드 실패!"
    exit 1
}

# 최신 태그 추가
docker tag "${AGENT_IMAGE}:${BUILD_NUMBER}" "${AGENT_IMAGE}:latest"

echo "✅ 에이전트 Docker 이미지 빌드 완료"
echo "  - 이미지: ${AGENT_IMAGE}:${BUILD_NUMBER}"
echo "  - 최신 태그: ${AGENT_IMAGE}:latest"
