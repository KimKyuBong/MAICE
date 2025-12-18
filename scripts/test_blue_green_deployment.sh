#!/bin/bash
# Blue-Green 배포 로컬 테스트 스크립트
# 개발 환경에서 Blue-Green 배포를 시뮬레이션하여 테스트합니다

set -e

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

log_info "========================================"
log_info "Blue-Green 배포 테스트 시작"
log_info "========================================"

# 1. 환경 확인
log_info "Step 1: 환경 확인..."

# Docker 실행 확인
if ! docker info >/dev/null 2>&1; then
    log_error "Docker가 실행되지 않았습니다"
    exit 1
fi
log_success "Docker 실행 중"

# 네트워크 확인
if ! docker network ls | grep -q "maicesystem_maice_network"; then
    log_warning "네트워크 생성 중..."
    docker network create maicesystem_maice_network
fi
log_success "Docker 네트워크 확인 완료"

# 2. 테스트용 간단한 백엔드 이미지 빌드
log_info "Step 2: 테스트용 이미지 빌드..."

# 테스트용 Dockerfile 생성
cat > /tmp/test_backend.Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

# 간단한 Flask 앱 설치
RUN pip install flask

# 테스트용 앱 생성
RUN echo 'from flask import Flask, jsonify\n\
import os\n\
\n\
app = Flask(__name__)\n\
VERSION = os.environ.get("VERSION", "unknown")\n\
\n\
@app.route("/health/simple")\n\
def health():\n\
    return jsonify({"status": "healthy", "version": VERSION})\n\
\n\
@app.route("/health")\n\
def health_detailed():\n\
    return jsonify({\n\
        "status": "healthy",\n\
        "version": VERSION,\n\
        "service": "test-backend"\n\
    })\n\
\n\
if __name__ == "__main__":\n\
    app.run(host="0.0.0.0", port=8000)' > app.py

CMD ["python", "app.py"]
EOF

# v1.0 이미지 빌드
docker build -t test-maice-back:v1.0 -f /tmp/test_backend.Dockerfile /tmp >/dev/null 2>&1
log_success "v1.0 이미지 빌드 완료"

# v2.0 이미지 빌드
docker build -t test-maice-back:v2.0 -f /tmp/test_backend.Dockerfile /tmp >/dev/null 2>&1
log_success "v2.0 이미지 빌드 완료"

# 3. Blue 환경 시작 (v1.0)
log_info "Step 3: Blue 환경 시작 (v1.0)..."

docker stop maice-back-blue 2>/dev/null || true
docker rm maice-back-blue 2>/dev/null || true

docker run -d \
    --name maice-back-blue \
    --network maicesystem_maice_network \
    -e VERSION=v1.0 \
    test-maice-back:v1.0 >/dev/null

sleep 3

# Blue 헬스체크
if docker exec maice-back-blue curl -f http://localhost:8000/health/simple >/dev/null 2>&1; then
    log_success "Blue 환경 (v1.0) 실행 중"
else
    log_error "Blue 환경 헬스체크 실패"
    exit 1
fi

# 4. Nginx 테스트 설정 생성
log_info "Step 4: Nginx 테스트 설정 생성..."

cat > /tmp/nginx_test.conf << 'EOF'
upstream maice_backend {
    server maice-back-blue:8000 max_fails=3 fail_timeout=30s;
    server maice-back-green:8000 max_fails=3 fail_timeout=30s backup;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;
    
    location /health {
        proxy_pass http://maice_backend;
        proxy_set_header Host $host;
    }
    
    location /api/ {
        proxy_pass http://maice_backend;
        proxy_set_header Host $host;
    }
}
EOF

# Nginx 실행
docker stop test-nginx 2>/dev/null || true
docker rm test-nginx 2>/dev/null || true

docker run -d \
    --name test-nginx \
    --network maicesystem_maice_network \
    -p 18080:80 \
    -v /tmp/nginx_test.conf:/etc/nginx/conf.d/default.conf:ro \
    nginx:alpine >/dev/null

sleep 2
log_success "Nginx 테스트 서버 실행 중 (포트: 18080)"

# 5. Blue 환경 테스트
log_info "Step 5: Blue 환경 테스트..."

