#!/bin/bash
# Blue-Green 무중단 배포 스크립트
# 백엔드 서비스의 완전한 무중단 배포를 구현합니다

set -e  # 오류 발생 시 스크립트 종료
set -o pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 매개변수 처리
DEPLOY_TARGET="${1:-backend}"  # backend, agent 중 하나

log_info "Blue-Green 무중단 배포 시작... (대상: ${DEPLOY_TARGET})"

# 필수 환경 변수 검증
log_info "필수 환경 변수 검증 중..."
REQUIRED_VARS=("REGISTRY_URL" "BUILD_NUMBER" "BACKEND_IMAGE" "DATABASE_URL" "OPENAI_API_KEY" "GOOGLE_CLIENT_ID" "GOOGLE_CLIENT_SECRET" "ADMIN_USERNAME" "ADMIN_PASSWORD" "SESSION_SECRET_KEY")

for var in "${REQUIRED_VARS[@]}"; do
    if [ -z "${!var}" ]; then
        log_error "${var}이(가) 설정되지 않았습니다"
        exit 1
    fi
done

log_success "모든 필수 환경 변수 확인 완료"

# 선택적 환경 변수 설정
ANTHROPIC_KEY=${ANTHROPIC_API_KEY:-""}
GOOGLE_KEY=${GOOGLE_API_KEY:-""}
GOOGLE_REDIRECT=${GOOGLE_REDIRECT_URI:-"https://maice.kbworks.xyz/auth/google/callback"}
MCP_URL=${MCP_SERVER_URL:-""}

# Registry에서 이미지 풀 (BUILD_NUMBER 우선, latest 태그는 사용하지 않음)
log_info "Docker Registry에서 이미지 풀 중..."
log_info "풀링할 이미지: ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}"

# 이미지 존재 여부 확인
if ! docker pull ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}; then
    log_error "이미지 풀 실패: ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER}"
    log_error "Registry에 해당 빌드 번호의 이미지가 존재하지 않습니다"
    exit 1
fi

# 로컬 이미지로 태깅 (BUILD_NUMBER만 사용, latest 태그는 사용하지 않음)
docker tag ${REGISTRY_URL}/${BACKEND_IMAGE}:${BUILD_NUMBER} ${BACKEND_IMAGE}:${BUILD_NUMBER}
log_success "이미지 풀 및 태깅 완료"
log_info "로컬 이미지: ${BACKEND_IMAGE}:${BUILD_NUMBER}"

# 네트워크 확인 및 생성
log_info "Docker 네트워크 확인 중..."
if ! docker network ls | grep -q "maicesystem_maice_network"; then
    log_warning "네트워크가 없음, 생성 중..."
    docker network create maicesystem_maice_network || {
        log_error "네트워크 생성 실패"
        exit 1
    }
    log_success "네트워크 생성 완료"
else
    log_success "네트워크 이미 존재함"
fi

# 기존 단일 컨테이너 마이그레이션 (maice-back → maice-back-blue)
log_info "기존 컨테이너 확인 및 마이그레이션 중..."
LEGACY_CONTAINER=$(docker ps --filter "name=^maice-back$" --format "{{.Names}}" 2>/dev/null | grep -x "maice-back" || true)

if [ -n "$LEGACY_CONTAINER" ]; then
    log_warning "기존 단일 컨테이너 발견: maice-back"
    log_warning "Blue-Green 배포 환경으로 마이그레이션 중..."
    
    # 컨테이너를 blue로 rename
    docker rename maice-back maice-back-blue 2>&1 || {
        log_error "컨테이너 이름 변경 실패"
        docker ps -a --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}"
        exit 1
    }
    
    log_success "컨테이너 마이그레이션 완료: maice-back → maice-back-blue"
    log_info "이제 maice-back-blue가 현재 활성 환경입니다"
    log_warning "⚠️  Nginx upstream 설정은 Final Verification 단계에서 업데이트됩니다"
else
    log_info "기존 단일 컨테이너 없음, Blue-Green 환경 확인 진행"
fi

