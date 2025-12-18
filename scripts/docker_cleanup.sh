#!/bin/bash

# Docker 정리 스크립트
# 사용하지 않는 이미지, 컨테이너, 네트워크, 볼륨 정리

set -e

echo "🧹 Docker 정리 시작..."

# 사용하지 않는 이미지 정리
echo "📦 사용하지 않는 이미지 정리 중..."
docker image prune -f

# 사용하지 않는 컨테이너 정리
echo "📦 사용하지 않는 컨테이너 정리 중..."
docker container prune -f

# 사용하지 않는 네트워크 정리
echo "🌐 사용하지 않는 네트워크 정리 중..."
docker network prune -f

# 사용하지 않는 볼륨 정리
echo "💾 사용하지 않는 볼륨 정리 중..."
docker volume prune -f

echo "✅ Docker 정리 완료"
echo "  - 정리된 이미지, 컨테이너, 네트워크, 볼륨"
