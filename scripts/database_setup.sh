#!/bin/bash
# 데이터베이스 설정 및 마이그레이션 스크립트
# 데이터베이스가 없으면 생성하고, 있으면 마이그레이션 실행

# set -e  # 오류 발생 시 스크립트 종료 (디버깅을 위해 주석처리)

echo "🗄️ 데이터베이스 설정 및 마이그레이션 시작..."

# 환경변수 검증
if [ -z "$DB_HOST" ]; then
    echo "❌ DB_HOST가 설정되지 않았습니다"
    exit 1
fi

if [ -z "$DATABASE_URL" ]; then
    echo "❌ DATABASE_URL이 설정되지 않았습니다"
    exit 1
fi

if [ -z "$AGENT_DATABASE_URL" ]; then
    echo "❌ AGENT_DATABASE_URL이 설정되지 않았습니다"
    exit 1
fi

echo "사용할 DB_HOST: ${DB_HOST}"
echo "사용할 DATABASE_URL: ${DATABASE_URL}"
echo "사용할 AGENT_DATABASE_URL: ${AGENT_DATABASE_URL}"

# PostgreSQL 서버 연결 확인
echo "🔍 PostgreSQL 서버 상태 확인 중..."
echo "PostgreSQL 서버 연결 확인 (최대 3분 대기)..."
for attempt in $(seq 1 18); do
    echo "연결 확인 시도 $attempt/18..."
    if nc -z "${DB_HOST}" "5432" 2>/dev/null; then
        echo "✅ PostgreSQL 서버가 포트 5432에서 응답합니다"
        break
    else
        echo "❌ PostgreSQL 서버에 연결할 수 없음 (시도 $attempt/18)"
        if [ $attempt -eq 18 ]; then
            echo "❌ PostgreSQL 서버 연결 불가능! KB-Web 서버에서 배포용 PostgreSQL이 실행되고 있는지 확인하세요"
            echo "❌ 다음 명령을 KB-Web 서버에서 실행하세요:"
            echo "   cd /home/hwansi/server/maicesystem"
            echo "   docker compose -f docker-compose.prod.yml up -d postgres"
            echo "   또는 배포용 PostgreSQL 컨테이너가 실행 중인지 확인하세요:"
            echo "   docker ps | grep postgres"
            echo "   docker compose -f docker-compose.prod.yml ps"
            exit 1
        fi
        echo "대기 중... ($(( attempt * 10 ))초 경과)"
        sleep 10
    fi
done

# 데이터베이스 생성 함수
create_database() {
    local db_name=$1
    local db_url=$2
    
    echo "데이터베이스 '$db_name' 존재 여부 확인 중..."
    
    # 데이터베이스 존재 여부 확인
    if PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d postgres -tc "SELECT 1 FROM pg_database WHERE datname = '$db_name'" | grep -q 1; then
        echo "✅ 데이터베이스 '$db_name'이 이미 존재합니다"
        return 0
    else
        echo "🔄 데이터베이스 '$db_name'이 존재하지 않습니다. 생성 중..."
        PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d postgres -c "CREATE DATABASE $db_name;" || {
            echo "❌ 데이터베이스 '$db_name' 생성 실패!"
            exit 1
        }
        echo "✅ 데이터베이스 '$db_name' 생성 완료"
        return 1
    fi
}

# 메인 데이터베이스 생성
echo "메인 데이터베이스 설정 중..."
create_database "maice_web" "${DATABASE_URL}"
echo "✅ 메인 데이터베이스 설정 완료"

# 에이전트 데이터베이스 생성
echo "에이전트 데이터베이스 설정 중..."
create_database "maice_agent" "${AGENT_DATABASE_URL}"
echo "✅ 에이전트 데이터베이스 설정 완료"

# 메인 데이터베이스 마이그레이션
echo "메인 데이터베이스 마이그레이션 시작..."
echo "현재 디렉토리: $(pwd)"
echo "back 디렉토리로 이동 중..."
cd back
echo "이동 후 디렉토리: $(pwd)"

# 가상환경 생성 및 활성화
echo "Python 가상환경 생성 중..."
python3 -m venv venv || {
    echo "❌ 가상환경 생성 실패!"
    exit 1
}

echo "가상환경 활성화 중..."
. venv/bin/activate

# 가상환경에서 pip 업그레이드
echo "pip 업그레이드 중..."
pip install --upgrade pip