# 현재 활성 환경 확인 (Blue 또는 Green) - 개선된 로직
get_active_environment() {
    # stdout/(stderr) 분리: 로그는 stderr로, 결과는 stdout으로 보냅니다
    {
        # Blue와 Green 컨테이너 실행 상태 확인
        local blue_running=$(docker ps --filter "name=maice-back-blue" --format "{{.Names}}" 2>/dev/null)
        local green_running=$(docker ps --filter "name=maice-back-green" --format "{{.Names}}" 2>/dev/null)
        local resolved=""

        log_info "컨테이너 실행 상태 확인:"
        log_info "  - Blue: ${blue_running:-없음}"
        log_info "  - Green: ${green_running:-없음}"
        log_info "현재 docker ps (요약):"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=maice-back" || true

        # 둘 다 실행 중이면 Nginx upstream 설정 확인
        if [ -n "$blue_running" ] && [ -n "$green_running" ]; then
            log_info "Blue와 Green 모두 실행 중, Nginx upstream 설정 확인..."
            local nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)

            # 우선순위 1: 호스트 Nginx 설정 파일 확인
            local nginx_conf="/opt/KB-Web/workspace/MAICE/nginx/conf.d/maice-prod.conf"
            if [ -f "$nginx_conf" ]; then
                log_info "호스트 Nginx conf 존재: $nginx_conf"
                log_info "호스트 Nginx conf 내 server 라인:"
                grep -n "server maice-back-" "$nginx_conf" | sed -e 's/^/    /' || true
                local active=$(grep "server maice-back-" "$nginx_conf" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 | sed 's/maice-back-//')
                if [ -n "$active" ]; then
                    log_info "✅ 호스트 Nginx 설정에서 활성 환경 확인: $active"
                    resolved="$active"
                fi
            fi

            # 우선순위 2: Nginx 컨테이너 내부 설정 확인 (bind mount 확인용)
            if [ -z "$resolved" ] && [ -n "$nginx_container" ]; then
                log_info "호스트 설정 확인 실패, Nginx 컨테이너 내부 설정 검사 (bind mount 확인용)..."
                local container_active=$(docker exec "$nginx_container" sh -lc 'grep "server maice-back-" /etc/nginx/conf.d/default.conf | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 | sed "s/maice-back-//"' 2>/dev/null || echo "")
                if [ -n "$container_active" ]; then
                    log_info "✅ Nginx 컨테이너 내부 설정에서 활성 환경 확인: $container_active"
                    resolved="$container_active"
                else
                    log_warning "Nginx 컨테이너 내부에서도 활성 환경 확인 실패"
                    docker exec "$nginx_container" sh -lc 'grep -n "server maice-back-" /etc/nginx/conf.d/default.conf | sed -e "s/^/    /"' || true
                fi
            fi

            if [ -z "$resolved" ]; then
                # 기본값: blue가 활성 (두 컨테이너 실행 중이나 upstream 확인 실패 시)
                log_warning "⚠️ Nginx 설정 확인 실패, 기본값 blue 사용 (새 환경은 green으로 배포)"
                resolved="blue"
            fi
        elif [ -n "$blue_running" ]; then
            log_info "Blue만 실행 중"
            resolved="blue"
        elif [ -n "$green_running" ]; then
            log_info "Green만 실행 중"
            resolved="green"
        else
            # 둘 다 없으면 blue를 기본으로 (최초 배포)
            log_info "실행 중인 컨테이너 없음, 최초 배포로 간주"
            resolved="blue"
        fi

        # 결과는 원래 stdout(fd 3)으로 출력
        echo "$resolved" >&3
    } 3>&1 1>&2
}

CURRENT_ENV=$(get_active_environment)

# 최초 배포 확인 (Blue와 Green 모두 없는 경우)
BLUE_EXISTS=$(docker ps -a --filter "name=maice-back-blue" --format "{{.Names}}" 2>/dev/null)
GREEN_EXISTS=$(docker ps -a --filter "name=maice-back-green" --format "{{.Names}}" 2>/dev/null)

