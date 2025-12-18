#!/bin/bash
# Blue-Green 배포 롤백 스크립트
# 배포 실패 또는 문제 발생 시 이전 환경으로 즉시 롤백

set -e  # 오류 발생 시 스크립트 종료

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

log_error "========================================"
log_error "Blue-Green 배포 롤백 시작"
log_error "========================================"

# 현재 활성 환경 확인 (개선된 로직)
get_active_environment() {
    # 1. Nginx 설정 파일에서 확인 (우선순위 1)
    local nginx_conf="/opt/KB-Web/workspace/MAICE/nginx/conf.d/maice-prod.conf"
    if [ -f "$nginx_conf" ]; then
        local active=$(grep "server maice-back-" "$nginx_conf" | grep -v "#" | grep -o "maice-back-[a-z]*" | head -1 | sed 's/maice-back-//')
        if [ -n "$active" ]; then
            log_info "Nginx 설정 파일에서 활성 환경 확인: $active"
            echo "$active"
            return 0
        fi
    fi
    
    # 2. Nginx 컨테이너에서 확인 (우선순위 2)
    local nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    if [ -n "$nginx_container" ]; then
        local active=$(docker exec ${nginx_container} cat /etc/nginx/conf.d/default.conf 2>/dev/null | \
                       grep -A 3 "upstream maice_backend" | \
                       grep "maice-back-" | \
                       grep -v "backup" | \
                       grep -o "maice-back-[a-z]*" | \
                       sed 's/maice-back-//' | \
                       head -1)
        if [ -n "$active" ]; then
            log_info "Nginx 컨테이너에서 활성 환경 확인: $active"
            echo "$active"
            return 0
        fi
    fi
    
    # 3. 실행 중인 컨테이너로 확인 (우선순위 3)
    local blue_running=$(docker ps --filter "name=maice-back-blue" --format "{{.Names}}" 2>/dev/null)
    local green_running=$(docker ps --filter "name=maice-back-green" --format "{{.Names}}" 2>/dev/null)
    
    if [ -n "$blue_running" ] && [ -z "$green_running" ]; then
        log_info "실행 중인 컨테이너로 활성 환경 확인: blue"
        echo "blue"
        return 0
    elif [ -n "$green_running" ] && [ -z "$blue_running" ]; then
        log_info "실행 중인 컨테이너로 활성 환경 확인: green"
        echo "green"
        return 0
    fi
    
    log_error "활성 환경을 확인할 수 없습니다"
    return 1
}

CURRENT_ENV=$(get_active_environment)

if [ -z "$CURRENT_ENV" ]; then
    log_error "활성 환경을 확인할 수 없어 롤백할 수 없습니다"
    exit 1
fi

log_info "현재 활성 환경: ${CURRENT_ENV}"

# 롤백 대상 환경 결정
if [ "${CURRENT_ENV}" = "blue" ]; then
    ROLLBACK_ENV="green"
else
    ROLLBACK_ENV="blue"
fi

log_info "롤백 대상 환경: ${ROLLBACK_ENV}"

# 롤백 대상 컨테이너 이름
ROLLBACK_CONTAINER="maice-back-${ROLLBACK_ENV}"
CURRENT_CONTAINER="maice-back-${CURRENT_ENV}"

# 롤백 대상 환경 컨테이너가 실행 중인지 확인
if ! docker ps --format "{{.Names}}" | grep -q "${ROLLBACK_CONTAINER}"; then
    log_error "롤백 대상 환경(${ROLLBACK_CONTAINER})이 실행되지 않고 있습니다"
    log_error "이전 버전의 컨테이너를 찾을 수 없습니다"
    
    # 중지된 컨테이너 확인
    if docker ps -a --format "{{.Names}}" | grep -q "${ROLLBACK_CONTAINER}"; then
        log_warning "중지된 ${ROLLBACK_CONTAINER} 발견, 재시작 시도..."
        docker start ${ROLLBACK_CONTAINER} 2>&1 || {
            log_error "컨테이너 시작 실패"
            docker logs ${ROLLBACK_CONTAINER} --tail 50 2>&1 || log_error "로그 조회 실패"
            exit 1
        }
        sleep 5
        
        if docker ps --format "{{.Names}}" | grep -q "${ROLLBACK_CONTAINER}"; then
            log_success "${ROLLBACK_CONTAINER} 재시작 성공"
        else
            log_error "${ROLLBACK_CONTAINER} 재시작 실패"
            log_error "컨테이너 로그:"
            docker logs ${ROLLBACK_CONTAINER} --tail 50 2>&1 || log_error "로그 조회 실패"
            exit 1
        fi
    else
        log_error "롤백 대상 컨테이너가 존재하지 않습니다"
        log_error "=== 현재 상황 분석 ==="
        log_error "1. 실행 중인 백엔드 컨테이너:"
        docker ps --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}" 2>&1 || log_error "조회 실패"
        log_error "2. 모든 백엔드 컨테이너 (중지 포함):"
        docker ps -a --filter "name=maice-back" --format "table {{.Names}}\t{{.Status}}" 2>&1 || log_error "조회 실패"
        log_error ""
        log_error "💡 롤백이 불가능한 상황입니다. 다음 중 하나를 선택하세요:"
        log_error "   1. 수동으로 이전 버전 이미지 재배포"
        log_error "   2. 현재 활성 환경(${CURRENT_ENV})을 그대로 유지"
        log_error "   3. 새 버전을 다시 배포 (문제 수정 후)"
        exit 1
    fi
fi

