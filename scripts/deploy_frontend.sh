#!/bin/bash
# 프론트엔드 Blue-Green 배포 스크립트
# Jenkins 파이프라인에서 사용되는 프론트엔드 배포 로직

set -e  # 오류 발생 시 스크립트 종료

echo "🚀 프론트엔드 Blue-Green 배포 시작..."

# 빌드 번호 확인
if [ -z "$BUILD_NUMBER" ]; then
    echo "❌ BUILD_NUMBER가 설정되지 않았습니다"
    exit 1
fi

echo "빌드 번호: ${BUILD_NUMBER}"
echo "현재 시간: $(date)"
echo "배포 시작: 빌드 #${BUILD_NUMBER}"

# 빌드 결과 확인 (압축 해제 후 build/ 디렉토리 사용)
echo "빌드 결과 확인:"
echo "현재 작업 디렉토리: $(pwd)"
echo "현재 디렉토리 전체 내용:"
ls -la

echo "build/ 디렉토리 확인 (압축 해제된 결과):"
if [ -d "build" ]; then
    echo "✅ build/ 디렉토리 발견 (압축 해제된 빌드 결과)"
    ls -la build/
    BUILD_FILES=$(find build -type f | wc -l)
    echo "빌드 파일 개수: $BUILD_FILES"
    
    if [ $BUILD_FILES -gt 0 ]; then
        BUILD_SOURCE="build"
        echo "✅ build/ 디렉토리에 실제 파일들이 있습니다"
    else
        echo "⚠️ build/ 디렉토리는 있지만 파일이 없습니다"
        BUILD_SOURCE=""
    fi
else
    echo "❌ build/ 디렉토리 없음"
    BUILD_SOURCE=""
fi

# fallback: front/build/ 디렉토리 확인 (기존 방식)
if [ -z "$BUILD_SOURCE" ]; then
    echo "front/build/ 디렉토리 확인 (fallback):"
    if [ -d "front/build" ]; then
        echo "✅ front/build/ 디렉토리 발견 (기존 빌드 결과)"
        ls -la front/build/
        BUILD_FILES=$(find front/build -type f | wc -l)
        echo "빌드 파일 개수: $BUILD_FILES"
        
        if [ $BUILD_FILES -gt 0 ]; then
            BUILD_SOURCE="front/build"
            echo "✅ front/build/ 디렉토리에 실제 파일들이 있습니다"
        else
            echo "⚠️ front/build/ 디렉토리는 있지만 파일이 없습니다"
        fi
    else
        echo "❌ front/build/ 디렉토리도 없음"
    fi
fi

if [ -z "$BUILD_SOURCE" ]; then
    echo "❌ 빌드 결과 디렉토리를 찾을 수 없습니다"
    echo "현재 디렉토리 내용:"
    ls -la
    echo "❌ 배포할 빌드 결과가 없습니다"
    exit 1
fi

echo "✅ 사용할 빌드 소스: $BUILD_SOURCE"

# Blue-Green 배포 전략 적용
echo "🔄 Blue-Green 배포 전략 적용..."

# 1. 현재 실행 중인 Nginx 컨테이너 확인
echo "현재 실행 중인 컨테이너 확인..."
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# 여러 패턴으로 Nginx 컨테이너 찾기 (실행 중인 것 우선)
nginx_container=""
nginx_status=""

# 1단계: 실행 중인 Nginx 컨테이너 찾기
for pattern in "maicesystem_nginx" "nginx" "maice.*nginx"; do
    nginx_container=$(docker ps --filter "name=$pattern" --format "{{.Names}}" | head -1)
    if [ -n "$nginx_container" ]; then
        nginx_status="running"
        echo "✅ 실행 중인 Nginx 컨테이너 발견 (패턴: $pattern): $nginx_container"
        break
    fi
done

# 2단계: 중지된 Nginx 컨테이너 찾기
if [ -z "$nginx_container" ]; then
    echo "🔍 중지된 Nginx 컨테이너 확인 중..."
    for pattern in "maicesystem_nginx" "nginx" "maice.*nginx"; do
        nginx_container=$(docker ps -a --filter "name=$pattern" --format "{{.Names}}" | head -1)
        if [ -n "$nginx_container" ]; then
            nginx_status="stopped"
            echo "✅ 중지된 Nginx 컨테이너 발견 (패턴: $pattern): $nginx_container"
            break
        fi
    done
fi

# 3단계: Nginx 컨테이너 상태 확인 및 필요시 시작
if [ -n "$nginx_container" ]; then
    if [ "$nginx_status" = "running" ]; then
        echo "✅ Nginx 컨테이너가 실행 중입니다: $nginx_container"
    else
        echo "⚠️ Nginx 컨테이너가 중지되어 있습니다: $nginx_container"
        echo "🔄 docker-compose로 Nginx 시작 중..."
        cd /opt/KB-Web/workspace/MAICE
        docker-compose -f docker-compose.prod.yml up -d nginx
        sleep 3
        nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
        nginx_status="running"
        echo "✅ Nginx 컨테이너 시작 완료: $nginx_container"
    fi
