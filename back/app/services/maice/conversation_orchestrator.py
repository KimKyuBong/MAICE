"""
MAICE 질문 처리 서비스 - 단순화된 세션별 독립 처리
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime

from app.services.maice.interfaces import ISessionService, IAgentService, IChatService
from app.services.maice.session_manager import SessionRouter
from app.utils.redis_client import RedisAgentClient
from app.models.models import MessageType
from app.schemas.schemas import (
    SSEAnswerChunkMessage,
    SSEAnswerCompleteMessage,
    SSEErrorMessage
)

logger = logging.getLogger(__name__)

class ChatService(IChatService):
    """대화 처리를 위한 단순화된 통합 서비스"""
    
    def __init__(self, session_service: ISessionService, ai_agent_service: IAgentService, redis_client: RedisAgentClient):
        self.session_service = session_service
        self.ai_agent_service = ai_agent_service
        self.redis_client = redis_client
        # 세션별 독립 라우터
        self.session_router = SessionRouter(session_service, ai_agent_service, redis_client)
    
    async def initialize(self):
        """MAICE 서비스 초기화"""
        try:
            # 에이전트 서비스 초기화
            await self.ai_agent_service.initialize()
            logger.info("✅ 에이전트 서비스 초기화 완료")
            
            logger.info("✅ MAICE 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ MAICE 서비스 초기화 실패: {str(e)}")
            raise
    
    async def process_question_streaming(
        self, 
        question: str, 
        user_id: int, 
        session_id: Optional[int] = None,
        conversation_history: Optional[list] = None,
        message_type: str = "question",
        user_mode: str = "agent"
    ):
        """
        스트리밍 방식으로 질문 처리 - 세션별 독립 처리
        모든 복잡한 로직을 SessionRouter로 위임하여 단순화
        """
        try:
            logger.info(f"🚀 MAICE 스트리밍 처리 시작")
            logger.info(f"🔍 입력 파라미터: question='{question}', user_id={user_id}, session_id={session_id}")
            
            # ChatService는 단순히 라우터에 위임만 수행 (순수 조정자 역할)
            # 세션 관리는 SessionRouter가 담당 
            async for message in self.session_router.process_session_message(
                question, user_id, session_id, message_type, user_mode
            ):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 스트리밍 처리 실패: {e}")
            error_msg = SSEErrorMessage(message=f"스트리밍 처리 중 오류: {e}")
            yield await self._send_sse_message(error_msg.model_dump())
    
    async def get_session_status(self, session_id: int) -> Dict[str, Any]:
        """세션 상태 조회"""
        try:
            # 세션 정보 조회
            session = await self.session_service.get_session(session_id)
            if not session:
                return {"error": "세션을 찾을 수 없습니다"}
            
            # 최근 대화 내용 조회
            recent_messages = await self.session_service.get_recent_messages(session_id, limit=5)
            
            return {
                "session_id": session_id,
                "status": "active", 
                "recent_messages": recent_messages,
                "last_updated": session.updated_at.isoformat() if session.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"❌ 세션 상태 조회 실패: {e}")
            return {"error": str(e)}
    
    async def _send_sse_message(self, message_data) -> str:
        """SSE 메시지 전송"""
        if isinstance(message_data, str):
            return f"data: {message_data}\n\n"
        else:
            return f"data: {json.dumps(message_data, ensure_ascii=False)}\n\n"