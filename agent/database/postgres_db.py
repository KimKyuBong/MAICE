"""
PostgreSQL 기반 에이전트 데이터베이스
Pydantic + Repository 패턴 사용, 모델 기반 테이블 자동 생성
"""

import asyncio
from typing import Optional
import asyncpg
import logging

from .repository import (
    QuestionClassificationRepository,
    ClarificationSessionRepository,
    ClarificationConversationRepository,
    SessionSummaryRepository,
    SessionTitleRepository
)

logger = logging.getLogger(__name__)

class PostgreSQLAgentDatabase:
    def __init__(self, database_url: str = None):
        # 환경변수에서 AGENT_DATABASE_URL 읽기
        if database_url is None:
            import os
            database_url = os.getenv("AGENT_DATABASE_URL")
        
        if database_url is None:
            self.database_url = "postgresql://postgres:postgres@postgres:5432/maice_agent"
            logger.info("🐳 Docker 환경: postgres:5432 사용 (환경변수 없음)")
        else:
            self.database_url = database_url
            logger.info(f"🔗 환경변수에서 데이터베이스 URL 사용: {database_url.split('@')[1] if '@' in database_url else '설정됨'}")
        
        self.pool: Optional[asyncpg.Pool] = None
        
        # Repository 인스턴스들 (실제 사용하는 것만)
        self.classification_repo: Optional[QuestionClassificationRepository] = None
        self.clarification_repo: Optional[ClarificationSessionRepository] = None
        self.clarification_conversation_repo: Optional[ClarificationConversationRepository] = None
        self.session_summary_repo: Optional[SessionSummaryRepository] = None
        self.session_title_repo: Optional[SessionTitleRepository] = None
    
    async def initialize(self):
        """데이터베이스 연결 풀 초기화 및 테이블 생성"""
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                logger.info(f"🔄 데이터베이스 초기화 시도 {attempt + 1}/{max_retries}")
                
                # 첫 번째 시도에서 데이터베이스 존재 여부 확인
                if attempt == 0:
                    await self._ensure_database_exists()
                
                # 데이터베이스에 직접 연결 시도
                self.pool = await asyncpg.create_pool(
                    self.database_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=30
                )
                
                # 연결 테스트
                async with self.pool.acquire() as conn:
                    await conn.execute("SELECT 1")
                
                await self._ensure_tables_exist()
                await self._initialize_repositories()
                
                logger.info("✅ PostgreSQL 에이전트 데이터베이스 초기화 완료")
                return
                
            except Exception as e:
                logger.error(f"❌ 데이터베이스 초기화 실패 (시도 {attempt + 1}/{max_retries}): {e}")
                
                if self.pool:
                    try:
                        await self.pool.close()
                    except:
                        pass
                    self.pool = None
                
                # 첫 번째 시도에서 실패한 경우 데이터베이스 생성 재시도
                if attempt == 0 and ("does not exist" in str(e).lower() or "database" in str(e).lower()):
                    logger.info("🔄 데이터베이스가 존재하지 않는 것 같습니다. 데이터베이스 생성을 재시도합니다...")
                    try:
                        await self._ensure_database_exists()
                    except Exception as db_create_error:
                        logger.warning(f"⚠️ 데이터베이스 생성 재시도 실패: {db_create_error}")
                
                if attempt < max_retries - 1:
                    logger.info(f"⏳ {retry_delay}초 후 재시도...")
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # 지수 백오프
                else:
                    logger.error("❌ 최대 재시도 횟수 초과. 데이터베이스 초기화 실패")
                    raise
    
    async def _ensure_database_exists(self):
        """데이터베이스가 존재하지 않으면 생성"""
        try:
            # 기본 PostgreSQL 서버에 연결 (postgres 데이터베이스)
            base_url = self.database_url.replace("/maice_agent", "/postgres")
            temp_pool = await asyncpg.create_pool(base_url, min_size=1, max_size=1)
            
            async with temp_pool.acquire() as conn:
                # 데이터베이스 존재 여부 확인
                db_exists = await conn.fetchval(
                    "SELECT 1 FROM pg_database WHERE datname = 'maice_agent'"
                )
                
                if not db_exists:
                    logger.info("🔨 데이터베이스 'maice_agent'가 존재하지 않습니다. 생성 중...")
                    # 데이터베이스 생성
                    await conn.execute("CREATE DATABASE maice_agent")
                    logger.info("✅ 데이터베이스 'maice_agent' 생성 완료")
                else:
                    logger.info("✅ 데이터베이스 'maice_agent'가 이미 존재합니다")
            
            await temp_pool.close()
            
        except Exception as e:
            logger.warning(f"⚠️ 데이터베이스 생성 확인 실패: {e}")
            # 데이터베이스가 이미 존재하거나 권한 문제일 수 있음
            # 실제 연결 시도에서 확인하도록 함
            pass
    
    async def _ensure_tables_exist(self):
        """필요한 테이블들이 존재하는지 확인하고 없으면 생성"""
        if not self.pool:
            raise RuntimeError("데이터베이스 풀이 초기화되지 않았습니다")
        
        try:
            async with self.pool.acquire() as conn:
                # 테이블 존재 여부 확인
                tables = await self._get_existing_tables(conn)
                
                # 필요한 테이블들 정의 (실제 사용하는 테이블만)
                required_tables = {
                    'llm_prompt_logs': self._get_llm_prompt_logs_table_sql(),
                    'llm_response_logs': self._get_llm_response_logs_table_sql(),
                    'agent_question_classifications': self._get_classification_table_sql(),
                    'agent_clarification_conversations': self._get_clarification_session_table_sql(),
                    'agent_clarification_turns': self._get_clarification_turns_table_sql(),
                    'session_summaries': self._get_session_summary_table_sql(),
                    'session_titles': self._get_session_title_table_sql()
                }
                
                # 없는 테이블만 생성
                for table_name, create_sql in required_tables.items():
                    if table_name not in tables:
                        logger.info(f"🔨 테이블 생성 중: {table_name}")
                        try:
                            await conn.execute(create_sql)
                            await self._create_table_indexes(conn, table_name)
                            logger.info(f"✅ 테이블 생성 완료: {table_name}")
                        except Exception as table_error:
                            # 테이블 생성 실패 시 상세 로그
                            if "already exists" in str(table_error).lower():
                                logger.info(f"✅ 테이블 이미 존재 (동시 생성): {table_name}")
                            else:
                                logger.error(f"❌ 테이블 생성 실패: {table_name} - {table_error}")
                                raise
                    else:
                        logger.debug(f"✅ 테이블 이미 존재: {table_name}")
                
        except Exception as e:
            logger.error(f"❌ 테이블 확인/생성 실패: {e}")
            raise
    
    async def _get_existing_tables(self, conn) -> set:
        """기존 테이블 목록 조회"""
        query = """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """
        rows = await conn.fetch(query)
        return {row['table_name'] for row in rows}
    
    def _get_llm_prompt_logs_table_sql(self) -> str:
        """LLM 프롬프트 로그 테이블 생성 SQL"""
        return """
            CREATE TABLE IF NOT EXISTS llm_prompt_logs (
                id SERIAL PRIMARY KEY,
                session_id INTEGER,
                user_id INTEGER,
                agent_name VARCHAR(100),
                prompt_type VARCHAR(50),
                prompt_content TEXT,
                request_id VARCHAR(255),
                model_name VARCHAR(100),
                temperature DOUBLE PRECISION,
                max_tokens INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_llm_response_logs_table_sql(self) -> str:
        """LLM 응답 로그 테이블 생성 SQL"""
        return """
            CREATE TABLE IF NOT EXISTS llm_response_logs (
                id SERIAL PRIMARY KEY,
                prompt_log_id INTEGER REFERENCES llm_prompt_logs(id) ON DELETE SET NULL,
                session_id INTEGER,
                user_id INTEGER,
                agent_name VARCHAR(100),
                response_content TEXT,
                response_tokens INTEGER,
                response_time_ms INTEGER,
                success BOOLEAN,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_classification_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_question_classifications (
                request_id VARCHAR(255) PRIMARY KEY,
                original_question TEXT NOT NULL,
                knowledge_code VARCHAR(100) NOT NULL,
                quality VARCHAR(50) NOT NULL,
                missing_fields JSONB,
                unit_tags JSONB,
                reasoning TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_clarification_session_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_clarification_conversations (
                request_id VARCHAR(255) PRIMARY KEY,
                original_question TEXT NOT NULL,
                initial_missing_fields JSONB,
                friendly_questions JSONB,
                unit_tags JSONB,
                status VARCHAR(50) DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_clarification_turns_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_clarification_turns (
                id SERIAL PRIMARY KEY,
                request_id VARCHAR(255) NOT NULL,
                turn_number INTEGER NOT NULL,
                current_focus TEXT NOT NULL,
                clarification_question TEXT NOT NULL,
                student_response TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_evaluation_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_answer_evaluations (
                request_id VARCHAR(255) PRIMARY KEY,
                session_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                evaluation JSONB NOT NULL,
                metadata JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_final_answer_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS agent_final_answers (
                request_id VARCHAR(255) PRIMARY KEY,
                session_id INTEGER NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                evaluation JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_learning_status_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS student_learning_status (
                session_id INTEGER PRIMARY KEY,
                question_type VARCHAR(100) NOT NULL,
                understanding_level VARCHAR(50) NOT NULL,
                difficulty_areas JSONB,
                learning_style VARCHAR(100) NOT NULL,
                analysis_summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_session_summary_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS session_summaries (
                session_id INTEGER PRIMARY KEY,
                conversation_summary TEXT NOT NULL,
                student_status JSONB NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    def _get_session_title_table_sql(self) -> str:
        return """
            CREATE TABLE IF NOT EXISTS session_titles (
                session_id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
    
    async def _create_table_indexes(self, conn, table_name: str):
        """테이블별 인덱스 생성"""
        index_sqls = {
            'llm_prompt_logs': [
                "CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_session_id ON llm_prompt_logs(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_user_id ON llm_prompt_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_agent_name ON llm_prompt_logs(agent_name)",
                "CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_created_at ON llm_prompt_logs(created_at)"
            ],
            'llm_response_logs': [
                "CREATE INDEX IF NOT EXISTS idx_llm_response_logs_prompt_log_id ON llm_response_logs(prompt_log_id)",
                "CREATE INDEX IF NOT EXISTS idx_llm_response_logs_session_id ON llm_response_logs(session_id)",
                "CREATE INDEX IF NOT EXISTS idx_llm_response_logs_user_id ON llm_response_logs(user_id)",
                "CREATE INDEX IF NOT EXISTS idx_llm_response_logs_agent_name ON llm_response_logs(agent_name)",
                "CREATE INDEX IF NOT EXISTS idx_llm_response_logs_created_at ON llm_response_logs(created_at)"
            ],
            'agent_question_classifications': [
                "CREATE INDEX IF NOT EXISTS idx_classifications_request_id ON agent_question_classifications(request_id)"
            ],
            'agent_clarification_conversations': [
                "CREATE INDEX IF NOT EXISTS idx_clarifications_request_id ON agent_clarification_conversations(request_id)"
            ],
            'agent_clarification_turns': [
                "CREATE INDEX IF NOT EXISTS idx_clarification_turns_request_id ON agent_clarification_turns(request_id)"
            ],
            'session_summaries': [
                "CREATE INDEX IF NOT EXISTS idx_session_summaries_session_id ON session_summaries(session_id)"
            ],
            'session_titles': [
                "CREATE INDEX IF NOT EXISTS idx_session_titles_session_id ON session_titles(session_id)"
            ]
        }
        
        for index_sql in index_sqls.get(table_name, []):
            try:
                await conn.execute(index_sql)
                logger.debug(f"✅ 인덱스 생성/확인 완료: {table_name}")
            except Exception as e:
                # 인덱스가 이미 존재하는 경우 무시
                if "already exists" not in str(e).lower():
                    logger.warning(f"⚠️ 인덱스 생성 실패: {e}")
                else:
                    logger.debug(f"✅ 인덱스 이미 존재: {table_name}")
    
    async def _initialize_repositories(self):
        """Repository 인스턴스들 초기화 (실제 사용하는 것만)"""
        if self.pool:
            self.classification_repo = QuestionClassificationRepository(self.pool)
            self.clarification_repo = ClarificationSessionRepository(self.pool)
            self.clarification_conversation_repo = ClarificationConversationRepository(self.pool)
            self.session_summary_repo = SessionSummaryRepository(self.pool)
            self.session_title_repo = SessionTitleRepository(self.pool)
    
    async def close(self):
        """데이터베이스 연결 종료"""
        if self.pool:
            await self.pool.close()
            logger.info("✅ PostgreSQL 연결 풀 종료")
    
    # Repository 접근자들
    @property
    def classification(self) -> QuestionClassificationRepository:
        if not self.classification_repo:
            raise RuntimeError("Repository가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self.classification_repo
    
    @property
    def clarification(self) -> ClarificationSessionRepository:
        if not self.clarification_repo:
            raise RuntimeError("Repository가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self.clarification_repo
    
    @property
    def clarification_conversation(self) -> ClarificationConversationRepository:
        if not self.clarification_conversation_repo:
            raise RuntimeError("Repository가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self.clarification_conversation_repo
    
    @property
    def session_summary(self) -> SessionSummaryRepository:
        if not self.session_summary_repo:
            raise RuntimeError("Repository가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self.session_summary_repo
    
    @property
    def session_title(self) -> SessionTitleRepository:
        if not self.session_title_repo:
            raise RuntimeError("Repository가 초기화되지 않았습니다. initialize()를 먼저 호출하세요.")
        return self.session_title_repo

# 전역 인스턴스
_agent_db: Optional[PostgreSQLAgentDatabase] = None

async def get_postgres_agent_db() -> PostgreSQLAgentDatabase:
    """PostgreSQL 에이전트 데이터베이스 인스턴스 반환"""
    global _agent_db
    if _agent_db is None:
        _agent_db = PostgreSQLAgentDatabase()
        await _agent_db.initialize()
    return _agent_db

async def get_db() -> PostgreSQLAgentDatabase:
    """get_db 함수 - get_postgres_agent_db의 별칭"""
    return await get_postgres_agent_db()

async def close_postgres_agent_db():
    """PostgreSQL 에이전트 데이터베이스 연결 종료"""
    global _agent_db
    if _agent_db:
        await _agent_db.close()
        _agent_db = None
