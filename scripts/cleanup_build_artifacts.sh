#!/bin/bash
# 빌드 아티팩트 정리 스크립트
# Jenkins 파이프라인에서 사용되는 빌드 아티팩트 정리 로직

set -e  # 오류 발생 시 스크립트 종료

echo "🧹 빌드 아티팩트 정리 시작..."

# 임시 파일 정리
echo "임시 파일 정리 중..."
find . -name "*.pyc" -delete || true
find . -name "__pycache__" -type d -exec rm -rf {} + || true
find . -name ".pytest_cache" -type d -exec rm -rf {} + || true

# Docker 관련 임시 파일 정리
echo "Docker 관련 임시 파일 정리 중..."
find . -name "Dockerfile.tmp" -delete || true
find . -name ".dockerignore.tmp" -delete || true

# 빌드 로그 파일 정리
echo "빌드 로그 파일 정리 중..."
find . -name "build.log" -delete || true
find . -name "*.log" -mtime +7 -delete || true

# Node.js 관련 정리
echo "Node.js 관련 파일 정리 중..."
find . -name "node_modules" -type d -exec rm -rf {} + || true
find . -name "package-lock.json" -delete || true

# Python 관련 정리
echo "Python 관련 파일 정리 중..."
find . -name "venv" -type d -exec rm -rf {} + || true
find . -name ".venv" -type d -exec rm -rf {} + || true
find . -name "*.egg-info" -type d -exec rm -rf {} + || true

# 압축 파일 정리
echo "압축 파일 정리 중..."
find . -name "*.tar.gz" -mtime +1 -delete || true
find . -name "*.zip" -mtime +1 -delete || true

echo "✅ 빌드 아티팩트 정리 완료"