if [ -z "$BLUE_EXISTS" ] && [ -z "$GREEN_EXISTS" ]; then
    log_warning "최초 배포 감지: Blue와 Green 모두 없음"
    CURRENT_ENV="none"
    NEW_ENV="blue"
    log_info "최초 배포 환경: ${NEW_ENV}"
else
    log_info "현재 활성 환경: ${CURRENT_ENV}"
    
    # 새 배포 환경 결정
    if [ "${CURRENT_ENV}" = "blue" ]; then
        NEW_ENV="green"
    else
        NEW_ENV="blue"
    fi
    
    log_info "새 배포 환경: ${NEW_ENV}"
fi

# 새 환경 컨테이너 이름
NEW_CONTAINER="maice-back-${NEW_ENV}"
OLD_CONTAINER="maice-back-${CURRENT_ENV}"

# 기존 새 환경 컨테이너 정리 (혹시 남아있을 경우)
log_info "기존 ${NEW_ENV} 환경 컨테이너 정리 중..."
docker stop ${NEW_CONTAINER} 2>/dev/null || true
docker rm ${NEW_CONTAINER} 2>/dev/null || true

# 새 환경에 백엔드 컨테이너 실행
log_info "새 ${NEW_ENV} 환경에 백엔드 컨테이너 실행 중..."
log_info "컨테이너 이름: ${NEW_CONTAINER}"
log_info "이미지: ${BACKEND_IMAGE}:${BUILD_NUMBER}"