# 롤백 대상 환경 헬스체크
log_info "롤백 대상 환경 헬스체크 중..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if docker exec ${ROLLBACK_CONTAINER} curl -f --max-time 5 http://localhost:8000/health/simple >/dev/null 2>&1; then
        log_success "롤백 대상 환경 헬스체크 성공"
        break
    fi
    
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
        log_warning "헬스체크 실패, 재시도 중... ($((RETRY_COUNT))/${MAX_RETRIES})"
        sleep 2
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    log_error "롤백 대상 환경 헬스체크 최종 실패"
    log_error "롤백 대상 컨테이너 로그:"
    docker logs ${ROLLBACK_CONTAINER} --tail 30
    log_error "수동 복구가 필요합니다"
    exit 1
fi

# Nginx upstream 설정 롤백
log_info "Nginx upstream 설정 롤백 중..."

# Nginx 컨테이너 찾기
NGINX_CONTAINER=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)

if [ -z "$NGINX_CONTAINER" ]; then
    log_error "Nginx 컨테이너를 찾을 수 없습니다"
    exit 1
fi

# 롤백용 upstream 설정 생성
cat > /tmp/nginx_upstream_rollback.conf << EOF
# 프로덕션 전용 nginx 설정 - Blue-Green 무중단 배포 지원

# 백엔드 upstream 설정 (Blue-Green) - 롤백됨
upstream maice_backend {
    # ${ROLLBACK_ENV^} 환경 (롤백된 환경 - 활성)
    server maice-back-${ROLLBACK_ENV}:8000 max_fails=3 fail_timeout=30s;
    
    # ${CURRENT_ENV^} 환경 (문제가 있는 환경 - 백업)
    server maice-back-${CURRENT_ENV}:8000 max_fails=3 fail_timeout=30s backup;
    
    # 연결 재사용
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;
    
    # Health check 엔드포인트 (로드밸런서 직접 접근)
    location /health {
        proxy_pass http://maice_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # 헬스체크 타임아웃 설정
        proxy_connect_timeout 5s;
        proxy_send_timeout 5s;
        proxy_read_timeout 5s;
    }
    
    # 정적 파일 직접 서빙 - SPA 프론트엔드 (프로덕션)
    location / {
        root /usr/share/nginx/html;
        index index.html;
        
        # SPA 라우팅을 위한 fallback
        try_files \$uri \$uri/ /index.html;
        
        # 정적 파일 캐싱 설정
        expires 1h;
        add_header Cache-Control "public, immutable";
    }
    
    # 백엔드 API
    location /api/ {
        proxy_pass http://maice_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # SSE 스트리밍을 위한 필수 설정
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        
        # SSE 버퍼링 비활성화
        proxy_buffering off;
        proxy_cache off;
        
        # SSE 타임아웃 설정 (길게)
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 300s;
    }
    
    # 로그인 API (Rate limiting 강화)
    location /api/auth/login {
        proxy_pass http://maice_backend;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
    
    # 파일 업로드 (크기 제한)
    client_max_body_size 10M;
    
    # 에러 페이지
    error_page 404 /404.html;
    error_page 500 502 503 504 /50x.html;
}
EOF

# Nginx 컨테이너에 롤백 설정 복사
docker cp /tmp/nginx_upstream_rollback.conf ${NGINX_CONTAINER}:/etc/nginx/conf.d/default.conf

# 설정 파일 문법 검증
log_info "Nginx 설정 파일 문법 검증 중..."
if docker exec ${NGINX_CONTAINER} nginx -t 2>&1 | grep -q "successful"; then
    log_success "Nginx 설정 파일 문법 검증 성공"
else
    log_error "Nginx 설정 파일 문법 검증 실패"
    docker exec ${NGINX_CONTAINER} nginx -t
    exit 1
fi

# Nginx graceful reload (무중단 롤백)
log_info "Nginx 무중단 reload 실행 중..."
if docker exec ${NGINX_CONTAINER} nginx -s reload 2>&1 | tee /tmp/nginx-reload.log; then
    log_success "✅ Nginx 설정 다시 로드 완료"
else
    log_warning "⚠️ Nginx reload 실패, 컨테이너 재시작 시도..."
    if docker restart ${NGINX_CONTAINER} 2>&1 | tee /tmp/nginx-restart.log; then
        log_success "✅ Nginx 컨테이너 재시작 완료"
        sleep 3  # 재시작 후 안정화 대기
    else
        log_error "❌ Nginx 컨테이너 재시작 실패"
        exit 1
    fi
fi

log_success "Nginx upstream 롤백 완료: ${CURRENT_ENV} → ${ROLLBACK_ENV}"

# 롤백 후 헬스체크
log_info "롤백 후 최종 헬스체크 중..."
sleep 2

if docker exec ${NGINX_CONTAINER} wget -q -O - http://localhost/health >/dev/null 2>&1; then
    log_success "롤백 후 헬스체크 성공"
else
    log_warning "롤백 후 헬스체크 실패 - 추가 확인 필요"
fi

# 롤백 완료
log_success "========================================"
log_success "롤백 완료!"
log_success "========================================"
log_success "현재 활성 환경: ${ROLLBACK_ENV}"
log_success "비활성 환경: ${CURRENT_ENV}"
log_success "활성 컨테이너: ${ROLLBACK_CONTAINER}"
log_success "========================================"

# 문제가 있는 환경 정리 여부 확인
log_warning "문제가 있는 ${CURRENT_ENV} 환경을 정리하시겠습니까?"
log_warning "수동으로 정리하려면: docker stop ${CURRENT_CONTAINER} && docker rm ${CURRENT_CONTAINER}"

# 최종 상태 확인
log_info "최종 컨테이너 상태:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=maice-back"

exit 0