# Python 의존성 설치
echo "Python 의존성 설치 중..."
pip install -r requirements.txt || {
    echo "❌ 가상환경에서 의존성 설치 실패!"
    exit 1
}

echo "✅ Python 의존성 설치 완료"

# 데이터베이스 연결 테스트 (간단한 psql 명령어로 대체)
echo "데이터베이스 연결 테스트 중 (재시도 포함)..."
max_attempts=10
for attempt in $(seq 1 $max_attempts); do
    echo "연결 시도 $attempt/$max_attempts..."
    
    # 간단한 연결 테스트 (psql 명령어 사용)
    if PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d postgres -c "SELECT 1;" >/dev/null 2>&1; then
        echo "✅ 데이터베이스 연결 성공!"
        break
    else
        if [ $attempt -eq $max_attempts ]; then
            echo "❌ 데이터베이스 연결 최종 실패!"
            echo "❌ KB-Web 서버의 PostgreSQL 상태를 확인하세요"
            exit 1
        fi
        echo "❌ 연결 실패, 15초 후 재시도..."
        sleep 15
    fi
done

# 메인 데이터베이스 마이그레이션 실행
echo "🔄 메인 데이터베이스 마이그레이션 실행 중..."

# Alembic 마이그레이션 실행 (모든 스키마 관리)
echo "🔄 Alembic 마이그레이션 실행 중..."
if [ -f alembic.ini ]; then
    echo "Alembic 설정 파일 발견"
    
    # Alembic 실행을 위한 환경변수 설정
    export DATABASE_URL="${DATABASE_URL}"
    echo "Alembic용 DATABASE_URL 설정: ${DATABASE_URL}"
    
    # alembic_version 테이블이 없으면 생성 (psql 직접 사용)
    echo "Alembic 버전 테이블 생성 확인 중..."
    PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_web -c "
        CREATE TABLE IF NOT EXISTS alembic_version (
            version_num VARCHAR(32) NOT NULL,
            CONSTRAINT alembic_version_pkc PRIMARY KEY (version_num)
        );
    " || {
        echo "❌ Alembic 버전 테이블 생성 실패!"
        exit 1
    }
    echo "✅ alembic_version 테이블 확인 완료"
    
    # 현재 마이그레이션 상태 확인
    echo "현재 마이그레이션 상태 확인 중..."
    if python -m alembic current >/dev/null 2>&1; then
        CURRENT_REVISION=$(python -m alembic current 2>/dev/null | tail -1 | awk '{print $1}')
        echo "현재 리비전: ${CURRENT_REVISION}"
    else
        echo "마이그레이션 상태가 설정되지 않음 - 초기 설정 필요"
        CURRENT_REVISION=""
    fi
    
    # 데이터베이스 스키마를 확인하여 적절한 리비전으로 stamp
    echo "데이터베이스 스키마 확인 중..."
    SCHEMA_CHECK_RESULT=$(PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_web -t -c "
        SELECT 
            CASE 
                WHEN EXISTS(SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'research_consent') THEN 'has_research_consent'
                WHEN EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'llm_prompt_logs') THEN 'has_llm_logs'
                WHEN EXISTS(SELECT 1 FROM information_schema.tables WHERE table_name = 'ab_test_sessions') THEN 'has_ab_test'
                ELSE 'basic'
            END;
    " 2>/dev/null || echo "basic")
    
    echo "스키마 상태: ${SCHEMA_CHECK_RESULT}"
    
    # 스키마 상태에 따라 적절한 리비전으로 stamp
    case "${SCHEMA_CHECK_RESULT}" in
        "has_research_consent")
            echo "연구 동의 필드가 이미 존재합니다"
            if [ -z "${CURRENT_REVISION}" ]; then
                echo "최신 리비전으로 stamp 설정 중..."
                python -m alembic stamp head || {
                    echo "❌ Alembic stamp 실패!"
                    exit 1
                }
            fi
            ;;
        "has_llm_logs")
            echo "LLM 로그 테이블 존재 - 5158aab2ee4d로 stamp하여 연구 동의 필드 마이그레이션 실행"
            python -m alembic stamp 5158aab2ee4d || {
                echo "❌ Alembic stamp 실패!"
                exit 1
            }
            echo "연구 동의 필드 마이그레이션 실행 중..."
            python -m alembic upgrade 20250108_research_consent || {
                echo "❌ 연구 동의 필드 마이그레이션 실패!"
                exit 1
            }
            ;;
        "has_ab_test")
            echo "A/B 테스트 테이블 존재 - 64733d9788f7로 stamp하여 마이그레이션 실행"
            python -m alembic stamp 64733d9788f7 || {
                echo "❌ Alembic stamp 실패!"
                exit 1
            }
            echo "최신 리비전으로 마이그레이션 실행 중..."
            python -m alembic upgrade head || {
                echo "❌ 최신 마이그레이션 실패!"
                exit 1
            }
            ;;
        *)
            echo "기본 테이블만 존재 - create_all_tables로 stamp하여 마이그레이션 실행"
            python -m alembic stamp create_all_tables || {
                echo "❌ Alembic stamp 실패!"
                exit 1
            }
            echo "최신 리비전으로 마이그레이션 실행 중..."
            python -m alembic upgrade head || {
                echo "❌ 최신 마이그레이션 실패!"
                exit 1
            }
            ;;
    esac
    
    echo "✅ Alembic 마이그레이션 실행 완료"
