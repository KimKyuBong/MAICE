#!/bin/bash

# Docker Registry 정리 스크립트
# 레거시 이미지 정리

set -e

echo "🗑️ Docker Registry 레거시 이미지 정리 시작..."

# Registry 정리 스크립트 실행
echo "📦 Registry 정리 중..."

# 현재 시간에서 7일 이전의 이미지들 정리
CUTOFF_DATE=$(date -d '7 days ago' '+%Y-%m-%dT%H:%M:%S')

echo "🗓️ 정리 기준 날짜: ${CUTOFF_DATE}"

# 사용하지 않는 이미지 정리 (7일 이전)
docker image prune -a -f --filter "until=168h" || {
    echo "⚠️ 이미지 정리 중 일부 오류 발생 (계속 진행)"
}

# dangling 이미지 정리
docker image prune -f || {
    echo "⚠️ dangling 이미지 정리 중 일부 오류 발생 (계속 진행)"
}

echo "✅ Registry 정리 완료"
echo "  - 7일 이전 이미지 정리"
echo "  - dangling 이미지 정리"
