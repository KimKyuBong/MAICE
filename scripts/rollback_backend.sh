#!/bin/bash
# Blue-Green 배포 롤백 스크립트
# 배포 실패 시 이전 환경으로 자동 롤백

set -e  # 오류 발생 시 스크립트 종료

echo "🔄 Blue-Green 배포 롤백 시작..."

# 현재 활성 환경 확인
CURRENT_ENV=""
if docker ps --format "{{.Names}}" | grep -q "maice-back-blue"; then
    CURRENT_ENV="blue"
elif docker ps --format "{{.Names}}" | grep -q "maice-back-green"; then
    CURRENT_ENV="green"
else
    echo "❌ 활성 백엔드 컨테이너를 찾을 수 없습니다"
    exit 1
fi

# 롤백 대상 환경 결정
if [ "${CURRENT_ENV}" = "blue" ]; then
    ROLLBACK_ENV="green"
else
    ROLLBACK_ENV="blue"
fi

echo "현재 활성 환경: ${CURRENT_ENV}"
echo "롤백 대상 환경: ${ROLLBACK_ENV}"

# 롤백 대상 환경 컨테이너가 존재하는지 확인
if ! docker ps --format "{{.Names}}" | grep -q "maice-back-${ROLLBACK_ENV}"; then
    echo "❌ 롤백 대상 환경(maice-back-${ROLLBACK_ENV})이 실행되지 않고 있습니다"
    echo "이전 버전의 컨테이너를 찾을 수 없습니다"
    exit 1
fi

# 롤백 대상 환경 헬스체크
echo "롤백 대상 환경 헬스체크 중..."
if docker exec maice-back-${ROLLBACK_ENV} curl -f http://localhost:8000/health >/dev/null 2>&1; then
    echo "✅ 롤백 대상 환경 헬스체크 성공"
else
    echo "❌ 롤백 대상 환경 헬스체크 실패"
    echo "롤백 대상 컨테이너 로그 확인:"
    docker logs maice-back-${ROLLBACK_ENV} --tail 20
    exit 1
fi

# Nginx upstream 설정 롤백
echo "Nginx upstream 설정 롤백 중..."
update_nginx_upstream() {
    local active_env=$1
    local backup_env=$2
    
    # 임시 nginx 설정 파일 생성
    cat > /tmp/nginx_upstream_rollback.conf << EOF
upstream maice_backend {
    # ${active_env} 환경 (활성)
    server maice-back-${active_env}:8000 max_fails=3 fail_timeout=30s;
    # ${backup_env} 환경 (백업)
    server maice-back-${backup_env}:8000 max_fails=3 fail_timeout=30s backup;
    
    keepalive 32;
}
EOF
    
    # Nginx 컨테이너에 설정 파일 복사
    nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    if [ -n "$nginx_container" ]; then
        # Nginx 컨테이너 상태 확인
        if ! docker ps --filter "name=nginx" --format "{{.Status}}" | grep -q "Up"; then
            echo "⚠️ Nginx 컨테이너가 실행되지 않음 - 재시작 시도"
            docker restart ${nginx_container} || {
                echo "❌ Nginx 컨테이너 재시작 실패"
                exit 1
            }
            sleep 3  # 재시작 대기
        fi
        
        docker cp /tmp/nginx_upstream_rollback.conf ${nginx_container}:/etc/nginx/conf.d/upstream.conf
        docker exec ${nginx_container} nginx -s reload
        echo "✅ Nginx upstream 설정 롤백 완료 (활성: ${active_env}, 백업: ${backup_env})"
        rm -f /tmp/nginx_upstream_rollback.conf
    else
        echo "❌ Nginx 컨테이너를 찾을 수 없습니다"
        echo "🔄 Nginx 컨테이너 시작 시도 중..."
        
        # Nginx 컨테이너 시작 시도
        if docker compose -f docker-compose.prod.yml up -d nginx; then
            echo "✅ Nginx 컨테이너 시작 완료"
            sleep 5  # 컨테이너 시작 대기
            nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
            
            # 설정 파일 복사 및 리로드
            docker cp /tmp/nginx_upstream_rollback.conf ${nginx_container}:/etc/nginx/conf.d/upstream.conf
            docker exec ${nginx_container} nginx -s reload
            echo "✅ Nginx upstream 설정 롤백 완료 (활성: ${active_env}, 백업: ${backup_env})"
            rm -f /tmp/nginx_upstream_rollback.conf
        else
            echo "❌ Nginx 컨테이너 시작 실패"
            exit 1
        fi
    fi
}

# 롤백 환경을 활성화
update_nginx_upstream ${ROLLBACK_ENV} ${CURRENT_ENV}

# 잠시 대기 후 현재 환경 정리
echo "현재 환경 정리 대기 중..."
sleep 10

# 현재 환경 컨테이너 정리
echo "현재 ${CURRENT_ENV} 환경 컨테이너 정리 중..."
docker stop maice-back-${CURRENT_ENV} || true
docker rm maice-back-${CURRENT_ENV} || true

# 최종 상태 확인
echo "🔍 롤백 후 컨테이너 상태 확인..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 롤백 성공 확인
if docker ps --format "{{.Names}}" | grep -q "maice-back-${ROLLBACK_ENV}"; then
    echo "✅ 롤백 성공! 활성 환경: ${ROLLBACK_ENV}"
else
    echo "❌ 롤백 실패"
    exit 1
fi

echo "🔄 Blue-Green 배포 롤백 완료!"
