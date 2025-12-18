#!/bin/bash

# Docker Registry 푸시 스크립트
# 이미지 태깅 및 Registry 푸시

set -e

echo "📦 Docker Registry 푸시 시작..."

# 필수 환경 변수 검증
if [ -z "$IMAGE_NAME" ]; then
    echo "❌ IMAGE_NAME 환경 변수가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$BUILD_NUMBER" ]; then
    echo "❌ BUILD_NUMBER 환경 변수가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$REGISTRY_HOST" ]; then
    echo "❌ REGISTRY_HOST 환경 변수가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$REGISTRY_PORT" ]; then
    echo "❌ REGISTRY_PORT 환경 변수가 설정되지 않았습니다"
    exit 1
fi

echo "📋 푸시 설정:"
echo "  - 이미지명: ${IMAGE_NAME}"
echo "  - 빌드번호: ${BUILD_NUMBER}"
echo "  - Registry: ${REGISTRY_HOST}:${REGISTRY_PORT}"

# 이미지 태깅 (Registry용) - BUILD_NUMBER 우선 정책
echo "🏷️ 이미지 태깅 중..."
docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:${BUILD_NUMBER}"

# latest 태그는 선택적으로만 사용 (명시적 요청 시에만)
if [ "${PUSH_LATEST_TAG:-false}" = "true" ]; then
    echo "🏷️ latest 태그 추가 중..."
    docker tag "${IMAGE_NAME}:${BUILD_NUMBER}" "${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:latest"
fi

# Registry에 푸시
echo "📤 Registry에 푸시 중..."
echo "  - 푸시할 이미지: ${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:${BUILD_NUMBER}"

docker push "${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:${BUILD_NUMBER}" || {
    echo "❌ ${IMAGE_NAME} 이미지 Registry 푸시 실패!"
    exit 1
}

# latest 태그 푸시 (선택적)
if [ "${PUSH_LATEST_TAG:-false}" = "true" ]; then
    echo "📤 latest 태그 푸시 중..."
    docker push "${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:latest" || {
        echo "❌ ${IMAGE_NAME} latest 태그 푸시 실패!"
        exit 1
    }
fi

echo "✅ ${IMAGE_NAME} 이미지 Registry 푸시 완료"
echo "  - 이미지: ${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:${BUILD_NUMBER}"
if [ "${PUSH_LATEST_TAG:-false}" = "true" ]; then
    echo "  - 최신 태그: ${REGISTRY_HOST}:${REGISTRY_PORT}/${IMAGE_NAME}:latest"
fi
