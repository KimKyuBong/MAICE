#!/bin/bash
# 프론트엔드 빌드 스크립트
# Jenkins 파이프라인에서 사용되는 프론트엔드 빌드 로직

set -e  # 오류 발생 시 스크립트 종료

echo "🎨 프론트엔드 빌드 시작..."

# 환경변수 검증
if [ -z "$GOOGLE_CLIENT_ID" ]; then
    echo "❌ GOOGLE_CLIENT_ID가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$GOOGLE_REDIRECT_URI" ]; then
    echo "❌ GOOGLE_REDIRECT_URI가 설정되지 않았습니다"
    exit 1
fi

echo "프론트엔드 환경변수 설정 확인..."
echo "GOOGLE_CLIENT_ID 길이: ${#GOOGLE_CLIENT_ID}"
echo "GOOGLE_REDIRECT_URI: ${GOOGLE_REDIRECT_URI}"

echo "로컬 환경에서 프론트엔드 빌드..."

# front 디렉토리로 이동
cd front

# 환경변수 설정
export VITE_GOOGLE_CLIENT_ID="${GOOGLE_CLIENT_ID}"
export VITE_GOOGLE_REDIRECT_URI="${GOOGLE_REDIRECT_URI}"
export VITE_API_BASE_URL=""  # 빈 문자열로 설정하여 상대 경로 사용 (nginx 프록시)
export VITE_ENVIRONMENT="production"

echo "환경변수 확인..."
echo "VITE_GOOGLE_CLIENT_ID 길이: ${#VITE_GOOGLE_CLIENT_ID}"
echo "VITE_GOOGLE_REDIRECT_URI: ${VITE_GOOGLE_REDIRECT_URI}"
echo "VITE_API_BASE_URL: ${VITE_API_BASE_URL}"
echo "VITE_ENVIRONMENT: ${VITE_ENVIRONMENT}"

# Node.js 및 yarn 버전 확인 및 업그레이드
echo "Node.js 및 yarn 버전 확인..."
node --version
npm --version

# Node.js 버전이 22 미만이면 업그레이드
NODE_VERSION=$(node --version | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 22 ]; then
    echo "Node.js 버전이 22 미만입니다. Node.js 22로 업그레이드 중..."
    
    # NodeSource 저장소 추가 및 Node.js 22 설치
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo -E bash -
    sudo apt-get install -y nodejs
    
    echo "업그레이드 후 Node.js 버전:"
    node --version
    npm --version
fi

yarn --version || {
    echo "yarn이 설치되지 않음, npm으로 설치..."
    npm install -g yarn
    yarn --version
}

# 의존성 설치
echo "의존성 설치..."
yarn install --frozen-lockfile || {
    echo "❌ yarn install 실패!"
    echo "❌ 프론트엔드 의존성 설치에 실패했습니다"
    exit 1
}

# 빌드 전 기존 심볼릭 링크 및 디렉토리 완전 정리
echo "빌드 전 기존 심볼릭 링크 및 디렉토리 완전 정리..."

# build가 심볼릭 링크인지 확인
if [ -L "build" ]; then
    echo "기존 build 심볼릭 링크 제거: $(readlink build)"
    rm -f build
fi

# build가 디렉토리인지 확인하고 제거
if [ -d "build" ]; then
    echo "기존 build 디렉토리 제거 중..."
    rm -rf build
    echo "✅ 기존 build 디렉토리 제거 완료"
fi

# build가 파일인지 확인하고 제거
if [ -f "build" ]; then
    echo "기존 build 파일 제거 중..."
    rm -f build
    echo "✅ 기존 build 파일 제거 완료"
fi

# 새로운 빈 디렉토리 생성
mkdir -p build
echo "✅ 새로운 빈 build 디렉토리 생성"

# 생성된 디렉토리 확인
echo "생성된 build 디렉토리 확인:"
ls -la build/
echo "build 디렉토리 타입: $(file build)"

# 빌드 전 디렉토리 상태
echo "빌드 전 디렉토리 상태:"
ls -la

# 프론트엔드 빌드
echo "프론트엔드 빌드..."
yarn build || {
    echo "❌ yarn build 실패!"
    echo "❌ 프론트엔드 빌드에 실패했습니다"
    echo "빌드 실패 후 디렉토리 상태:"
    ls -la
    exit 1
}

# 빌드 완료 후 디렉토리 상태
echo "빌드 완료 후 디렉토리 상태:"
ls -la

echo "✅ 빌드 완료 - 정적 파일 생성됨"
echo "빌드 결과 디렉토리 내용:"
ls -la build/
echo "빌드 파일 개수:"
find build -type f | wc -l

# 빌드 결과가 실제로 생성되었는지 확인
BUILD_FILE_COUNT=$(find build -type f | wc -l)
echo "빌드 결과 파일 개수: $BUILD_FILE_COUNT"

if [ ! -d 'build' ] || [ $BUILD_FILE_COUNT -eq 0 ]; then
    echo "❌ 빌드 결과가 생성되지 않았습니다!"
    echo "현재 디렉토리 내용:"
    ls -la
    echo "build 디렉토리 내용:"
    ls -la build/ 2>/dev/null || echo "build 디렉토리가 없습니다"
    echo "빌드 로그 확인:"
    echo "yarn build 명령어가 성공했는지 확인하세요"
    exit 1
fi

# 핵심 파일 존재 여부 확인
if [ ! -f 'build/index.html' ]; then
    echo "❌ index.html 파일이 생성되지 않았습니다!"
    echo "build 디렉토리 내용:"
    ls -la build/
    exit 1
fi

echo "✅ 핵심 빌드 파일 검증 완료"

echo "✅ 빌드 결과 검증 완료"

# 상위 디렉토리로 돌아가기
cd ..

# 빌드 결과 확인
echo "🔍 호스트 시스템에서 빌드 결과 확인..."
if [ -d "front/build" ]; then
    echo "✅ front/build 디렉토리 존재"
    BUILD_FILES=$(find front/build -type f | wc -l)
    echo "빌드 파일 개수: $BUILD_FILES"
    
    if [ $BUILD_FILES -gt 0 ]; then
        echo "✅ 빌드 결과가 호스트 시스템에 정상적으로 복사됨"
        echo "빌드 결과 샘플:"
        ls -la front/build/ | head -10
    else
        echo "❌ 빌드 디렉토리는 있지만 파일이 없습니다!"
        echo "front 디렉토리 전체 내용:"
        ls -la front/
        echo "front/build 디렉토리 내용:"
        ls -la front/build/
        exit 1
    fi
else
    echo "❌ front/build 디렉토리가 존재하지 않습니다!"
    echo "front 디렉토리 내용:"
    ls -la front/
    exit 1
fi

echo "✅ 로컬 환경에서 프론트엔드 빌드 완료"