else
    echo "⚠️ Nginx 컨테이너를 찾을 수 없습니다"
    echo "🔄 docker-compose로 Nginx 시작 중..."
    cd /opt/KB-Web/workspace/MAICE
    docker-compose -f docker-compose.prod.yml up -d nginx
    sleep 3
    nginx_container=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
    nginx_status="running"
    if [ -n "$nginx_container" ]; then
        echo "✅ Nginx 컨테이너 시작 완료: $nginx_container"
    else
        echo "❌ Nginx 컨테이너 시작 실패"
        exit 1
    fi
fi

echo "✅ Nginx 컨테이너 확인 완료: $nginx_container"

# 2. Blue-Green 디렉토리 준비
BLUE_DIR="/opt/KB-Web/workspace/MAICE/front/dist-blue"
GREEN_DIR="/opt/KB-Web/workspace/MAICE/front/dist-green"
CURRENT_DIR="/opt/KB-Web/workspace/MAICE/front/dist"

echo "Blue-Green 디렉토리 준비 중..."
echo "Blue 디렉토리: $BLUE_DIR"
echo "Green 디렉토리: $GREEN_DIR"
echo "현재 디렉토리: $CURRENT_DIR"

# 디렉토리 생성 (젠킨스 에이전트 권한으로)
echo "디렉토리 생성 시도 중..."
mkdir -p "$BLUE_DIR" "$GREEN_DIR" || {
    echo "❌ Blue-Green 디렉토리 생성 실패"
    echo "💡 젠킨스 에이전트에 적절한 권한이 있는지 확인하세요"
    echo "   다음 명령어로 수동으로 디렉토리를 생성하고 권한을 설정하세요:"
    echo "   sudo mkdir -p $BLUE_DIR $GREEN_DIR"
    echo "   sudo chown -R jenkins-agent:jenkins-agent /opt/KB-Web/workspace/MAICE/front/"
    echo "   또는 젠킨스 에이전트를 jenkins-agent 그룹에 추가하세요"
    exit 1
}
echo "✅ 디렉토리 생성 성공"

# 3. 현재 활성 버전 확인 (Blue 또는 Green) - 개선된 로직
CURRENT_VERSION=""
if [ -L "$CURRENT_DIR" ]; then
    LINK_TARGET=$(readlink "$CURRENT_DIR")
    if [[ "$LINK_TARGET" == *"blue"* ]]; then
        CURRENT_VERSION="blue"
        NEW_VERSION="green"
    else
        CURRENT_VERSION="green"
        NEW_VERSION="blue"
    fi
    echo "✅ 현재 활성 버전: $CURRENT_VERSION"
    echo "✅ 새 버전: $NEW_VERSION"
    echo "✅ 심볼릭 링크: $CURRENT_DIR -> $LINK_TARGET"
else
    # 심볼릭 링크가 없으면 기본적으로 blue로 설정
    CURRENT_VERSION="blue"
    NEW_VERSION="green"
    echo "✅ 심볼릭 링크 없음, 최초 배포로 간주"
    echo "✅ 기본 설정: Blue → Green"
fi

echo "🔄 Blue-Green 전환 계획:"
echo "  - 현재 활성: $CURRENT_VERSION"
echo "  - 새 배포: $NEW_VERSION"
echo "  - 빌드 번호: $BUILD_NUMBER"

# 4. 새 버전에 파일 복사 (개선된 로직)
NEW_DIR_VAR="${NEW_VERSION^^}_DIR"  # GREEN_DIR 또는 BLUE_DIR
NEW_DIR_PATH="${!NEW_DIR_VAR}"      # 변수 값 가져오기

echo "📁 새 버전 디렉토리에 파일 복사 중: $NEW_DIR_PATH"
echo "  - 소스: $BUILD_SOURCE"
echo "  - 대상: $NEW_DIR_PATH"
echo "  - 빌드 번호: $BUILD_NUMBER"

