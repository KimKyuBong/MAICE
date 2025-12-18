#!/bin/bash

# 원격 서버 데이터베이스 스키마 수정 스크립트
# agent_name 컬럼 누락 문제 해결

set -e

echo "🔧 원격 서버 데이터베이스 스키마 수정 시작..."

# 환경변수 확인
if [ -z "$DB_HOST" ]; then
    echo "❌ DB_HOST 환경변수가 설정되지 않았습니다."
    echo "사용법: DB_HOST=your-server-ip ./fix_remote_db_schema.sh"
    exit 1
fi

if [ -z "$DB_PASSWORD" ]; then
    echo "❌ DB_PASSWORD 환경변수가 설정되지 않았습니다."
    echo "사용법: DB_PASSWORD=your-password ./fix_remote_db_schema.sh"
    exit 1
fi

DB_USER=${DB_USER:-postgres}
DB_NAME=${DB_NAME:-maice_agent}

echo "📋 연결 정보:"
echo "  - 호스트: $DB_HOST"
echo "  - 사용자: $DB_USER"
echo "  - 데이터베이스: $DB_NAME"

# 1. 현재 테이블 구조 확인
echo "🔍 현재 llm_response_logs 테이블 구조 확인..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'llm_response_logs' 
ORDER BY ordinal_position;
" || {
    echo "❌ 테이블 구조 확인 실패!"
    exit 1
}

# 2. agent_name 컬럼 추가
echo "🔧 agent_name 컬럼 추가 중..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
DO \$\$
BEGIN
    -- agent_name 컬럼이 없으면 추가
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'llm_response_logs' 
        AND column_name = 'agent_name'
    ) THEN
        ALTER TABLE llm_response_logs 
        ADD COLUMN agent_name VARCHAR(100);
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_llm_response_logs_agent_name 
        ON llm_response_logs(agent_name);
        
        RAISE NOTICE 'agent_name 컬럼과 인덱스가 성공적으로 추가되었습니다.';
    ELSE
        RAISE NOTICE 'agent_name 컬럼이 이미 존재합니다.';
    END IF;
END \$\$;
" || {
    echo "❌ agent_name 컬럼 추가 실패!"
    exit 1
}

# 3. llm_prompt_logs 테이블도 확인 및 수정
echo "🔧 llm_prompt_logs 테이블 확인 및 수정 중..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
DO \$\$
BEGIN
    -- agent_name 컬럼이 없으면 추가
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'llm_prompt_logs' 
        AND column_name = 'agent_name'
    ) THEN
        ALTER TABLE llm_prompt_logs 
        ADD COLUMN agent_name VARCHAR(100);
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_agent_name 
        ON llm_prompt_logs(agent_name);
        
        RAISE NOTICE 'llm_prompt_logs에 agent_name 컬럼과 인덱스가 성공적으로 추가되었습니다.';
    ELSE
        RAISE NOTICE 'llm_prompt_logs에 agent_name 컬럼이 이미 존재합니다.';
    END IF;
END \$\$;
" || {
    echo "❌ llm_prompt_logs agent_name 컬럼 추가 실패!"
    exit 1
}

# 4. 수정 후 테이블 구조 재확인
echo "✅ 수정 후 테이블 구조 확인..."
PGPASSWORD=$DB_PASSWORD psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('llm_response_logs', 'llm_prompt_logs')
ORDER BY table_name, ordinal_position;
" || {
    echo "❌ 수정 후 테이블 구조 확인 실패!"
    exit 1
}

echo "🎉 데이터베이스 스키마 수정이 완료되었습니다!"
echo "이제 에이전트 서비스를 재시작해주세요."
