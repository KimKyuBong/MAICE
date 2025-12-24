#!/bin/bash
# 단순 배포 스크립트
# Jenkins 파이프라인에서 사용되는 백엔드 배포 로직

set -e  # 오류 발생 시 스크립트 종료

# 매개변수 처리
DEPLOY_TARGET="${1:-backend}"  # backend, agent 중 하나
INFRA_ACTION="${2:-none}"       # 인프라 관리 작업 (none, restart, start, stop, status, config-check)
INFRA_SERVICE="${3:-all}"        # 인프라 서비스 (all, nginx, redis)

echo "🚀 KB-Web에서 단순 배포 시작... (대상: ${DEPLOY_TARGET})"
echo "🏗️ 인프라 관리 옵션: ${INFRA_ACTION} ${INFRA_SERVICE}"

# 인프라 관리 작업 실행
if [ "${INFRA_ACTION}" != "none" ]; then
    echo "🏗️ 인프라 관리 작업 실행: ${INFRA_ACTION} ${INFRA_SERVICE}"
    
    # 인프라 관리 스크립트 확인
    if [ -f "scripts/manage_infrastructure.sh" ]; then
        chmod +x scripts/manage_infrastructure.sh
        
        case "${INFRA_ACTION}" in
            "restart")
                ./scripts/manage_infrastructure.sh -r "${INFRA_SERVICE}"
                ;;
            "start")
                ./scripts/manage_infrastructure.sh -u "${INFRA_SERVICE}"
                ;;
            "stop")
                ./scripts/manage_infrastructure.sh -d "${INFRA_SERVICE}"
                ;;
            "status")
                ./scripts/manage_infrastructure.sh -s "${INFRA_SERVICE}"
                ;;
            "config-check")
                if [ "${INFRA_SERVICE}" = "nginx" ]; then
                    ./scripts/manage_infrastructure.sh -c nginx
                elif [ "${INFRA_SERVICE}" = "redis" ]; then
                    ./scripts/manage_infrastructure.sh -c redis
                else
                    echo "⚠️ 설정 확인은 nginx 또는 redis에 대해서만 가능합니다"
                fi
                ;;
            *)
                echo "⚠️ 알 수 없는 인프라 작업: ${INFRA_ACTION}"
                ;;
        esac
    else
        echo "⚠️ 인프라 관리 스크립트를 찾을 수 없습니다: scripts/manage_infrastructure.sh"
    fi
fi

# Registry에서 이미지 풀
echo "Docker Registry에서 이미지 풀 중..."
echo "환경 변수 확인:"
echo "  REGISTRY_URL: ${REGISTRY_URL}"
echo "  BUILD_NUMBER: ${BUILD_NUMBER}"
echo "  BACKEND_IMAGE: ${BACKEND_IMAGE}"
echo "  AGENT_IMAGE: ${AGENT_IMAGE}"

# 필수 환경 변수 검증
if [ -z "${REGISTRY_URL}" ]; then
    echo "❌ REGISTRY_URL이 설정되지 않았습니다"
    exit 1
fi
if [ -z "${BUILD_NUMBER}" ]; then
    echo "❌ BUILD_NUMBER가 설정되지 않았습니다"
    exit 1
fi
if [ -z "${BACKEND_IMAGE}" ]; then
    echo "❌ BACKEND_IMAGE가 설정되지 않았습니다"
    exit 1
fi
if [ -z "${AGENT_IMAGE}" ]; then
    echo "❌ AGENT_IMAGE가 설정되지 않았습니다"
    exit 1
fi

# Registry에서 이미지 풀
docker pull ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}
docker pull ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER}

# 로컬 이미지로 태깅
docker tag ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER} ${BACKEND_IMAGE}:${BUILD_NUMBER}
docker tag ${REGISTRY_URL}/${AGENT_IMAGE}:${BUILD_NUMBER} ${AGENT_IMAGE}:${BUILD_NUMBER}

# 단순 배포: 기존 백엔드 컨테이너 확인
echo "기존 백엔드 컨테이너 확인 중..."

# 네트워크 확인 및 생성
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

