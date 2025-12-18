#!/bin/bash
# 프론트엔드 배포 상태 진단 스크립트
# Blue-Green 배포가 제대로 작동하고 있는지 확인

set -e

echo "========================================"
echo "🔍 프론트엔드 배포 상태 진단"
echo "========================================"

BLUE_DIR="/opt/KB-Web/workspace/MAICE/front/dist-blue"
GREEN_DIR="/opt/KB-Web/workspace/MAICE/front/dist-green"
CURRENT_DIR="/opt/KB-Web/workspace/MAICE/front/dist"

echo ""
echo "1️⃣ 디렉토리 구조 확인"
echo "----------------------------------------"
echo "Blue 디렉토리:"
if [ -d "$BLUE_DIR" ]; then
    echo "✅ 존재함"
    echo "  파일 개수: $(find $BLUE_DIR -type f 2>/dev/null | wc -l)"
    echo "  마지막 수정: $(stat -f "%Sm" $BLUE_DIR 2>/dev/null || stat -c "%y" $BLUE_DIR 2>/dev/null)"
    echo "  index.html: $([ -f "$BLUE_DIR/index.html" ] && echo "✅" || echo "❌")"
else
    echo "❌ 없음"
fi

echo ""
echo "Green 디렉토리:"
if [ -d "$GREEN_DIR" ]; then
    echo "✅ 존재함"
    echo "  파일 개수: $(find $GREEN_DIR -type f 2>/dev/null | wc -l)"
    echo "  마지막 수정: $(stat -f "%Sm" $GREEN_DIR 2>/dev/null || stat -c "%y" $GREEN_DIR 2>/dev/null)"
    echo "  index.html: $([ -f "$GREEN_DIR/index.html" ] && echo "✅" || echo "❌")"
else
    echo "❌ 없음"
fi

echo ""
echo "2️⃣ 현재 활성 버전 확인"
echo "----------------------------------------"
if [ -L "$CURRENT_DIR" ]; then
    LINK_TARGET=$(readlink "$CURRENT_DIR")
    echo "✅ 심볼릭 링크 존재"
    echo "  링크: $CURRENT_DIR -> $LINK_TARGET"
    
    if [[ "$LINK_TARGET" == *"blue"* ]]; then
        echo "  현재 활성: 🔵 BLUE"
    elif [[ "$LINK_TARGET" == *"green"* ]]; then
        echo "  현재 활성: 🟢 GREEN"
    else
        echo "  ⚠️ 알 수 없는 링크: $LINK_TARGET"
    fi
else
    echo "❌ 심볼릭 링크 없음"
    if [ -d "$CURRENT_DIR" ]; then
        echo "  $CURRENT_DIR는 일반 디렉토리입니다"
    else
        echo "  $CURRENT_DIR가 존재하지 않습니다"
    fi
fi

echo ""
echo "3️⃣ Nginx 설정 확인"
echo "----------------------------------------"
NGINX_CONF="/opt/KB-Web/workspace/MAICE/nginx/conf.d/maice-prod.conf"
if [ -f "$NGINX_CONF" ]; then
    echo "✅ Nginx 설정 파일 존재"
    NGINX_ROOT=$(grep "root /var/www/html-" "$NGINX_CONF" | grep -v "#" | head -1 | sed 's/.*root \(\/var\/www\/html-[^;]*\);.*/\1/')
    echo "  Nginx root: $NGINX_ROOT"
    
    if [[ "$NGINX_ROOT" == *"blue"* ]]; then
        echo "  Nginx 설정: 🔵 BLUE"
    elif [[ "$NGINX_ROOT" == *"green"* ]]; then
        echo "  Nginx 설정: 🟢 GREEN"
    else
        echo "  ⚠️ 알 수 없는 설정: $NGINX_ROOT"
    fi
else
    echo "❌ Nginx 설정 파일 없음"
fi