CONTAINER_ID=$(docker run -d \
    --name ${NEW_CONTAINER} \
    --restart unless-stopped \
    --network maicesystem_maice_network \
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

log_success "컨테이너 실행 완료: ${CONTAINER_ID:0:12}"

# 컨테이너 실행 확인
sleep 3
if ! docker ps --filter "name=${NEW_CONTAINER}" --format "{{.Names}}" | grep -q "${NEW_CONTAINER}"; then
    log_error "컨테이너 실행 실패: ${NEW_CONTAINER}"
    log_error "컨테이너 로그:"
    docker logs ${NEW_CONTAINER} --tail 50
    exit 1
fi

log_success "컨테이너 실행 상태 확인 완료"

# 새 컨테이너 헬스체크 (최대 60초 대기)
log_info "새 ${NEW_ENV} 환경 헬스체크 중..."
MAX_RETRIES=30
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    log_info "헬스체크 시도 $((RETRY_COUNT + 1))/${MAX_RETRIES}..."
    
    # 컨테이너가 여전히 실행 중인지 확인
    if ! docker ps --filter "name=${NEW_CONTAINER}" --format "{{.Names}}" | grep -q "${NEW_CONTAINER}"; then
        log_error "컨테이너가 중지됨: ${NEW_CONTAINER}"
        log_error "컨테이너 로그 (최근 100줄):"
        docker logs ${NEW_CONTAINER} --tail 100 2>&1 || log_error "로그 조회 실패"
        log_error "컨테이너 상태:"
        docker inspect ${NEW_CONTAINER} --format '{{.State.Status}} - ExitCode: {{.State.ExitCode}}' 2>&1 || log_error "상태 조회 실패"
        log_info "실패한 컨테이너 정리 중..."
        docker stop ${NEW_CONTAINER} 2>/dev/null || true
        docker rm ${NEW_CONTAINER} 2>/dev/null || true
        exit 1
    fi
    
    # 헬스체크 실행 (호스트에서 직접)
    # 컨테이너 IP 가져오기
    CONTAINER_IP=$(docker inspect ${NEW_CONTAINER} --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
    
    if [ -n "$CONTAINER_IP" ] && curl -f --max-time 5 http://${CONTAINER_IP}:8000/health/simple >/dev/null 2>&1; then
        log_success "헬스체크 성공!"
        break
    else
        # 헬스체크 실패 원인 간단히 로깅 (매번은 아니고 5번마다)
        if [ $((RETRY_COUNT % 5)) -eq 0 ]; then
            log_warning "헬스체크 실패 (IP: ${CONTAINER_IP:-없음}), 최근 로그 확인:"
            docker logs ${NEW_CONTAINER} --tail 10 2>&1 || log_error "로그 조회 실패"
        fi
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "새 ${NEW_ENV} 환경 헬스체크 최종 실패 (${MAX_RETRIES}회 시도)"
    log_error "=== 상세 디버깅 정보 ==="
    
    # 컨테이너 상태 확인
    log_error "1. 컨테이너 상태:"
    docker ps -a --filter "name=${NEW_CONTAINER}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>&1 || log_error "상태 조회 실패"
    
    # 컨테이너 로그 (길게)
    log_error "2. 컨테이너 로그 (최근 100줄):"
    docker logs ${NEW_CONTAINER} --tail 100 2>&1 || log_error "로그 조회 실패"
    
    # 컨테이너 IP 확인
    log_error "3. 컨테이너 네트워크 정보:"
    CONTAINER_IP=$(docker inspect ${NEW_CONTAINER} --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
    log_error "   컨테이너 IP: ${CONTAINER_IP:-없음}"
    log_error "   네트워크: $(docker inspect ${NEW_CONTAINER} --format '{{range $k,$v := .NetworkSettings.Networks}}{{$k}}{{end}}' 2>/dev/null)"
    
    # 환경 변수 확인 (민감 정보 제외)
    log_error "4. 환경 변수 확인:"
    docker exec ${NEW_CONTAINER} env 2>/dev/null | grep -E "(DATABASE_URL|REDIS_URL|ENVIRONMENT)" 2>&1 || log_error "환경 변수 조회 실패"
    
    # 호스트에서 헬스체크 시도
    log_error "5. 호스트에서 헬스체크 시도:"
    if [ -n "$CONTAINER_IP" ]; then
        curl -v --max-time 5 http://${CONTAINER_IP}:8000/health/simple 2>&1 | head -20 || log_error "헬스체크 응답 없음"
    else
        log_error "컨테이너 IP 없음, 헬스체크 불가"
    fi
    
    log_error "=== 정리 시작 ==="
    log_info "새 컨테이너 정리 중..."
    docker stop ${NEW_CONTAINER} 2>/dev/null || true
    docker rm ${NEW_CONTAINER} 2>/dev/null || true
    exit 1
fi

# Nginx upstream 설정 업데이트 (개선된 로직)
log_info "🔄 Nginx upstream 설정 업데이트 중..."
NGINX_CONF="/opt/KB-Web/workspace/MAICE/nginx/conf.d/maice-prod.conf"

if [ -f "$NGINX_CONF" ]; then
    # 현재 upstream 확인
    log_info "변경 전 Nginx conf server 라인:"
    grep -n "server maice-back-" "$NGINX_CONF" | sed -e 's/^/    /' || true
    CURRENT_UPSTREAM=$(grep "server maice-back-" "$NGINX_CONF" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1)
    log_info "현재 Nginx upstream: $CURRENT_UPSTREAM"
    
    # 새 환경으로 변경
    NEW_UPSTREAM="maice-back-${NEW_ENV}"
    log_info "새 upstream으로 변경: $NEW_UPSTREAM"
    
    # 백업 생성
    cp "$NGINX_CONF" "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)"
    
    # upstream 변경 (더 정확한 패턴 매칭)
    # 참고: maice-prod.conf는 bind mount되어 컨테이너 내부 /etc/nginx/conf.d/default.conf로 마운트됨
    # Docker bind mount에서 파일 수정 후 reload가 즉시 반영되지 않을 수 있으므로:
    # 1. 파일 수정 후 sync로 강제 동기화
    # 2. nginx -T로 실제 로드된 설정 확인
    # 3. 그래도 안되면 컨테이너 재시작
    if sed -i "s|server maice-back-[a-z]*:8000|server $NEW_UPSTREAM:8000|" "$NGINX_CONF" 2>/dev/null; then
        log_success "호스트 Nginx 설정 파일 업데이트 성공"
        # 파일 시스템 버퍼 강제 동기화 (Docker bind mount 동기화 보장)
        sync
        log_info "파일 시스템 동기화 완료"
    elif sudo sed -i "s|server maice-back-[a-z]*:8000|server $NEW_UPSTREAM:8000|" "$NGINX_CONF" 2>/dev/null; then
        log_success "호스트 Nginx 설정 파일 업데이트 성공 (sudo 사용)"
        sync
        log_info "파일 시스템 동기화 완료"
    else
        log_error "❌ 호스트 Nginx 설정 파일 업데이트 실패"
        log_error "파일 경로: $NGINX_CONF"
        log_error "파일 권한 확인:"
        ls -la "$NGINX_CONF" 2>&1 || true
        log_error "sudo 권한이 필요할 수 있습니다"
        exit 1
    fi
    
    # 변경 확인 (호스트 파일 확인, bind mount이므로 컨테이너 내부도 동일)
    log_info "변경 후 Nginx conf server 라인:"
    grep -n "server maice-back-" "$NGINX_CONF" | sed -e 's/^/    /' || true
    
    UPDATED_UPSTREAM=$(grep "server maice-back-" "$NGINX_CONF" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1)
    if [ "$UPDATED_UPSTREAM" = "$NEW_UPSTREAM" ]; then
        log_success "✅ Nginx upstream 업데이트 완료: $NEW_UPSTREAM"
    else
        log_error "❌ Nginx upstream 업데이트 실패"
        log_error "예상: $NEW_UPSTREAM, 실제: ${UPDATED_UPSTREAM:-없음}"
        exit 1
    fi
    
    # Nginx 설정 검증
    NGINX_CONTAINER=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    if [ -n "$NGINX_CONTAINER" ]; then
        log_info "🔍 Nginx 설정 검증 중..."
        
        # DNS 해석을 위한 대기 시간 (새 컨테이너가 Docker DNS에 등록될 시간)
        log_info "DNS 해석을 위한 대기 중 (5초)..."
        sleep 5
        
        # DNS 해석 테스트
        log_info "DNS 해석 테스트 중..."
        if docker exec "$NGINX_CONTAINER" nslookup maice-back-${NEW_ENV} 127.0.0.11 >/dev/null 2>&1; then
            log_success "✅ DNS 해석 성공"
        else
            log_warning "⚠️ DNS 해석 실패, 추가 대기 중 (10초)..."
            sleep 10
        fi
        log_info "컨테이너 내부 default.conf server 라인 (검증용, bind mount이므로 호스트 파일과 동일):"
        docker exec "$NGINX_CONTAINER" sh -lc 'grep -n "server maice-back-" /etc/nginx/conf.d/default.conf | sed -e "s/^/    /"' || true
        
        if docker exec "$NGINX_CONTAINER" nginx -t 2>&1 | tee /tmp/nginx-test.log; then
            log_success "✅ Nginx 설정 검증 완료"
            
            # Nginx 설정 다시 로드
            log_info "Nginx 설정 다시 로드 중..."
            # Docker bind mount에서 파일 수정 후 reload가 즉시 반영되지 않는 이유:
            # 1. 파일 시스템 버퍼 캐시 지연
            # 2. Nginx가 이미 열어둔 파일 핸들 캐싱
            # 3. bind mount 동기화 타이밍 이슈
            # 해결: 파일 수정 직후 약간의 대기 시간을 두고 reload
            sleep 2  # 파일 시스템 동기화를 위한 대기
            
            # reload 결과 확인 (reload는 출력이 없으면 성공)
            if docker exec "$NGINX_CONTAINER" nginx -s reload 2>&1; then
                log_success "✅ Nginx reload 명령 실행 완료"
                
                # 실제 로드된 설정 확인 (nginx -T로 확인하는 것이 가장 정확함)
                sleep 2  # reload 후 설정이 완전히 로드되기까지 대기
                log_info "Reload 후 실제 로드된 설정 확인 중 (nginx -T 사용)..."
                loaded_upstream=$(docker exec "$NGINX_CONTAINER" nginx -T 2>&1 | grep -A 5 "upstream maice_backend" | grep "server maice-back-" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 2>/dev/null || echo "")
                
                if [ "$loaded_upstream" = "$NEW_UPSTREAM" ]; then
                    log_success "✅ Nginx 설정 reload 후 반영 확인 완료: $NEW_UPSTREAM (nginx -T 검증)"
                else
                    log_warning "⚠️ Reload 후 설정이 반영되지 않음 (예상: $NEW_UPSTREAM, 실제: ${loaded_upstream:-없음})"
                    log_warning "⚠️ Docker bind mount에서 reload가 제대로 동작하지 않는 경우이므로 컨테이너 재시작으로 강제 반영..."
                    if docker restart "$NGINX_CONTAINER" 2>&1; then
                        sleep 5  # 재시작 후 안정화 대기
                        log_success "✅ Nginx 컨테이너 재시작 완료"
                        
                        # 재시작 후 실제 로드된 설정 확인 (nginx -T)
                        restarted_upstream=$(docker exec "$NGINX_CONTAINER" nginx -T 2>&1 | grep -A 5 "upstream maice_backend" | grep "server maice-back-" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 2>/dev/null || echo "")
                        if [ "$restarted_upstream" = "$NEW_UPSTREAM" ]; then
                            log_success "✅ Nginx 재시작 후 설정 반영 확인 완료: $NEW_UPSTREAM (nginx -T 검증)"
                        else
                            log_error "❌ Nginx 재시작 후에도 설정이 반영되지 않음"
                            log_error "예상: $NEW_UPSTREAM, 실제: ${restarted_upstream:-없음}"
                            exit 1
                        fi
                    else
                        log_error "❌ Nginx 컨테이너 재시작 실패"
                        exit 1
                    fi
                fi
            else
                log_warning "⚠️ Nginx reload 실패, 컨테이너 재시작 시도..."
                if docker restart "$NGINX_CONTAINER" 2>&1; then
                    sleep 5  # 재시작 후 안정화 대기
                    log_success "✅ Nginx 컨테이너 재시작 완료"
                    
                    # 재시작 후 실제 로드된 설정 확인 (nginx -T)
                    restarted_upstream=$(docker exec "$NGINX_CONTAINER" nginx -T 2>&1 | grep -A 5 "upstream maice_backend" | grep "server maice-back-" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 2>/dev/null || echo "")
                    if [ "$restarted_upstream" = "$NEW_UPSTREAM" ]; then
                        log_success "✅ Nginx 재시작 후 설정 반영 확인 완료: $NEW_UPSTREAM (nginx -T 검증)"
                    else
                        log_error "❌ Nginx 재시작 후에도 설정이 반영되지 않음"
                        log_error "예상: $NEW_UPSTREAM, 실제: ${restarted_upstream:-없음}"
                        exit 1
                    fi
                else
                    log_error "❌ Nginx 컨테이너 재시작 실패"
                    exit 1
                fi
            fi
        else
            log_error "❌ Nginx 설정 오류 - 변경사항을 되돌립니다"
            # 백업에서 복원
            cp "${NGINX_CONF}.backup.$(date +%Y%m%d_%H%M%S)" "$NGINX_CONF"
            log_error "Nginx 설정을 이전 상태로 복원했습니다"
            exit 1
        fi
    else
        log_warning "⚠️ Nginx 컨테이너가 실행 중이 아닙니다"
        log_warning "Final Verification 단계에서 Nginx 설정이 적용됩니다"
    fi
else
    log_error "❌ Nginx 설정 파일을 찾을 수 없습니다: $NGINX_CONF"
    exit 1
fi

# 배포 완료
log_success "========================================"
log_success "새 ${NEW_ENV} 환경 배포 완료!"
log_success "========================================"
log_success "새 환경: ${NEW_ENV} (${NEW_CONTAINER})"
log_success "기존 환경: ${CURRENT_ENV} (${OLD_CONTAINER})"
log_success "Nginx upstream: maice-back-${NEW_ENV}"
log_success "✅ Nginx 설정이 이미 적용되었습니다"
log_success "========================================"

# 최종 상태 확인
log_info "최종 컨테이너 상태:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=maice-back"

exit 0
