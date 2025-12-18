#!/bin/bash
# 백엔드/에이전트 배포 스크립트
# Jenkins 파이프라인에서 사용되는 백엔드/에이전트 배포 로직

set -e  # 오류 발생 시 스크립트 종료

# 매개변수 처리
DEPLOY_TARGET="${1:-all}"  # all, backend, agent 중 하나

echo "🚀 KB-Web에서 배포 시작... (대상: ${DEPLOY_TARGET})"

# Registry에서 이미지 풀
echo "Docker Registry에서 이미지 풀 중..."
REGISTRY_URL="${REGISTRY_URL}"
BUILD_NUMBER="${BUILD_NUMBER}"
BACKEND_IMAGE="${BACKEND_IMAGE}"
AGENT_IMAGE="${AGENT_IMAGE}"

# 배포 대상에 따라 필요한 이미지만 풀
case "${DEPLOY_TARGET}" in
    "backend")
        echo "백엔드 이미지만 풀 중..."
        docker pull ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}
        docker tag ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER} ${BACKEND_IMAGE}:${BUILD_NUMBER}
        ;;
    "agent")
        echo "에이전트 이미지만 풀 중..."
        docker pull ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER}
        docker tag ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER} ${AGENT_IMAGE}:${BUILD_NUMBER}
        ;;
    *)
        echo "모든 이미지 풀 중..."
        docker pull ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}
        docker pull ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER}
        docker tag ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER} ${BACKEND_IMAGE}:${BUILD_NUMBER}
        docker tag ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER} ${AGENT_IMAGE}:${BUILD_NUMBER}
        ;;
esac

echo "기존 컨테이너 중지 및 제거 중..."

# 배포 대상에 따른 선택적 컨테이너 정리
case "${DEPLOY_TARGET}" in
    "backend")
        echo "백엔드 컨테이너만 정리 중..."
        docker stop maice-back || true
        docker rm maice-back || true
        ;;
    "agent")
        echo "에이전트 컨테이너만 정리 중..."
        docker stop maice-agent || true
        docker rm maice-agent || true
        ;;
    *)
        echo "전체 애플리케이션 컨테이너 정리 중..."
        docker stop maice-back maice-agent || true
        docker rm maice-back maice-agent || true
        ;;
esac

echo "✅ 컨테이너 정리 완료"

echo "새 버전 배포 중..."

# 배포용 docker-compose로 인프라 서비스 시작
echo "배포용 인프라 서비스 시작..."

# 네트워크가 없으면 생성
echo "Docker 네트워크 확인 및 생성..."
if ! docker network ls | grep -q "maicesystem_maice_network"; then
    echo "네트워크가 없음, 생성 중..."
    docker network create maicesystem_maice_network || {
        echo "❌ 네트워크 생성 실패"
        exit 1
    }
    echo "✅ 네트워크 생성 완료"
else
    echo "✅ 네트워크 이미 존재함"
fi

# 네트워크 상태 확인 (간단하게만)
echo "✅ 네트워크 설정 완료"

# 애플리케이션 컨테이너만 정리 (인프라는 젠킨스에서 처리됨)
echo "애플리케이션 컨테이너 정리..."
case "${DEPLOY_TARGET}" in
    "backend")
        echo "백엔드 컨테이너만 정리 중..."
        docker stop maice-back || true
        docker rm maice-back || true
        ;;
    "agent")
        echo "에이전트 컨테이너만 정리 중..."
        docker stop maice-agent || true
        docker rm maice-agent || true
        ;;
    *)
        echo "전체 애플리케이션 컨테이너 정리 중..."
        docker stop maice-back maice-agent || true
        docker rm maice-back maice-agent || true
        ;;
esac

# Redis 서비스 상태 확인 (젠킨스에서 이미 시작됨)
echo "Redis 서비스 상태 확인..."
sleep 3
echo "Redis 컨테이너 상태:"
docker ps --filter "name=redis" --format "table {{.Names}}\t{{.Status}}" || echo "Redis 컨테이너 없음"

# PostgreSQL 연결은 이미 Database Setup 단계에서 확인됨
echo "PostgreSQL 연결 정보:"
echo "DB_HOST: ${DB_HOST}"
echo "DB_PORT: ${DB_PORT:-5432}"
echo "DB_USER: ${DB_USER:-postgres}"
echo "DB_PASSWORD: ${DB_PASSWORD:+[설정됨]}"

# 선택적 환경 변수들을 환경에서 가져오기 (이미 검증됨)
ANTHROPIC_KEY=${ANTHROPIC_API_KEY:-""}
GOOGLE_KEY=${GOOGLE_API_KEY:-""}
GOOGLE_REDIRECT=${GOOGLE_REDIRECT_URI:-"https://maice.kbworks.xyz/auth/google/callback"}
MCP_URL=${MCP_SERVER_URL:-""}
MCP_OPENAI_BASE_URL=${MCP_OPENAI_BASE_URL:-""}
MCP_API_KEY=${MCP_API_KEY:-""}