echo ""
echo "4️⃣ Nginx 컨테이너 확인"
echo "----------------------------------------"
NGINX_CONTAINER=$(docker ps --filter "name=nginx" --format "{{.Names}}" | head -1)
if [ -n "$NGINX_CONTAINER" ]; then
    echo "✅ Nginx 컨테이너 실행 중: $NGINX_CONTAINER"
    
    # 컨테이너 내부 파일 확인
    echo ""
    echo "  Blue 디렉토리 (컨테이너 내부):"
    docker exec "$NGINX_CONTAINER" sh -c "ls -la /var/www/html-blue/ 2>/dev/null | head -5" || echo "  ❌ 접근 불가"
    
    echo ""
    echo "  Green 디렉토리 (컨테이너 내부):"
    docker exec "$NGINX_CONTAINER" sh -c "ls -la /var/www/html-green/ 2>/dev/null | head -5" || echo "  ❌ 접근 불가"
    
    # index.html 파일 해시 비교
    echo ""
    echo "  Blue index.html MD5:"
    docker exec "$NGINX_CONTAINER" sh -c "md5sum /var/www/html-blue/index.html 2>/dev/null" || echo "  ❌ 파일 없음"
    
    echo "  Green index.html MD5:"
    docker exec "$NGINX_CONTAINER" sh -c "md5sum /var/www/html-green/index.html 2>/dev/null" || echo "  ❌ 파일 없음"
else
    echo "❌ Nginx 컨테이너가 실행되고 있지 않습니다"
fi

echo ""
echo "5️⃣ Blue-Green 동기화 상태"
echo "----------------------------------------"
# 호스트와 컨테이너의 파일 동기화 확인
if [ -f "$BLUE_DIR/index.html" ] && [ -n "$NGINX_CONTAINER" ]; then
    HOST_BLUE_MD5=$(md5sum "$BLUE_DIR/index.html" 2>/dev/null | cut -d' ' -f1)
    CONTAINER_BLUE_MD5=$(docker exec "$NGINX_CONTAINER" sh -c "md5sum /var/www/html-blue/index.html 2>/dev/null | cut -d' ' -f1")
    
    echo "Blue 디렉토리:"
    echo "  호스트 MD5: $HOST_BLUE_MD5"
    echo "  컨테이너 MD5: $CONTAINER_BLUE_MD5"
    
    if [ "$HOST_BLUE_MD5" = "$CONTAINER_BLUE_MD5" ]; then
        echo "  ✅ 동기화됨"
    else
        echo "  ❌ 동기화 안 됨"
    fi
fi

if [ -f "$GREEN_DIR/index.html" ] && [ -n "$NGINX_CONTAINER" ]; then
    HOST_GREEN_MD5=$(md5sum "$GREEN_DIR/index.html" 2>/dev/null | cut -d' ' -f1)
    CONTAINER_GREEN_MD5=$(docker exec "$NGINX_CONTAINER" sh -c "md5sum /var/www/html-green/index.html 2>/dev/null | cut -d' ' -f1")
    
    echo ""
    echo "Green 디렉토리:"
    echo "  호스트 MD5: $HOST_GREEN_MD5"
    echo "  컨테이너 MD5: $CONTAINER_GREEN_MD5"
    
    if [ "$HOST_GREEN_MD5" = "$CONTAINER_GREEN_MD5" ]; then
        echo "  ✅ 동기화됨"
    else
        echo "  ❌ 동기화 안 됨"
    fi
fi

echo ""
echo "6️⃣ Nginx 캐시 헤더 확인"
echo "----------------------------------------"
if [ -f "$NGINX_CONF" ]; then
    echo "Cache-Control 설정:"
    grep -A5 "location /" "$NGINX_CONF" | grep -E "(expires|Cache-Control)" || echo "  캐시 설정 없음"
fi

echo ""
echo "7️⃣ 최근 Jenkins 빌드 정보"
echo "----------------------------------------"
if [ -f "/opt/KB-Web/workspace/MAICE/build-info.json" ]; then
    echo "최근 빌드 정보:"
    cat "/opt/KB-Web/workspace/MAICE/build-info.json" | grep -E "(build_number|git_commit|build_time)" || cat "/opt/KB-Web/workspace/MAICE/build-info.json"
else
    echo "❌ 빌드 정보 파일 없음"
fi

echo ""
echo "========================================"
echo "🔍 진단 완료"
echo "========================================"
echo ""
echo "💡 문제 해결 방법:"
echo "1. 심볼릭 링크와 Nginx 설정이 일치하지 않으면:"
echo "   → deploy_frontend.sh를 다시 실행하세요"
echo ""
echo "2. 호스트와 컨테이너의 파일이 동기화되지 않으면:"
echo "   → Nginx 컨테이너를 재시작하세요"
echo ""
echo "3. Blue와 Green의 파일이 동일하면:"
echo "   → 새로운 빌드가 배포되지 않았을 수 있습니다"
echo ""
echo "4. 브라우저에서 여전히 구버전이 보이면:"
echo "   → Ctrl+Shift+R (또는 Cmd+Shift+R)로 강제 새로고침"
echo "   → 또는 Nginx 설정의 immutable 캐시 헤더를 수정하세요"

