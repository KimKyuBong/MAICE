import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from app.models.models import Base, UserModel, UserRole
from datetime import datetime
import secrets
from sqlalchemy.sql import select
import logging
import sqlalchemy as sa
from sqlalchemy import inspect

load_dotenv()

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# PostgreSQL 연결
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@postgres:5432/maice_web")
# 명시적으로 asyncpg 사용
if not DATABASE_URL.startswith("postgresql+asyncpg://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(
    DATABASE_URL, 
    echo=False,
    pool_size=100,  # 연결 풀 크기 대폭 증가
    max_overflow=200,  # 최대 오버플로우 연결 수 대폭 증가
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=1800,  # 연결 재활용 시간 (30분으로 단축)
    pool_timeout=120,  # 연결 대기 시간 증가
    # 동시성 문제 해결을 위한 추가 설정
    pool_reset_on_return='commit',  # 커밋 시 풀 리셋
    isolation_level='AUTOCOMMIT',  # 자동 커밋으로 동시성 개선
    connect_args={
        "server_settings": {
            "application_name": "maice_backend",
            "jit": "off",  # JIT 컴파일러 비활성화로 성능 향상
            "default_transaction_isolation": "read committed"  # 읽기 커밋된 격리 수준
        }
    }
)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ----------------------------
# Auto schema sync (dev-friendly)
# ----------------------------
def _str_to_bool(v: str | None, default: bool = True) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "y", "on")


def _compile_server_default(sync_conn, server_default) -> str | None:
    """Try to compile server_default to SQL string, return None on failure."""
    if server_default is None:
        return None
    try:
        arg = getattr(server_default, "arg", None)
        if arg is None:
            return None
        # arg can be TextClause/ClauseElement
        if hasattr(arg, "compile"):
            return str(arg.compile(dialect=sync_conn.dialect))
        return str(arg)
    except Exception:
        return None


def _table_has_rows(sync_conn, table_name: str) -> bool:
    prep = sync_conn.dialect.identifier_preparer
    qt = prep.quote(table_name)
    try:
        # fast existence check
        return sync_conn.execute(sa.text(f"SELECT 1 FROM {qt} LIMIT 1")).first() is not None
    except Exception:
        # if table not readable for any reason, assume it has data to stay safe
        return True


def _add_missing_columns_sync(sync_conn):
    """
    Add missing columns ONLY (no drops/renames/type changes).
    This is intentionally conservative for safety.
    """
    insp = inspect(sync_conn)
    existing_tables = set(insp.get_table_names())
    prep = sync_conn.dialect.identifier_preparer

    for table_name, table in Base.metadata.tables.items():
        if table_name not in existing_tables:
            continue

        existing_cols = {c["name"] for c in insp.get_columns(table_name)}
        has_rows = _table_has_rows(sync_conn, table_name)

        for col in table.columns:
            if col.name in existing_cols:
                continue

            qt = prep.quote(table_name)
            qc = prep.quote(col.name)
            coltype = col.type.compile(dialect=sync_conn.dialect)

            default_sql = _compile_server_default(sync_conn, col.server_default)
            default_clause = f" DEFAULT {default_sql}" if default_sql else ""

            # Safe rule:
            # - If table already has rows and column is NOT NULL without default, add as NULLABLE to avoid failure.
            # - Otherwise, follow model's nullability.
            if (not col.nullable) and has_rows and not default_sql and not col.primary_key:
                nullable_clause = ""
                logger.warning(
                    f"[AUTO_SCHEMA_SYNC] {table_name}.{col.name} is NOT NULL but table has rows and no default; "
                    f"adding as NULLABLE to avoid migration failure. Consider explicit migration for strict constraints."
                )
            else:
                nullable_clause = "" if col.nullable or col.primary_key else " NOT NULL"

            sql = f"ALTER TABLE {qt} ADD COLUMN {qc} {coltype}{default_clause}{nullable_clause}"
            logger.info(f"[AUTO_SCHEMA_SYNC] {sql}")
            sync_conn.execute(sa.text(sql))


async def ensure_schema():
    """
    Ensure required schema exists at runtime:
    - Create missing tables (Base.metadata.create_all(checkfirst=True))
    - Add missing columns (conservative, add-only)

    Controlled by env AUTO_SCHEMA_SYNC (default: true).
    """
    if not _str_to_bool(os.getenv("AUTO_SCHEMA_SYNC"), default=True):
        logger.info("[AUTO_SCHEMA_SYNC] AUTO_SCHEMA_SYNC=false -> skip schema sync")
        return

    try:
        logger.info("[AUTO_SCHEMA_SYNC] start: create missing tables + add missing columns")
        async with engine.begin() as conn:
            # 1) create missing tables
            await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, checkfirst=True))
            # 2) add missing columns
            await conn.run_sync(_add_missing_columns_sync)
        logger.info("[AUTO_SCHEMA_SYNC] done")
    except Exception as e:
        logger.error(f"[AUTO_SCHEMA_SYNC] failed: {e}")
        # Don't block startup hard in dev; but you can force strictness later if needed.