# 기존 파일 정리 (완전 삭제)
rm -rf "$NEW_DIR_PATH"/* 2>/dev/null || true
rm -rf "$NEW_DIR_PATH"/.* 2>/dev/null || true

# 빌드 소스 검증
if [ ! -d "$BUILD_SOURCE" ]; then
    echo "❌ 빌드 소스 디렉토리가 존재하지 않습니다: $BUILD_SOURCE"
    exit 1
fi

# 파일 복사 (상세 로깅)
echo "📋 복사할 파일 목록 (상위 10개):"
find "$BUILD_SOURCE" -type f | head -10

# 심볼릭 링크를 따라가며 실제 파일 복사 (broken link 문제 해결)
# -L 옵션: 심볼릭 링크를 실제 파일/디렉토리로 변환하여 복사
# broken link가 있으면 경고만 하고 계속 진행
echo "🔄 파일 복사 중..."
if cp -rL "$BUILD_SOURCE"/* "$NEW_DIR_PATH/" 2>&1 | grep -v "cannot stat"; then
    echo "✅ 파일 복사 완료"
else
    # 복사 실패 시에도 파일이 있는지 확인
    if [ ! -f "$NEW_DIR_PATH/index.html" ]; then
        echo "❌ 새 버전 디렉토리에 파일 복사 실패"
        echo "복사된 파일 확인:"
        ls -la "$NEW_DIR_PATH" || echo "디렉토리가 비어있습니다"
        exit 1
    else
        echo "⚠️ 일부 경고가 있었지만 주요 파일은 복사되었습니다"
    fi
fi

# 복사 결과 검증
COPIED_FILES=$(find "$NEW_DIR_PATH" -type f | wc -l)
echo "복사된 파일 개수: $COPIED_FILES"

# 권한 설정 (젠킨스 에이전트 권한으로)
chown -R jenkins-agent:jenkins-agent "$NEW_DIR_PATH" 2>/dev/null || true
chmod -R 755 "$NEW_DIR_PATH" 2>/dev/null || true

echo "✅ 새 버전 파일 복사 완료"
echo "  - 복사된 파일 수: $COPIED_FILES"
echo "  - 빌드 번호: $BUILD_NUMBER"

# 5. 배포 파일 검증 (전환 전 안전장치)
echo "🔍 배포 파일 검증 중..."

# 필수 파일들이 존재하는지 확인 (SvelteKit 구조에 맞게 수정)
required_files=("index.html" "_app")
for file in "${required_files[@]}"; do
    if [ ! -e "$NEW_DIR_PATH/$file" ]; then
        echo "❌ 필수 파일이 없습니다: $NEW_DIR_PATH/$file"
        echo "배포를 중단합니다."
        exit 1
    fi
done

echo "✅ 모든 필수 파일 검증 완료"

# 6. Blue-Green 전환 (Nginx 설정 변경)
echo "🔄 Blue-Green 전환 중 (무중단 배포)..."
echo "현재 활성 버전: $CURRENT_VERSION"
echo "새 버전으로 전환: $NEW_VERSION"

# Nginx 설정 파일 경로
NGINX_CONF="/opt/KB-Web/workspace/MAICE/nginx/conf.d/maice-prod.conf"

# Nginx 설정 파일에서 프론트엔드 root 경로 변경
echo "📝 Nginx 설정 파일 업데이트 중..."
if [ -f "$NGINX_CONF" ]; then
    # 현재 설정 확인
    CURRENT_ROOT=$(grep "root /var/www/html-" "$NGINX_CONF" | grep -v "#" | head -1 | sed 's/.*root \(\/var\/www\/html-[^;]*\);.*/\1/')
    echo "현재 Nginx root: $CURRENT_ROOT"
    
    # 새 버전으로 변경
    NEW_ROOT="/var/www/html-${NEW_VERSION}"
    sed -i "s|root /var/www/html-[a-z]*;|root $NEW_ROOT;|" "$NGINX_CONF"
    
    echo "✅ Nginx 설정 업데이트 완료: $NEW_ROOT"
    
    # 변경 확인
    UPDATED_ROOT=$(grep "root /var/www/html-" "$NGINX_CONF" | grep -v "#" | head -1 | sed 's/.*root \(\/var\/www\/html-[^;]*\);.*/\1/')
    echo "업데이트된 Nginx root: $UPDATED_ROOT"
else
    echo "❌ Nginx 설정 파일을 찾을 수 없습니다: $NGINX_CONF"
    exit 1
fi

