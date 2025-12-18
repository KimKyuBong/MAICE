import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
import asyncpg

from .models import (
    QuestionClassificationData,
    ClarificationSessionData,
    ClarificationConversationData,
    SessionSummaryData,
    SessionTitleData
)

logger = logging.getLogger(__name__)

class BaseRepository:
    """기본 Repository 클래스"""
    
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    async def execute(self, query: str, *args):
        """SQL 실행"""
        async with self.pool.acquire() as conn:
            return await conn.execute(query, *args)
    
    async def fetch_one(self, query: str, *args):
        """단일 결과 조회"""
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
    
    async def fetch_all(self, query: str, *args):
        """여러 결과 조회"""
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

class QuestionClassificationRepository(BaseRepository):
    """질문 분류 Repository"""
    
    async def save(self, data: QuestionClassificationData) -> bool:
        """분류 결과 저장"""
        try:
            query = """
                INSERT INTO agent_question_classifications 
                (request_id, original_question, knowledge_code, quality, missing_fields, unit_tags, reasoning)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                ON CONFLICT (request_id) DO UPDATE SET
                    knowledge_code = EXCLUDED.knowledge_code,
                    quality = EXCLUDED.quality,
                    missing_fields = EXCLUDED.missing_fields,
                    unit_tags = EXCLUDED.unit_tags,
                    reasoning = EXCLUDED.reasoning
            """
            
            await self.execute(
                query,
                data.request_id,
                data.original_question,
                data.knowledge_code,
                data.quality,
                json.dumps(data.missing_fields, ensure_ascii=False),
                json.dumps(data.unit_tags, ensure_ascii=False),
                data.reasoning
            )
            
            logger.info(f"✅ 분류 결과 저장 완료: {data.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 분류 결과 저장 실패: {e}")
            return False
    
    async def get_by_request_id(self, request_id: str) -> Optional[QuestionClassificationData]:
        """request_id로 조회"""
        try:
            query = """
                SELECT * FROM agent_question_classifications 
                WHERE request_id = $1
            """
            row = await self.fetch_one(query, request_id)
            
            if row:
                return QuestionClassificationData(
                    request_id=row['request_id'],
                    original_question=row['original_question'],
                    knowledge_code=row['knowledge_code'],
                    quality=row['quality'],
                    missing_fields=json.loads(row['missing_fields']) if row['missing_fields'] else [],
                    unit_tags=json.loads(row['unit_tags']) if row['unit_tags'] else [],
                    reasoning=row['reasoning'],
                    created_at=row['created_at']
                )
            return None
            
        except Exception as e:
            logger.error(f"❌ 분류 결과 조회 실패: {e}")
            return None

class ClarificationSessionRepository(BaseRepository):
    """명료화 세션 Repository"""
    
    async def save(self, data: ClarificationSessionData) -> bool:
        """명료화 세션 저장"""
        try:
            query = """
                INSERT INTO agent_clarification_conversations 
                (request_id, original_question, initial_missing_fields, friendly_questions, unit_tags)
                VALUES ($1, $2, $3, $4, $5)
                ON CONFLICT (request_id) DO UPDATE SET
                    original_question = EXCLUDED.original_question,
                    initial_missing_fields = EXCLUDED.initial_missing_fields,
                    friendly_questions = EXCLUDED.friendly_questions,
                    unit_tags = EXCLUDED.unit_tags
            """
            
            await self.execute(
                query,
                data.request_id,
                data.original_question,
                json.dumps(data.initial_missing_fields, ensure_ascii=False),
                json.dumps(data.friendly_questions, ensure_ascii=False),
                json.dumps(data.unit_tags, ensure_ascii=False)
            )
            
            logger.info(f"✅ 명료화 세션 저장 완료: {data.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 명료화 세션 저장 실패: {e}")
            return False

class ClarificationConversationRepository(BaseRepository):
    """명료화 대화 Repository"""
    
    async def save(self, data: ClarificationConversationData) -> bool:
        """명료화 대화 턴 저장"""
        try:
            query = """
                INSERT INTO agent_clarification_turns 
                (request_id, turn_number, current_focus, clarification_question, student_response)
                VALUES ($1, $2, $3, $4, $5)
            """
            
            await self.execute(
                query,
                data.request_id,
                data.turn_number,
                data.current_focus,
                data.clarification_question,
                data.student_response
            )
            
            logger.info(f"✅ 명료화 대화 턴 저장 완료: {data.request_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 명료화 대화 턴 저장 실패: {e}")
            return False

class SessionSummaryRepository(BaseRepository):
    """세션 요약 Repository"""
    
    async def save(self, data: SessionSummaryData) -> bool:
        """세션 요약 저장"""
        try:
            query = """
                INSERT INTO session_summaries 
                (session_id, conversation_summary, student_status)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id) DO UPDATE SET
                    conversation_summary = EXCLUDED.conversation_summary,
                    student_status = EXCLUDED.student_status
            """
            
            await self.execute(
                query,
                data.session_id,
                data.conversation_summary,
                json.dumps(data.student_status, ensure_ascii=False)
            )
            
            logger.info(f"✅ 세션 요약 저장 완료: {data.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 세션 요약 저장 실패: {e}")
            return False

class SessionTitleRepository(BaseRepository):
    """세션 제목 Repository"""
    
    async def save(self, data: SessionTitleData) -> bool:
        """세션 제목 저장"""
        try:
            query = """
                INSERT INTO session_titles 
                (session_id, title)
                VALUES ($1, $2)
                ON CONFLICT (session_id) DO UPDATE SET
                    title = EXCLUDED.title
            """
            
            await self.execute(
                query,
                data.session_id,
                data.title
            )
            
            logger.info(f"✅ 세션 제목 저장 완료: {data.session_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 세션 제목 저장 실패: {e}")
            return False
