#!/bin/bash

# 환경 변수 검증 스크립트
# 필수 환경 변수들의 존재 여부와 유효성을 검증

set -e

echo "=== 환경 변수 검증 시작 ==="

# 필수 환경 변수 검증
ERROR_COUNT=0

# OpenAI API 키 검증
if [ -n "${OPENAI_API_KEY}" ] && [ "${#OPENAI_API_KEY}" -gt 10 ]; then
    echo "✅ OpenAI API 키가 설정되어 있습니다"
else
    echo "❌ OpenAI API 키가 설정되지 않았거나 너무 짧습니다"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# Google OAuth 설정 검증
if [ -n "${GOOGLE_CLIENT_ID}" ] && [ -n "${GOOGLE_CLIENT_SECRET}" ]; then
    echo "✅ Google OAuth 설정이 올바릅니다"
else
    echo "❌ Google OAuth 설정이 누락되었습니다!"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 관리자 계정 설정 검증
if [ -n "${ADMIN_USERNAME}" ] && [ -n "${ADMIN_PASSWORD}" ]; then
    echo "✅ 관리자 계정 설정이 올바릅니다"
else
    echo "❌ 관리자 계정 설정이 누락되었습니다!"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 세션 시크릿 키 검증
if [ -n "${SESSION_SECRET_KEY}" ] && [ "${#SESSION_SECRET_KEY}" -gt 10 ]; then
    echo "✅ 세션 시크릿 키가 설정되어 있습니다"
else
    echo "❌ 세션 시크릿 키가 설정되지 않았거나 너무 짧습니다"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 데이터베이스 URL 검증
if [ -n "${DATABASE_URL}" ] && [[ "${DATABASE_URL}" == postgresql* ]]; then
    echo "✅ 데이터베이스 URL이 올바르게 설정되어 있습니다"
else
    echo "❌ 데이터베이스 URL이 올바르지 않습니다!"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 에이전트 데이터베이스 URL 검증
if [ -n "${AGENT_DATABASE_URL}" ] && [[ "${AGENT_DATABASE_URL}" == postgresql* ]]; then
    echo "✅ 에이전트 데이터베이스 URL이 올바르게 설정되어 있습니다"
else
    echo "❌ 에이전트 데이터베이스 URL이 올바르지 않습니다!"
    ERROR_COUNT=$((ERROR_COUNT + 1))
fi

# 검증 결과 출력
if [ $ERROR_COUNT -gt 0 ]; then
    echo "❌ 총 $ERROR_COUNT 개의 필수 환경 변수가 누락되었습니다!"
    echo "=== 누락된 환경 변수 목록 ==="
    [ -z "${OPENAI_API_KEY}" ] && echo "  - OPENAI_API_KEY"
    [ -z "${GOOGLE_CLIENT_ID}" ] && echo "  - GOOGLE_CLIENT_ID"
    [ -z "${GOOGLE_CLIENT_SECRET}" ] && echo "  - GOOGLE_CLIENT_SECRET"
    [ -z "${ADMIN_USERNAME}" ] && echo "  - ADMIN_USERNAME"
    [ -z "${ADMIN_PASSWORD}" ] && echo "  - ADMIN_PASSWORD"
    [ -z "${SESSION_SECRET_KEY}" ] && echo "  - SESSION_SECRET_KEY"
    [ -z "${DATABASE_URL}" ] && echo "  - DATABASE_URL"
    [ -z "${AGENT_DATABASE_URL}" ] && echo "  - AGENT_DATABASE_URL"
    echo "================================"
    exit 1
else
    echo "✅ 모든 필수 환경 변수 검증 완료"
fi

echo "=== 환경 변수 검증 완료 ==="