RESPONSE=$(curl -s http://localhost:18080/health)
VERSION=$(echo $RESPONSE | grep -o '"version":"[^"]*"' | cut -d'"' -f4)

if [ "$VERSION" = "v1.0" ]; then
    log_success "Blue 환경 응답 확인: $VERSION"
else
    log_error "Blue 환경 응답 오류: $VERSION"
    exit 1
fi

# 6. Green 환경 배포 (v2.0)
log_info "Step 6: Green 환경 배포 (v2.0) - Blue-Green 시작..."

docker stop maice-back-green 2>/dev/null || true
docker rm maice-back-green 2>/dev/null || true

docker run -d \
    --name maice-back-green \
    --network maicesystem_maice_network \
    -e VERSION=v2.0 \
    test-maice-back:v2.0 >/dev/null

sleep 3

# Green 헬스체크
if docker exec maice-back-green curl -f http://localhost:8000/health/simple >/dev/null 2>&1; then
    log_success "Green 환경 (v2.0) 실행 중"
else
    log_error "Green 환경 헬스체크 실패"
    exit 1
fi

# 7. Nginx 설정 전환 (Blue → Green)
log_info "Step 7: Nginx 설정 전환 (무중단)..."

cat > /tmp/nginx_test_green.conf << 'EOF'
upstream maice_backend {
    server maice-back-green:8000 max_fails=3 fail_timeout=30s;
    server maice-back-blue:8000 max_fails=3 fail_timeout=30s backup;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;
    
    location /health {
        proxy_pass http://maice_backend;
        proxy_set_header Host $host;
    }
    
    location /api/ {
        proxy_pass http://maice_backend;
        proxy_set_header Host $host;
    }
}
EOF

docker cp /tmp/nginx_test_green.conf test-nginx:/etc/nginx/conf.d/default.conf
docker exec test-nginx nginx -s reload >/dev/null 2>&1

sleep 2
log_success "Nginx 설정 전환 완료 (Blue → Green)"

# 8. Green 환경 테스트
log_info "Step 8: Green 환경 테스트..."

RESPONSE=$(curl -s http://localhost:18080/health)
VERSION=$(echo $RESPONSE | grep -o '"version":"[^"]*"' | cut -d'"' -f4)

if [ "$VERSION" = "v2.0" ]; then
    log_success "Green 환경 응답 확인: $VERSION"
else
    log_error "Green 환경 응답 오류: $VERSION"
    exit 1
fi

# 9. 롤백 테스트 (Green → Blue)
log_info "Step 9: 롤백 테스트 (Green → Blue)..."

docker cp /tmp/nginx_test.conf test-nginx:/etc/nginx/conf.d/default.conf
docker exec test-nginx nginx -s reload >/dev/null 2>&1

sleep 2

RESPONSE=$(curl -s http://localhost:18080/health)
VERSION=$(echo $RESPONSE | grep -o '"version":"[^"]*"' | cut -d'"' -f4)

if [ "$VERSION" = "v1.0" ]; then
    log_success "롤백 성공: $VERSION"
else
    log_error "롤백 실패: $VERSION"
    exit 1
fi

# 10. 정리
log_info "Step 10: 테스트 환경 정리..."

read -p "테스트 환경을 정리하시겠습니까? (y/n): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    docker stop test-nginx maice-back-blue maice-back-green 2>/dev/null || true
    docker rm test-nginx maice-back-blue maice-back-green 2>/dev/null || true
    docker rmi test-maice-back:v1.0 test-maice-back:v2.0 2>/dev/null || true
    rm -f /tmp/test_backend.Dockerfile /tmp/nginx_test.conf /tmp/nginx_test_green.conf
    log_success "테스트 환경 정리 완료"
else
    log_info "테스트 환경 유지"
    log_info "수동 정리: docker stop test-nginx maice-back-blue maice-back-green && docker rm test-nginx maice-back-blue maice-back-green"
fi

log_success "========================================"
log_success "Blue-Green 배포 테스트 성공!"
log_success "========================================"
log_success "테스트 결과:"
log_success "  ✅ Blue 환경 배포 성공"
log_success "  ✅ Green 환경 배포 성공"
log_success "  ✅ 무중단 전환 성공 (Blue → Green)"
log_success "  ✅ 롤백 성공 (Green → Blue)"
log_success "========================================"

exit 0

