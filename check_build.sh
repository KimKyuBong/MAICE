#!/bin/bash
# 현재 배포된 빌드 파일에서 API_BASE_URL 확인

echo "=== 현재 빌드 디렉토리 확인 ==="
ls -la front/dist-* 2>/dev/null || echo "dist 디렉토리 없음"

echo ""
echo "=== build 디렉토리 확인 ==="
ls -la front/build 2>/dev/null || echo "build 디렉토리 없음"

echo ""
echo "=== 빌드된 JS 파일에서 API URL 패턴 검색 ==="
if [ -d "front/build" ]; then
    grep -r "maice.kbworks.xyz" front/build/*.js 2>/dev/null | head -5 || echo "패턴 없음"
fi

if [ -d "front/dist-blue" ]; then
    echo ""
    echo "=== dist-blue에서 API URL 패턴 검색 ==="
    grep -r "maice.kbworks.xyz" front/dist-blue/*.js 2>/dev/null | head -5 || echo "패턴 없음"
fi

if [ -d "front/dist-green" ]; then
    echo ""
    echo "=== dist-green에서 API URL 패턴 검색 ==="
    grep -r "maice.kbworks.xyz" front/dist-green/*.js 2>/dev/null | head -5 || echo "패턴 없음"
fi
