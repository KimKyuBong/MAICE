#!/bin/bash

# 인프라 관리 스크립트
# nginx, redis 등의 인프라 서비스를 관리합니다

# set -e  # 에러 시 즉시 종료 비활성화 (더 세밀한 에러 처리)

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 도움말 출력
show_help() {
    cat << EOF
인프라 관리 스크립트

사용법:
    $0 [옵션] [서비스]

옵션:
    -h, --help          이 도움말 출력
    -s, --status        서비스 상태 확인
    -r, --restart       서비스 재시작
    -d, --down          서비스 중지
    -u, --up            서비스 시작
    -l, --logs          서비스 로그 확인
    -c, --config        설정 파일 확인/리로드

서비스:
    nginx               Nginx 웹서버
    redis               Redis 캐시 서버
    all                 모든 인프라 서비스

예시:
    $0 -s nginx          # nginx 상태 확인
    $0 -r redis          # redis 재시작
    $0 -u all            # 모든 인프라 서비스 시작
    $0 -d nginx          # nginx 중지
    $0 -l redis          # redis 로그 확인
    $0 -c nginx          # nginx 설정 확인

EOF
}

# Docker Compose 파일 확인
check_docker_compose() {
    if [ ! -f "docker-compose.prod.yml" ]; then
        log_error "docker-compose.prod.yml 파일을 찾을 수 없습니다"
        exit 1
    fi
}

# 서비스 상태 확인
check_service_status() {
    local service=$1
    
    log_info "$service 서비스 상태 확인 중..."
    
    if docker ps --filter "name=$service" --format "{{.Names}}" | grep -q "$service"; then
        local container_name=$(docker ps --filter "name=$service" --format "{{.Names}}" | head -1)
        local status=$(docker ps --filter "name=$service" --format "{{.Status}}" | head -1)
        log_success "$service 컨테이너가 실행 중입니다: $container_name ($status)"
        return 0
    else
        log_warning "$service 컨테이너가 실행되지 않습니다"
        return 1
    fi
}

# 서비스 시작
start_service() {
    local service=$1
    
    log_info "$service 서비스 시작 중..."
    
    if check_service_status "$service" >/dev/null 2>&1; then
        log_warning "$service 서비스가 이미 실행 중입니다"
        return 0
    fi
    
    docker compose -f docker-compose.prod.yml up -d "$service"
    
    # 시작 확인
    sleep 3
    if check_service_status "$service" >/dev/null 2>&1; then
        log_success "$service 서비스 시작 완료"
    else
        log_error "$service 서비스 시작 실패"
        return 1
    fi
}

# 서비스 중지
stop_service() {
    local service=$1
    
    log_info "$service 서비스 중지 중..."
    
    if ! check_service_status "$service" >/dev/null 2>&1; then
        log_warning "$service 서비스가 이미 중지되어 있습니다"
        return 0
    fi
    
    docker stop "$service" || true
    docker rm "$service" || true
    
    log_success "$service 서비스 중지 완료"
}

# 서비스 재시작 (Docker Compose down/up 사용)
restart_service() {
    local service=$1
    
    log_info "$service 서비스 재시작 중 (Docker Compose down/up)..."
    
    # Docker Compose로 서비스 중지 (컨테이너 제거 포함)
    log_info "$service 서비스 중지 중..."
    if docker compose -f docker-compose.prod.yml stop "$service"; then
        log_info "$service 서비스 중지 성공"
    else
        log_warning "$service 서비스 중지 실패 (이미 중지됨)"
    fi
    
    # Docker Compose로 서비스 제거
    log_info "$service 서비스 제거 중..."
    if docker compose -f docker-compose.prod.yml rm -f "$service"; then
        log_info "$service 서비스 제거 성공"
    else
        log_warning "$service 서비스 제거 실패 (이미 제거됨)"
    fi
    
    # Docker Compose로 새 컨테이너 생성
    log_info "$service 서비스 새 컨테이너 생성 중..."
    if docker compose -f docker-compose.prod.yml up -d "$service"; then
        log_info "Docker Compose 명령어 성공"
    else
        log_error "Docker Compose 명령어 실패"
        return 1
    fi
    
    # 시작 확인
    log_info "컨테이너 시작 대기 중..."
    sleep 5
    
    if check_service_status "$service" >/dev/null 2>&1; then
        log_success "$service 서비스 재시작 완료 (새 컨테이너 생성됨)"
    else
        log_error "$service 서비스 재시작 실패"
        log_info "Docker Compose 로그 확인:"
        docker compose -f docker-compose.prod.yml logs "$service" || true
        return 1
    fi
}

# 서비스 로그 확인
show_service_logs() {
    local service=$1
    local lines=${2:-50}
    
    log_info "$service 서비스 로그 확인 중 (최근 $lines 줄)..."
    
    if check_service_status "$service" >/dev/null 2>&1; then
        docker logs --tail "$lines" "$service"
    else
        log_error "$service 서비스가 실행되지 않습니다"
        return 1
    fi
}