# 선택적 환경 변수들을 환경에서 가져오기
ANTHROPIC_KEY=${ANTHROPIC_API_KEY:-""}
GEMINI_KEY=${GEMINI_API_KEY:-""}
GOOGLE_REDIRECT=${GOOGLE_REDIRECT_URI:-"https://maice.kbworks.xyz/auth/google/callback"}
MCP_URL=${MCP_SERVER_URL:-""}

# 배포 대상에 따른 분기 처리
case "${DEPLOY_TARGET}" in
    "backend")
        echo "🏗️ 백엔드 Blue-Green 배포 시작..."
        
        # 기존 새 환경 컨테이너 정리 (혹시 남아있을 경우)
        echo "기존 ${NEW_ENV} 환경 컨테이너 정리 중..."
        docker stop maice-back || true
        docker rm maice-back || true
        
        # 새 환경에 백엔드 컨테이너 실행
        echo "새 ${NEW_ENV} 환경에 백엔드 컨테이너 실행 중..."
        echo "필수 환경 변수 확인 (마스킹):"
        echo "OPENAI_API_KEY 길이: ${#OPENAI_API_KEY}"
        echo "GOOGLE_CLIENT_ID 길이: ${#GOOGLE_CLIENT_ID}"
        echo "GOOGLE_CLIENT_SECRET 길이: ${#GOOGLE_CLIENT_SECRET}"
        echo "ADMIN_USERNAME: ${ADMIN_USERNAME}"
        echo "SESSION_SECRET_KEY 길이: ${#SESSION_SECRET_KEY}"
        
        echo "데이터베이스 연결 정보 확인:"
        echo "DATABASE_URL: ${DATABASE_URL}"

        echo "Docker 컨테이너 실행 명령어:"
        echo "docker run -d --name maice-back --network maicesystem_maice_network -p 8000:8000 \\"
        echo "  -e DATABASE_URL=\"${DATABASE_URL}\" \\"
        echo "  -e REDIS_URL=redis://redis:6379 \\"
        echo "  -e OPENAI_API_KEY=\"[MASKED]\" \\"
        echo "  -e ANTHROPIC_API_KEY=\"[MASKED]\" \\"
        echo "  -e GEMINI_API_KEY=\"[MASKED]\" \\"
        echo "  -e ADMIN_USERNAME=\"${ADMIN_USERNAME}\" \\"
        echo "  -e ADMIN_PASSWORD=\"[MASKED]\" \\"
        echo "  -e SESSION_SECRET_KEY=\"[MASKED]\" \\"
        echo "  -e GOOGLE_CLIENT_ID=\"[MASKED]\" \\"
        echo "  -e GOOGLE_CLIENT_SECRET=\"[MASKED]\" \\"
        echo "  -e GOOGLE_REDIRECT_URI=\"${GOOGLE_REDIRECT}\" \\"
        echo "  -e MCP_SERVER_URL=\"${MCP_URL}\" \\"
        echo "  -e LLM_PROVIDER=mcp \\"
        echo "  -e OPENAI_CHAT_MODEL=gpt-5-mini \\"
        echo "  -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \\"
        echo "  -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \\"
        echo "  -e MCP_MODEL=penGPT \\"
        echo "  -e ORCHESTRATOR_MODE=decentralized \\"
        echo "  -e FORCE_NON_STREAMING=1 \\"
        echo "  -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \\"
        echo "  -e PYTHONUNBUFFERED=1 \\"
        echo "  -e ENVIRONMENT=production \\"
        echo "  -e ENABLE_MAICE_TEST=false \\"
        echo "  ${BACKEND_IMAGE}:${BUILD_NUMBER}"
        
        # 기존 백엔드 컨테이너 중지 (새 컨테이너 실행 전)
        echo "🔄 기존 백엔드 컨테이너 중지 중..."
        EXISTING_CONTAINERS=$(docker ps -a --filter "name=maice-back" --format "{{.Names}}" 2>/dev/null || true)
        
        if [ -n "$EXISTING_CONTAINERS" ]; then
            echo "발견된 기존 백엔드 컨테이너들:"
            echo "$EXISTING_CONTAINERS"
            
            # 각 컨테이너 중지 및 제거
            echo "$EXISTING_CONTAINERS" | while read container_name; do
                if [ -n "$container_name" ]; then
                    echo "중지 중: $container_name"
                    docker stop "$container_name" 2>/dev/null || true
                    docker rm "$container_name" 2>/dev/null || true
                fi
            done
        else
            echo "기존 백엔드 컨테이너가 없습니다"
        fi
        
        echo "✅ 기존 백엔드 정리 완료"
        
        # 컨테이너 실행 (단순한 이름)
        CONTAINER_ID=$(docker run -d --name maice-back --network maicesystem_maice_network -p 8000:8000 \
            -e DATABASE_URL="${DATABASE_URL}" \
            -e REDIS_URL=redis://redis:6379 \
            -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
            -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
            -e GEMINI_API_KEY="${GEMINI_KEY}" \
            -e ADMIN_USERNAME="${ADMIN_USERNAME}" \
            -e ADMIN_PASSWORD="${ADMIN_PASSWORD}" \
            -e SESSION_SECRET_KEY="${SESSION_SECRET_KEY}" \
            -e GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}" \
            -e GOOGLE_CLIENT_SECRET="${GOOGLE_CLIENT_SECRET}" \
            -e GOOGLE_REDIRECT_URI="${GOOGLE_REDIRECT}" \
            -e MCP_SERVER_URL="${MCP_URL}" \
            -e LLM_PROVIDER=mcp \
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
            ${BACKEND_IMAGE}:${BUILD_NUMBER})
        
        echo "컨테이너 ID: ${CONTAINER_ID}"
        
        # 컨테이너 실행 확인
        sleep 3
        if docker ps --filter "name=maice-back" --format "{{.Names}}" | grep -q "maice-back"; then
            echo "✅ 컨테이너 실행 성공: maice-back"
        else
            echo "❌ 컨테이너 실행 실패: maice-back"
            echo "컨테이너 로그 확인:"
            docker logs ${CONTAINER_ID} --tail 50
            echo "모든 컨테이너 상태:"
            docker ps -a --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
            exit 1
        fi
        
        # 새 컨테이너 헬스체크 대기
        echo "새 백엔드 컨테이너 헬스체크 대기 중..."
        MAX_RETRIES=30
        RETRY_COUNT=0
        
        while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
            echo "헬스체크 시도 $((RETRY_COUNT + 1))/${MAX_RETRIES}..."
            
            # 컨테이너 상태 확인
            if ! docker ps --filter "name=maice-back" --format "{{.Names}}" | grep -q "maice-back"; then
                echo "❌ 컨테이너가 실행되지 않음: maice-back"
                echo "컨테이너 로그 확인:"
                docker logs maice-back --tail 50
                echo "모든 컨테이너 상태:"
                docker ps -a --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                exit 1
            fi
            
            # 헬스체크 실행 (호스트에서 Docker 네트워크를 통해 확인)
            HEALTH_CHECK_SUCCESS=false
            
            # 방법 1: 호스트에서 컨테이너 IP로 직접 헬스체크
            CONTAINER_IP=$(docker inspect maice-back --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
            if [ -n "$CONTAINER_IP" ]; then
                echo "컨테이너 IP: ${CONTAINER_IP}"
                
                if curl -f --max-time 5 http://localhost:8000/health/simple >/dev/null 2>&1; then
                    echo "✅ 간단한 헬스체크 성공 (IP: ${CONTAINER_IP})"
                    HEALTH_CHECK_SUCCESS=true
                else
                    echo "⚠️ 간단한 헬스체크 실패 - 상세 헬스체크 시도"
                    
                    if curl -f --max-time 10 http://${CONTAINER_IP}:8000/health >/dev/null 2>&1; then
                        echo "✅ 상세 헬스체크 성공 (IP: ${CONTAINER_IP})"
                        HEALTH_CHECK_SUCCESS=true
                    else
                        echo "⚠️ 상세 헬스체크도 실패 - 포트 연결 확인 시도"
                        
                        if nc -z ${CONTAINER_IP} 8000 2>/dev/null; then
                            echo "✅ 포트 연결 확인 성공 (IP: ${CONTAINER_IP})"
                            HEALTH_CHECK_SUCCESS=true
                        else
                            echo "❌ 모든 헬스체크 방법 실패"
                            echo "컨테이너 로그 (최근 20줄):"
                            docker logs maice-back --tail 20
                            echo "헬스체크 응답 확인:"
                            curl -v http://${CONTAINER_IP}:8000/health/simple 2>&1 | head -10
                        fi
                    fi
                fi
            else
                echo "❌ 컨테이너 IP를 찾을 수 없습니다"
                echo "컨테이너 상태 확인:"
                docker ps --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
                exit 1
            fi
            
            if [ "$HEALTH_CHECK_SUCCESS" = "true" ]; then
                echo "✅ 새 백엔드 컨테이너 헬스체크 성공"
                break
            fi
            
            RETRY_COUNT=$((RETRY_COUNT + 1))
            if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
                echo "2초 후 재시도..."
                sleep 2
            fi
        done
        
        if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
            echo "❌ 새 백엔드 컨테이너 헬스체크 최종 실패"
            echo "컨테이너 상세 로그:"
            docker logs maice-back --tail 50
            echo "컨테이너 상태:"
            docker inspect maice-back --format "{{.State.Status}} - {{.State.ExitCode}}"
            echo "새 컨테이너 정리 중..."
            docker stop maice-back || true
            docker rm maice-back || true
            exit 1
        fi
        
        # 배포 완료 - 새 백엔드가 성공적으로 실행됨
        echo "✅ 새 백엔드 배포 완료"
        
        # 잠시 대기
        echo "배포 완료 대기 중..."
        sleep 5
        
        echo "🏗️ 백엔드 배포 완료!"
        ;;
        
    "agent")
        echo "🤖 에이전트 배포 시작..."
        
        # 에이전트는 단순 교체 (무중단 배포 불필요)
        echo "기존 에이전트 컨테이너 정리 중..."
        docker stop maice-agent || true
        docker rm maice-agent || true
        
        echo "새 에이전트 컨테이너 실행 중..."
        echo "필수 환경 변수 확인 (마스킹):"
        echo "OPENAI_API_KEY 길이: ${#OPENAI_API_KEY}"
        
        echo "데이터베이스 연결 정보 확인:"
        echo "AGENT_DATABASE_URL: ${AGENT_DATABASE_URL}"

        docker run -d --name maice-agent --network maicesystem_maice_network \
            -e AGENT_DATABASE_URL="${AGENT_DATABASE_URL}" \
            -e REDIS_URL=redis://redis:6379 \
            -e OPENAI_API_KEY="${OPENAI_API_KEY}" \
            -e ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY}" \
            -e GEMINI_API_KEY="${GEMINI_KEY}" \
            -e MCP_SERVER_URL="${MCP_URL}" \
            -e LLM_PROVIDER=mcp \
            -e OPENAI_CHAT_MODEL=gpt-5-mini \
            -e ANTHROPIC_CHAT_MODEL=claude-sonnet-4-20250514 \
            -e GOOGLE_CHAT_MODEL=gemini-2.5-flash-lite \
            -e MCP_MODEL=penGPT \
            -e ORCHESTRATOR_MODE=decentralized \
            -e FORCE_NON_STREAMING=1 \
            -e AUTO_PROMOTE_AFTER_CLARIFICATION=0 \
            -e PYTHONUNBUFFERED=1 \
            ${AGENT_IMAGE}:${BUILD_NUMBER}
        
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
        
        echo "🤖 에이전트 배포 완료!"
        ;;
        
    *)
        echo "❌ 잘못된 배포 대상: ${DEPLOY_TARGET}"
        echo "사용법: $0 [backend|agent]"
        exit 1
        ;;
esac

# 최종 상태 확인
echo "🔍 최종 컨테이너 상태 확인..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

echo "✅ ${DEPLOY_TARGET} 배포 완료!"