# 배포 대상에 따른 분기 처리
case "${DEPLOY_TARGET}" in
    "backend")
        echo "백엔드 컨테이너 실행 중..."
        echo "필수 환경 변수 확인 (마스킹):"
        echo "OPENAI_API_KEY 길이: ${#OPENAI_API_KEY}"
        echo "GOOGLE_CLIENT_ID 길이: ${#GOOGLE_CLIENT_ID}"
        echo "GOOGLE_CLIENT_SECRET 길이: ${#GOOGLE_CLIENT_SECRET}"
        echo "ADMIN_USERNAME: ${ADMIN_USERNAME}"
        echo "SESSION_SECRET_KEY 길이: ${#SESSION_SECRET_KEY}"
        
        echo "데이터베이스 연결 정보 확인:"
        echo "DATABASE_URL: ${DATABASE_URL}"

        docker run -d --name maice-back --restart unless-stopped --network maicesystem_maice_network \
            -e DATABASE_URL="${DATABASE_URL}" \
            -e REDIS_URL=redis://redis:6379 \
            -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
            -e ANTHROPIC_API_KEY="${ANTHROPIC_KEY}" \
            -e GOOGLE_API_KEY="${GOOGLE_KEY}" \
            -e ADMIN_USERNAME="${ADMIN_USERNAME}" \
            -e ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
            -e SESSION_SECRET_KEY="${SESSION_SECRET_KEY}" \
            -e GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}" \
            -e GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}" \
            -e GOOGLE_REDIRECT_URI="${GOOGLE_REDIRECT}" \
            -e MCP_SERVER_URL="${MCP_URL}" \
            -e LLM_PROVIDER="${LLM_PROVIDER:-mcp}" \
            -e OPENAI_CHAT_MODEL=gpt-5-mini \
            -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \
            -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \
            -e MCP_MODEL=penGPT \
            -e ORCHESTRATOR_MODE=decentralized \
            -e FORCE_NON_STREAMING=1 \
            -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \
            -e PYTHONUNBUFFERED=1 \
            -e ENVIRONMENT=production \
            -e ENABLE_MAICE_TEST=false \
            ${BACKEND_IMAGE}:${BUILD_NUMBER}
        ;;
    "agent")
        echo "에이전트 컨테이너 실행 중..."
        echo "필수 환경 변수 확인 (마스킹):"
        echo "OPENAI_API_KEY 길이: ${#OPENAI_API_KEY}"
        
        echo "데이터베이스 연결 정보 확인:"
        echo "AGENT_DATABASE_URL: ${AGENT_DATABASE_URL}"

        echo "🔍 컨테이너 실행 시 LLM_PROVIDER 확인: LLM_PROVIDER=${LLM_PROVIDER:-mcp}"
        
        docker run -d --name maice-agent --restart unless-stopped --network maicesystem_maice_network \
            -e AGENT_DATABASE_URL="${AGENT_DATABASE_URL}" \
            -e REDIS_URL=redis://redis:6379 \
            -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
            -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
            -e GOOGLE_API_KEY="${GOOGLE_KEY}" \
            -e MCP_SERVER_URL="${MCP_URL}" \
            -e MCP_OPENAI_BASE_URL="${MCP_OPENAI_BASE_URL}" \
            -e MCP_API_KEY="${MCP_API_KEY}" \
            -e LLM_PROVIDER="${LLM_PROVIDER:-mcp}" \
            -e OPENAI_CHAT_MODEL=gpt-5-mini \
            -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \
            -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \
            -e MCP_MODEL=penGPT \
            -e ORCHESTRATOR_MODE=decentralized \
            -e FORCE_NON_STREAMING=1 \
            -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \
            -e PYTHONUNBUFFERED=1 \
            ${AGENT_IMAGE}:${BUILD_NUMBER}
        ;;
    *)
        echo "❌ 잘못된 배포 대상: ${DEPLOY_TARGET}"
        echo "사용법: $0 [backend|agent]"
        exit 1
        ;;
esac

# 배포 대상에 따른 완료 처리
case "${DEPLOY_TARGET}" in
    "backend")
        echo "🏗️ 백엔드 배포 완료!"
        
        # 백엔드 컨테이너 상태 확인만 수행
        sleep 10
        if docker ps | grep -q maice-back; then
            echo "✅ 백엔드 컨테이너 실행 중"
        else
            echo "❌ 백엔드 컨테이너 실행 실패"
            echo "백엔드 로그 확인:"
            docker logs maice-back --tail 20
            exit 1
        fi
        ;;
        
    "agent")
        echo "🤖 에이전트 배포 완료!"
        
        # 에이전트 컨테이너 상태 확인
        sleep 10
        if docker ps | grep -q maice-agent; then
            echo "✅ 에이전트 컨테이너 실행 중"
        else
            echo "❌ 에이전트 컨테이너 실행 실패"
            echo "에이전트 로그 확인:"
            docker logs maice-agent --tail 20
            exit 1
        fi
        ;;
        
    "all"|*)
        echo "🚀 전체 배포 완료!"
        
        # 컨테이너 상태 확인만 수행
        sleep 10
        echo "컨테이너 상태 확인:"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
        
        # 백엔드 컨테이너 상태 확인
        if docker ps | grep -q maice-back; then
            echo "✅ 백엔드 컨테이너 실행 중"
        else
            echo "❌ 백엔드 컨테이너 실행 실패"
            echo "백엔드 로그 확인:"
            docker logs maice-back --tail 20
            exit 1
        fi

        # 에이전트 컨테이너 상태 확인
        if docker ps | grep -q maice-agent; then
            echo "✅ 에이전트 컨테이너 실행 중"
        else
            echo "❌ 에이전트 컨테이너 실행 실패"
            echo "에이전트 로그 확인:"
            docker logs maice-agent --tail 20
            exit 1
        fi
        ;;
esac

echo "✅ ${DEPLOY_TARGET} 배포 완료!"