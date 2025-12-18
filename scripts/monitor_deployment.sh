#!/bin/bash
# 배포 상태 모니터링 스크립트
# 배포 후 서비스 상태를 모니터링하고 검증

set -e

echo "🔍 배포 상태 모니터링 시작..."

# 모니터링 설정
MAX_RETRIES=10
RETRY_INTERVAL=5
HEALTH_CHECK_TIMEOUT=10

# 현재 활성 백엔드 컨테이너 확인 (Blue-Green 지원)
get_active_backend() {
    echo "🔍 실행 중인 컨테이너 확인 중..." >&2
    docker ps --format "{{.Names}}" | grep -E "(maice|backend)" >&2 || echo "백엔드 관련 컨테이너 없음" >&2
    
    # Blue-Green 환경 확인 (우선)
    local blue_running=$(docker ps --filter "name=maice-back-blue" --format "{{.Names}}" 2>/dev/null)
    local green_running=$(docker ps --filter "name=maice-back-green" --format "{{.Names}}" 2>/dev/null)
    
    # 둘 다 실행 중이면 Nginx upstream 설정 확인
    if [ -n "$blue_running" ] && [ -n "$green_running" ]; then
        echo "✅ Blue-Green 환경 감지 (Blue, Green 모두 실행 중)" >&2
        local nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
        if [ -n "$nginx_container" ]; then
            # backup 키워드가 없는 서버가 활성 환경
            local active=$(docker exec ${nginx_container} cat /etc/nginx/conf.d/default.conf 2>/dev/null | \
                          grep -A 3 "upstream maice_backend" | \
                          grep "maice-back-" | \
                          grep -v "backup" | \
                          grep -o "maice-back-[a-z]*" | \
                          head -1 || echo "")
            if [ -n "$active" ]; then
                echo "✅ 활성 환경: ${active}" >&2
                echo "$active"
                return
            fi
        fi
        # 기본값: blue 우선
        echo "✅ Blue 환경 기본 선택" >&2
        echo "maice-back-blue"
    elif [ -n "$blue_running" ]; then
        echo "✅ Blue 환경 발견" >&2
        echo "maice-back-blue"
    elif [ -n "$green_running" ]; then
        echo "✅ Green 환경 발견" >&2
        echo "maice-back-green"
    # 레거시 단일 컨테이너 확인
    elif docker ps --format "{{.Names}}" | grep -q "^maice-back$"; then
        echo "✅ 레거시 단일 컨테이너 발견: maice-back" >&2
        echo "maice-back"
    else
        echo "❌ 백엔드 컨테이너를 찾을 수 없음" >&2
        echo "none"
    fi
}

