#!/bin/bash

# 인프라 관리 스크립트 테스트

set -e

echo "🧪 인프라 관리 스크립트 테스트 시작..."

# 스크립트 존재 확인
if [ ! -f "scripts/manage_infrastructure.sh" ]; then
    echo "❌ 인프라 관리 스크립트를 찾을 수 없습니다"
    exit 1
fi

# 실행 권한 부여
chmod +x scripts/manage_infrastructure.sh

echo "✅ 인프라 관리 스크립트 발견 및 권한 설정 완료"

# 도움말 테스트
echo "📋 도움말 테스트..."
./scripts/manage_infrastructure.sh --help

echo ""
echo "🔍 상태 확인 테스트..."
./scripts/manage_infrastructure.sh -s all

echo ""
echo "✅ 인프라 관리 스크립트 테스트 완료"
echo ""
echo "💡 사용 가능한 명령어 예시:"
echo "  ./scripts/manage_infrastructure.sh -s nginx     # nginx 상태 확인"
echo "  ./scripts/manage_infrastructure.sh -r redis     # redis 재시작"
echo "  ./scripts/manage_infrastructure.sh -u all       # 모든 서비스 시작"
echo "  ./scripts/manage_infrastructure.sh -l nginx     # nginx 로그 확인"
echo "  ./scripts/manage_infrastructure.sh -c nginx     # nginx 설정 확인"
