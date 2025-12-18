#!/bin/bash
# 트래픽 제어 스크립트
# Blue-Green 배포 중 트래픽을 안전하게 제어

set -e

# 매개변수 처리
ACTION="${1:-status}"  # status, switch, drain
ENVIRONMENT="${2:-}"   # blue, green

echo "🚦 트래픽 제어 시작... (액션: ${ACTION}, 환경: ${ENVIRONMENT})"

# 현재 활성 환경 확인
get_active_environment() {
    if docker ps --format "{{.Names}}" | grep -q "maice-back-blue"; then
        echo "blue"
    elif docker ps --format "{{.Names}}" | grep -q "maice-back-green"; then
        echo "green"
    else
        echo "none"
    fi
}

# Nginx upstream 상태 확인
check_upstream_status() {
    local nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    
    if [ -z "$nginx_container" ]; then
        echo "❌ Nginx 컨테이너를 찾을 수 없습니다"
        return 1
    fi
    
    echo "Nginx upstream 상태 확인 중..."
    docker exec ${nginx_container} nginx -T 2>/dev/null | grep -A 10 "upstream maice_backend" || {
        echo "❌ upstream 설정을 찾을 수 없습니다"
        return 1
    }
    
    return 0
}

# 트래픽 전환
switch_traffic() {
    local target_env=$1
    local current_env=$(get_active_environment)
    
    if [ "$current_env" = "none" ]; then
        echo "❌ 활성 환경을 찾을 수 없습니다"
        return 1
    fi
    
    if [ "$target_env" = "$current_env" ]; then
        echo "ℹ️ 이미 ${target_env} 환경이 활성화되어 있습니다"
        return 0
    fi
    
    echo "트래픽 전환 중: ${current_env} → ${target_env}"
    
    # 대상 환경 헬스체크
    local target_container="maice-back-${target_env}"
    if ! docker exec ${target_container} curl -f --max-time 5 http://localhost:8000/health >/dev/null 2>&1; then
        echo "❌ 대상 환경 헬스체크 실패"
        return 1
    fi
    
    # Nginx upstream 설정 업데이트
    update_nginx_upstream() {
        local active_env=$1
        local backup_env=$2
        
        cat > /tmp/nginx_upstream_switch.conf << EOF
upstream maice_backend {
    # ${active_env} 환경 (활성)
    server maice-back-${active_env}:8000 max_fails=3 fail_timeout=30s;
    # ${backup_env} 환경 (백업)
    server maice-back-${backup_env}:8000 max_fails=3 fail_timeout=30s backup;
    
    keepalive 32;
}
EOF
        
        nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
        docker cp /tmp/nginx_upstream_switch.conf ${nginx_container}:/etc/nginx/conf.d/upstream.conf
        docker exec ${nginx_container} nginx -s reload
        rm -f /tmp/nginx_upstream_switch.conf
        
        echo "✅ 트래픽 전환 완료 (활성: ${active_env}, 백업: ${backup_env})"
    }
    
    update_nginx_upstream ${target_env} ${current_env}
    
    # 전환 후 검증
    sleep 5
    if check_upstream_status; then
        echo "✅ 트래픽 전환 검증 완료"
    else
        echo "❌ 트래픽 전환 검증 실패"
        return 1
    fi
}

# 트래픽 드레인 (점진적 트래픽 감소)
drain_traffic() {
    local target_env=$1
    
    echo "트래픽 드레인 시작: ${target_env}"
    
    # 1단계: 트래픽을 백업으로 설정
    local current_env=$(get_active_environment)
    if [ "$current_env" = "$target_env" ]; then
        if [ "$current_env" = "blue" ]; then
            switch_traffic "green"
        else
            switch_traffic "blue"
        fi
    fi
    
    # 2단계: 대상 환경을 점진적으로 비활성화
    cat > /tmp/nginx_upstream_drain.conf << EOF
upstream maice_backend {
    # 현재 활성 환경
    server maice-back-${current_env}:8000 max_fails=3 fail_timeout=30s;
    # 드레인 대상 환경 (가중치 감소)
    server maice-back-${target_env}:8000 max_fails=1 fail_timeout=10s weight=1;
    
    keepalive 32;
}
EOF
    
    nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    docker cp /tmp/nginx_upstream_drain.conf ${nginx_container}:/etc/nginx/conf.d/upstream.conf
    docker exec ${nginx_container} nginx -s reload
    rm -f /tmp/nginx_upstream_drain.conf
    
    echo "✅ 트래픽 드레인 완료"
}

# 상태 확인
show_status() {
    local current_env=$(get_active_environment)
    
    echo "=== 트래픽 제어 상태 ==="
    echo "현재 활성 환경: ${current_env}"
    
    if [ "$current_env" != "none" ]; then
        echo "활성 컨테이너 상태:"
        docker ps --filter "name=maice-back-${current_env}" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    fi
    
    echo ""
    echo "모든 백엔드 컨테이너 상태:"
    docker ps --filter "name=maice-back-" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    echo ""
    echo "Nginx upstream 설정:"
    check_upstream_status
}

# 메인 로직
main() {
    case "$ACTION" in
        "status")
            show_status
            ;;
        "switch")
            if [ -z "$ENVIRONMENT" ]; then
                echo "❌ 환경을 지정해주세요 (blue 또는 green)"
                exit 1
            fi
            switch_traffic "$ENVIRONMENT"
            ;;
        "drain")
            if [ -z "$ENVIRONMENT" ]; then
                echo "❌ 환경을 지정해주세요 (blue 또는 green)"
                exit 1
            fi
            drain_traffic "$ENVIRONMENT"
            ;;
        *)
            echo "❌ 잘못된 액션: ${ACTION}"
            echo "사용법: $0 [status|switch|drain] [blue|green]"
            exit 1
            ;;
    esac
}

# 스크립트 실행
main "$@"