# Nginx 설정 확인 및 리로드
nginx_config_check() {
    log_info "Nginx 설정 확인 중..."
    
    if ! check_service_status "nginx" >/dev/null 2>&1; then
        log_error "Nginx 서비스가 실행되지 않습니다"
        return 1
    fi
    
    local nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    
    # 설정 파일 문법 검사
    log_info "Nginx 설정 파일 문법 검사 중..."
    if docker exec "$nginx_container" nginx -t; then
        log_success "Nginx 설정 파일 문법이 올바릅니다"
        
        # 설정 리로드
        log_info "Nginx 설정 리로드 중..."
        if docker exec "$nginx_container" nginx -s reload; then
            log_success "Nginx 설정 리로드 완료"
        else
            log_error "Nginx 설정 리로드 실패"
            return 1
        fi
    else
        log_error "Nginx 설정 파일에 문법 오류가 있습니다"
        return 1
    fi
}

# Redis 상태 확인
redis_status_check() {
    log_info "Redis 상태 확인 중..."
    
    if ! check_service_status "redis" >/dev/null 2>&1; then
        log_error "Redis 서비스가 실행되지 않습니다"
        return 1
    fi
    
    local redis_container=$(docker ps --filter "name=redis" --format "{{.Names}}" | head -1)
    
    # Redis 연결 테스트
    if docker exec "$redis_container" redis-cli ping | grep -q "PONG"; then
        log_success "Redis 연결 성공"
        
        # Redis 정보 출력
        log_info "Redis 정보:"
        docker exec "$redis_container" redis-cli info server | grep -E "(redis_version|uptime_in_seconds|connected_clients)"
    else
        log_error "Redis 연결 실패"
        return 1
    fi
}

# 모든 인프라 서비스 관리
manage_all_services() {
    local action=$1
    
    log_info "모든 인프라 서비스에 대해 $action 작업 실행 중..."
    
    case $action in
        "start")
            start_service "redis"
            start_service "nginx"
            ;;
        "stop")
            stop_service "nginx"
            stop_service "redis"
            ;;
        "restart")
            restart_service "redis"
            restart_service "nginx"
            ;;
        "status")
            check_service_status "redis"
            check_service_status "nginx"
            ;;
        *)
            log_error "알 수 없는 작업: $action"
            return 1
            ;;
    esac
}

# 메인 로직
main() {
    local action=""
    local service=""
    local show_logs=false
    local config_check=false
    
    # 인수 파싱
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -s|--status)
                action="status"
                shift
                ;;
            -r|--restart)
                action="restart"
                shift
                ;;
            -d|--down)
                action="stop"
                shift
                ;;
            -u|--up)
                action="start"
                shift
                ;;
            -l|--logs)
                show_logs=true
                shift
                ;;
            -c|--config)
                config_check=true
                shift
                ;;
            nginx|redis|all)
                service="$1"
                shift
                ;;
            *)
                log_error "알 수 없는 옵션: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Docker Compose 파일 확인
    check_docker_compose
    
    # 로그 확인 요청
    if [ "$show_logs" = true ]; then
        if [ -z "$service" ]; then
            log_error "로그를 확인할 서비스를 지정해주세요"
            exit 1
        fi
        
        if [ "$service" = "all" ]; then
            show_service_logs "redis"
            echo ""
            show_service_logs "nginx"
        else
            show_service_logs "$service"
        fi
        exit 0
    fi
    
    # 설정 확인 요청
    if [ "$config_check" = true ]; then
        if [ "$service" = "nginx" ]; then
            nginx_config_check
        elif [ "$service" = "redis" ]; then
            redis_status_check
        else
            log_error "설정 확인은 nginx 또는 redis에 대해서만 가능합니다"
            exit 1
        fi
        exit 0
    fi
    
    # 작업 실행
    if [ -z "$action" ]; then
        log_error "작업을 지정해주세요 (-s, -r, -d, -u 중 하나)"
        show_help
        exit 1
    fi
    
    if [ -z "$service" ]; then
        log_error "서비스를 지정해주세요 (nginx, redis, all 중 하나)"
        show_help
        exit 1
    fi
    
    # 서비스별 작업 실행
    if [ "$service" = "all" ]; then
        manage_all_services "$action"
    else
        case $action in
            "status")
                check_service_status "$service"
                ;;
            "start")
                start_service "$service"
                ;;
            "stop")
                stop_service "$service"
                ;;
            "restart")
                restart_service "$service"
                ;;
            *)
                log_error "알 수 없는 작업: $action"
                exit 1
                ;;
        esac
    fi
    
    log_success "인프라 관리 작업 완료"
}

# 스크립트 실행
main "$@"