# Nginx 설정 검증
if [ -n "$nginx_container" ] && [ "$nginx_status" = "running" ]; then
    echo "🔍 Nginx 설정 검증 중..."
    
    # DNS 해석을 위한 대기 시간 (새 컨테이너가 Docker DNS에 등록될 시간)
    echo "DNS 해석을 위한 대기 중 (5초)..."
    sleep 5
    
    # DNS 해석 테스트 (백엔드 컨테이너 확인)
    # 현재 활성화된 백엔드 컨테이너를 동적으로 확인
    echo "DNS 해석 테스트 중..."
    ACTIVE_BACKEND=""
    
    # Blue와 Green 중 실행 중인 컨테이너 찾기
    if docker ps --filter "name=maice-back-blue" --format "{{.Names}}" | grep -q "maice-back-blue"; then
        ACTIVE_BACKEND="maice-back-blue"
    elif docker ps --filter "name=maice-back-green" --format "{{.Names}}" | grep -q "maice-back-green"; then
        ACTIVE_BACKEND="maice-back-green"
    fi
    
    if [ -n "$ACTIVE_BACKEND" ]; then
        echo "🔍 활성 백엔드 컨테이너: $ACTIVE_BACKEND"
        if docker exec "$nginx_container" nslookup "$ACTIVE_BACKEND" 127.0.0.11 >/dev/null 2>&1; then
            echo "✅ DNS 해석 성공: $ACTIVE_BACKEND"
        else
            echo "⚠️ DNS 해석 실패: $ACTIVE_BACKEND, 추가 대기 중 (10초)..."
            sleep 10
        fi
    else
        echo "⚠️ 활성 백엔드 컨테이너를 찾을 수 없습니다. DNS 테스트 건너뜀"
    fi
    
    # 프론트엔드 배포는 nginx -t 검증 건너뛰기
    echo "ℹ️  프론트엔드 배포는 Nginx 설정 검증을 건너뜁니다"
    echo "   (백엔드 upstream 호스트가 없을 수 있기 때문)"
    echo "   Nginx reload는 Final Verification 단계에서 수행됩니다"
else
    echo "⚠️ Nginx 컨테이너가 실행 중이 아닙니다"
    echo "💡 Final Verification에서 Nginx가 시작됩니다"
fi

# 7. 심볼릭 링크 업데이트 (Blue-Green 전환 완료)
echo "🔗 심볼릭 링크 업데이트 중..."
if [ -L "$CURRENT_DIR" ]; then
    rm "$CURRENT_DIR"
fi
ln -sf "dist-${NEW_VERSION}" "$CURRENT_DIR"
echo "✅ 심볼릭 링크 업데이트 완료: $CURRENT_DIR -> dist-${NEW_VERSION}"

# 8. 전환 후 최종 검증 (무중단 배포 안전장치)
echo "🔍 전환 후 최종 검증 중..."

# 새 버전 디렉토리의 파일 확인
if [ ! -e "$NEW_DIR_PATH/index.html" ]; then
    echo "❌ 새 버전 디렉토리의 index.html 접근 실패"
    echo "새 버전 디렉토리 상태:"
    ls -la "$NEW_DIR_PATH"
    exit 1
fi

echo "✅ 새 버전 파일 검증 완료"

# Nginx 컨테이너가 실행 중이라면 내부 파일도 확인
if [ -n "$nginx_container" ] && [ "$nginx_status" = "running" ]; then
    echo "Nginx 컨테이너 내부 파일 확인:"
    NEW_CONTAINER_PATH="/var/www/html-${NEW_VERSION}"
    docker exec "$nginx_container" sh -c "ls -la $NEW_CONTAINER_PATH/ | head -10" || {
        echo "⚠️ 컨테이너 내부 파일 확인 실패"
    }
fi

# 9. Nginx 설정 리로드 (Final Verification)
echo "🔄 Nginx 설정 리로드 중..."
if [ -n "$nginx_container" ] && [ "$nginx_status" = "running" ]; then
    if docker exec "$nginx_container" nginx -s reload; then
        echo "✅ Nginx 설정 리로드 완료"
    else
        echo "❌ Nginx 설정 리로드 실패 - 롤백 시도"
        # 롤백: 이전 버전으로 되돌리기
        sed -i "s|root /var/www/html-[a-z]*;|root /var/www/html-${CURRENT_VERSION};|" "$NGINX_CONF"
        rm "$CURRENT_DIR" && ln -sf "dist-${CURRENT_VERSION}" "$CURRENT_DIR"
        docker exec "$nginx_container" nginx -s reload || {
            echo "❌ 롤백도 실패했습니다. 수동 확인이 필요합니다."
            exit 1
        }
        echo "✅ 롤백 완료"
        exit 1
    fi
else
    echo "⚠️ Nginx 컨테이너가 실행 중이 아닙니다 - 리로드 건너뜀"
fi

echo "✅ 무중단 Blue-Green 전환 완료"

# 10. 이전 버전은 유지 (Blue-Green 배포 - 빠른 롤백을 위해)
echo "ℹ️  이전 버전($CURRENT_VERSION)은 롤백을 위해 보존됩니다"
echo "ℹ️  다음 배포 시 자동으로 덮어씌워집니다"

# 11. 배포 완료 확인
echo "========================================"
echo "✅ 프론트엔드 Blue-Green 전환 완료!"
echo "========================================"
echo "현재 활성 버전: $NEW_VERSION"
echo "활성 디렉토리: $NEW_DIR_PATH"
if [ -L "$CURRENT_DIR" ]; then
    echo "심볼릭 링크: $CURRENT_DIR -> $(readlink "$CURRENT_DIR")"
else
    echo "심볼릭 링크: 심볼릭 링크가 없습니다"
fi
echo "✅ Nginx 설정 리로드 완료"
echo "========================================"