# DB 세션 의존성
async def get_db() -> AsyncSession:
    """FastAPI 의존성 주입을 위한 데이터베이스 세션 제공자"""
    session = async_session()
    try:
        yield session
    except Exception as e:
        await session.rollback()
        raise e
    finally:
        await session.close()

# 테스트용 독립 세션 생성
async def get_test_db() -> AsyncSession:
    """테스트용 독립 데이터베이스 세션 제공자"""
    session = async_session()
    return session

# 컨텍스트 매니저를 사용한 세션 격리 (최적화된 방식)
class TestDBSession:
    """테스트용 독립 데이터베이스 세션 컨텍스트 매니저"""
    
    def __init__(self):
        self.session = None
    
    async def __aenter__(self):
        # 공유 엔진 사용 + 독립적인 세션 생성 (안정성과 성능의 균형)
        self.session = async_session()
        return self.session
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            try:
                await self.session.close()
            except Exception:
                pass  # 세션 종료 오류 무시

# 데이터베이스 초기화
async def init_db():
    """데이터베이스 초기 데이터를 설정합니다. (테이블 생성은 Alembic으로 관리)"""
    try:
        # 개발 편의: docker compose up 시점에 누락 테이블/컬럼이 있으면 자동으로 보정
        # (기존 데이터 변경 없이 add-only)
        await ensure_schema()
            
        # 관리자 계정 생성 (환경변수로 명시적으로 설정된 경우에만)
        async with async_session() as session:
            # 환경변수에서 관리자 계정 정보 가져오기
            admin_username = os.getenv("ADMIN_USERNAME")
            admin_password = os.getenv("ADMIN_PASSWORD")

            if not admin_username or not admin_password:
                logger.info("ADMIN_USERNAME/ADMIN_PASSWORD가 설정되지 않아 관리자 계정 생성을 건너뜁니다.")
                await session.commit()
                return
            
            # 관리자 계정 존재 여부 확인
            result = await session.execute(
                select(UserModel).where(UserModel.username == admin_username)
            )
            admin = result.scalar_one_or_none()
            
            if not admin:
                from app.core.auth.security import get_password_hash
                # 환경변수로 관리자 계정 생성
                admin = UserModel(
                    username=admin_username,
                    password_hash=get_password_hash(admin_password),
                    role=UserRole.ADMIN,
                    created_at=datetime.utcnow()
                )
                session.add(admin)
                logger.info(f"관리자 계정이 생성되었습니다: {admin_username}")
            else:
                logger.info(f"관리자 계정이 이미 존재합니다: {admin_username}")

            # 기본 학생/테스트 계정 자동 생성은 공개용 코드에서 제거했습니다.
            # 필요하면 별도 스크립트(back/scripts/create_test_users.py)로 생성하거나,
            # 아래 환경변수로 명시적으로 활성화하세요.
            seed_test_users = os.getenv("SEED_TEST_USERS", "").lower() in ("1", "true", "yes")
            seed_password = os.getenv("SEED_TEST_USERS_PASSWORD")

            if seed_test_users:
                if not seed_password:
                    raise ValueError("SEED_TEST_USERS=true 인 경우 SEED_TEST_USERS_PASSWORD가 필요합니다.")

                test_accounts = [{"username": f"test_student_{i:02d}", "role": UserRole.STUDENT} for i in range(1, 11)]

                for test_account in test_accounts:
                    result = await session.execute(
                        select(UserModel).where(UserModel.username == test_account["username"])
                    )
                    existing_test_user = result.scalar_one_or_none()

                    if not existing_test_user:
                        from app.core.auth.security import get_password_hash
                        test_user = UserModel(
                            username=test_account["username"],
                            password_hash=get_password_hash(seed_password),
                            role=test_account["role"],
                            question_count=0,
                            max_questions=None,
                            remaining_questions=100,
                            progress_rate=0,
                            created_at=datetime.utcnow(),
                        )
                        session.add(test_user)

                logger.info("✅ SEED_TEST_USERS 활성화: 테스트 계정 생성(또는 유지) 완료")

            await session.commit()
            
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류 발생: {str(e)}")
        raise

async def check_db_connection():
    """데이터베이스 연결 상태를 확인합니다."""
    try:
        async with async_session() as session:
            result = await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        print(f"데이터베이스 연결 오류: {e}")
        return False