else
    echo "⚠️ Alembic 설정 파일이 없습니다. 기본 마이그레이션만 실행합니다."
fi

# 에이전트 데이터베이스 마이그레이션 실행
echo "에이전트 데이터베이스 마이그레이션 실행 중..."
cd ../agent

# 에이전트 환경변수 설정
export AGENT_DATABASE_URL="${AGENT_DATABASE_URL}"
echo "에이전트 DATABASE_URL 설정: ${AGENT_DATABASE_URL}"

# 에이전트 데이터베이스 연결 테스트 (간단한 psql 명령어로 대체)
echo "에이전트 데이터베이스 연결 테스트 중..."
if PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_agent -c "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ 에이전트 데이터베이스 연결 성공!"
else
    echo "❌ 에이전트 데이터베이스 연결 실패"
    exit 1
fi

# 에이전트 데이터베이스에 LLM 로깅 테이블 생성
echo "에이전트 데이터베이스에 LLM 로깅 테이블 생성 중..."

# llm_prompt_logs 테이블 생성
PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_agent -c "
CREATE TABLE IF NOT EXISTS llm_prompt_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tool_name VARCHAR(255),
    provider VARCHAR(100),
    model VARCHAR(100),
    max_tokens INTEGER,
    stream BOOLEAN,
    temperature DECIMAL(3,2),
    timeout INTEGER,
    max_retries INTEGER,
    input_prompt TEXT,
    variables JSONB,
    messages JSONB,
    input_tokens INTEGER,
    message_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);" || {
    echo "❌ llm_prompt_logs 테이블 생성 실패!"
    exit 1
}

# llm_response_logs 테이블 생성
PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_agent -c "
CREATE TABLE IF NOT EXISTS llm_response_logs (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tool_name VARCHAR(255),
    provider VARCHAR(100),
    model VARCHAR(100),
    input_tokens INTEGER,
    output_tokens INTEGER,
    response_time_seconds DECIMAL(10,3),
    response_content TEXT,
    message_id VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);" || {
    echo "❌ llm_response_logs 테이블 생성 실패!"
    exit 1
}

# 인덱스 생성
echo "LLM 로그 테이블 인덱스 생성 중..."
PGPASSWORD=postgres psql -h "${DB_HOST}" -U postgres -d maice_agent -c "
CREATE INDEX IF NOT EXISTS ix_llm_prompt_logs_timestamp ON llm_prompt_logs(timestamp);
CREATE INDEX IF NOT EXISTS ix_llm_prompt_logs_tool_name ON llm_prompt_logs(tool_name);
CREATE INDEX IF NOT EXISTS ix_llm_prompt_logs_provider ON llm_prompt_logs(provider);
CREATE INDEX IF NOT EXISTS ix_llm_prompt_logs_model ON llm_prompt_logs(model);
CREATE INDEX IF NOT EXISTS ix_llm_response_logs_timestamp ON llm_response_logs(timestamp);
CREATE INDEX IF NOT EXISTS ix_llm_response_logs_tool_name ON llm_response_logs(tool_name);
CREATE INDEX IF NOT EXISTS ix_llm_response_logs_provider ON llm_response_logs(provider);
CREATE INDEX IF NOT EXISTS ix_llm_response_logs_model ON llm_response_logs(model);
" || {
    echo "❌ LLM 로그 테이블 인덱스 생성 실패!"
    exit 1
}

echo "✅ 에이전트 데이터베이스 LLM 로깅 테이블 생성 완료!"

echo "✅ 모든 데이터베이스 설정 및 마이그레이션 완료!"