# 헬스체크 수행 (호스트에서 컨테이너 IP로 직접 확인)
check_health() {
    local container_name=$1
    local max_retries=${2:-$MAX_RETRIES}
    
    echo "헬스체크 수행 중: ${container_name}"
    
    # 컨테이너 IP 확인
    local container_ip=$(docker inspect ${container_name} --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
    if [ -z "$container_ip" ]; then
        echo "❌ 컨테이너 IP를 찾을 수 없습니다: ${container_name}"
        return 1
    fi
    
    echo "컨테이너 IP: ${container_ip}"
    
    for i in $(seq 1 $max_retries); do
        # 간단한 헬스체크 우선 시도 (컨테이너 IP 사용)
        if curl -f --max-time 5 http://${container_ip}:8000/health/simple >/dev/null 2>&1; then
            echo "✅ 간단한 헬스체크 성공 (${i}/${max_retries})"
            return 0
        else
            echo "⚠️ 간단한 헬스체크 실패 (${i}/${max_retries}) - 상세 헬스체크 시도"
            
            # 상세 헬스체크 시도 (컨테이너 IP 사용)
            if curl -f --max-time ${HEALTH_CHECK_TIMEOUT} http://${container_ip}:8000/health >/dev/null 2>&1; then
                echo "✅ 상세 헬스체크 성공 (${i}/${max_retries})"
                return 0
            else
                echo "⚠️ 상세 헬스체크도 실패 (${i}/${max_retries})"
                if [ $i -lt $max_retries ]; then
                    sleep $RETRY_INTERVAL
                fi
            fi
        fi
    done
    
    echo "❌ 헬스체크 최종 실패"
    return 1
}

# API 엔드포인트 테스트
test_api_endpoints() {
    local container_name=$1
    
    echo "API 엔드포인트 테스트 중..."
    
    # 컨테이너 IP 확인
    local container_ip=$(docker inspect ${container_name} --format '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' 2>/dev/null)
    if [ -z "$container_ip" ]; then
        echo "❌ 컨테이너 IP를 찾을 수 없습니다: ${container_name}"
        return 1
    fi
    
    # 기본 헬스체크
    if ! curl -f --max-time 5 http://${container_ip}:8000/health/simple >/dev/null 2>&1; then
        echo "❌ 간단한 헬스체크 API 실패"
        return 1
    fi
    
    # 상세 헬스체크
    if ! curl -f --max-time 5 http://${container_ip}:8000/health >/dev/null 2>&1; then
        echo "❌ 상세 헬스체크 API 실패"
        return 1
    fi
    
    echo "✅ API 엔드포인트 테스트 성공"
    return 0
}

# 컨테이너 리소스 사용량 확인
check_container_resources() {
    local container_name=$1
    
    echo "컨테이너 리소스 사용량 확인 중..."
    
    # 메모리 사용량 확인
    local memory_usage=$(docker stats --no-stream --format "{{.MemUsage}}" ${container_name} | cut -d'/' -f1 | sed 's/[^0-9.]//g')
    local memory_limit=$(docker stats --no-stream --format "{{.MemUsage}}" ${container_name} | cut -d'/' -f2 | sed 's/[^0-9.]//g')
    
    if [ -n "$memory_usage" ] && [ -n "$memory_limit" ]; then
        local memory_percent=$(echo "scale=2; $memory_usage * 100 / $memory_limit" | bc)
        echo "메모리 사용률: ${memory_percent}%"
        
        if (( $(echo "$memory_percent > 90" | bc -l) )); then
            echo "⚠️ 메모리 사용률이 높습니다 (${memory_percent}%)"
        fi
    fi
    
    # CPU 사용량 확인
    local cpu_usage=$(docker stats --no-stream --format "{{.CPUPerc}}" ${container_name} | sed 's/%//')
    echo "CPU 사용률: ${cpu_usage}%"
    
    if (( $(echo "$cpu_usage > 80" | bc -l) )); then
        echo "⚠️ CPU 사용률이 높습니다 (${cpu_usage}%)"
    fi
}

# 로그 확인
check_logs() {
    local container_name=$1
    
    echo "최근 로그 확인 중..."
    
    # 최근 에러 로그 확인
    local error_count=$(docker logs ${container_name} --since 5m 2>&1 | grep -i "error\|exception\|failed" | wc -l)
    
    if [ $error_count -gt 0 ]; then
        echo "⚠️ 최근 5분간 ${error_count}개의 에러/예외가 발생했습니다"
        echo "최근 에러 로그:"
        docker logs ${container_name} --since 5m 2>&1 | grep -i "error\|exception\|failed" | tail -5
    else
        echo "✅ 최근 에러 로그 없음"
    fi
}

# 메인 모니터링 로직
main() {
    echo "🔍 전체 컨테이너 상태 확인..."
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    local active_backend=$(get_active_backend)
    echo "🔍 감지된 백엔드: ${active_backend}"
    
    if [ "$active_backend" = "none" ]; then
        echo "❌ 활성 백엔드 컨테이너를 찾을 수 없습니다"
        echo "💡 다음을 확인해주세요:"
        echo "   - docker compose ps"
        echo "   - docker ps | grep maice"
        exit 1
    fi
    
    local container_name="${active_backend}"
    echo "백엔드 컨테이너: ${container_name}"
    
    # 컨테이너 존재 확인
    if ! docker ps --format "{{.Names}}" | grep -q "${container_name}"; then
        echo "❌ 컨테이너 ${container_name}가 실행되지 않고 있습니다"
        exit 1
    fi
    
    # 헬스체크 수행
    if ! check_health ${container_name}; then
        echo "❌ 헬스체크 실패"
        exit 1
    fi
    
    # API 엔드포인트 테스트
    if ! test_api_endpoints ${container_name}; then
        echo "❌ API 엔드포인트 테스트 실패"
        exit 1
    fi
    
    # 리소스 사용량 확인
    check_container_resources ${container_name}
    
    # 로그 확인
    check_logs ${container_name}
    
    echo "✅ 배포 상태 모니터링 완료 - 모든 검증 통과"
}

# 스크립트 실행
main "$@"
