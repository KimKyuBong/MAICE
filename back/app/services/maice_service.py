"""
MAICE 비즈니스 로직 Service
MAICE 관련 복잡한 비즈니스 로직을 제어하는 서비스
"""

from typing import Dict, Any, Optional, List, AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
import uuid
import logging
import json
from datetime import datetime

from app.services.maice.session_repository import NewSessionService
from app.services.maice.streaming_processor import AIAgentService
from app.services.maice.conversation_orchestrator import ChatService
from app.utils.redis_client import RedisAgentClient
from app.services.user_mode_service import get_user_mode_service
from app.utils.timezone import utc_to_kst

logger = logging.getLogger(__name__)


class MaiceService:
    """MAICE 통합 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def process_chat_streaming(
        self,
        question: str,
        user_id: int,
        session_id: Optional[int] = None,
        message_type: str = "question",
        conversation_history: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """채팅 스트리밍 처리"""
        try:
            logger.info(f"🚀 MAICE 채팅 시작: message='{question[:50]}...', session_id={session_id}")
            
            # 사용자 모드 할당
            user_mode_service = await get_user_mode_service(self.db_session)
            user_mode = await user_mode_service.get_or_assign_mode(user_id)
            use_agents = (user_mode == 'agent')
            
            logger.info(f"🎯 사용자 모드 할당: {user_mode}, use_agents={use_agents}")
            
            if not use_agents:
                # 프리패스 모드
                async for message in self._process_freepass_streaming(
                    question, user_id, session_id, message_type, conversation_history
                ):
                    yield message
            else:
                # 에이전트 모드
                async for message in self._process_agent_streaming(
                    question, user_id, session_id, message_type, conversation_history
                ):
                    yield message
                    
        except Exception as e:
            logger.error(f"❌ MAICE 채팅 처리 오류: {str(e)}")
            error_msg = f"data: {json.dumps({'type': 'error', 'message': f'채팅 처리 중 오류가 발생했습니다: {str(e)}'}, ensure_ascii=False)}\n\n"
            yield error_msg
    
    async def process_test_chat_streaming(
        self,
        question: str,
        user_id: int,
        session_id: Optional[int] = None,
        message_type: str = "question", 
        conversation_history: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """테스트 채팅 스트리밍 처리"""
        # 일반 채팅과 동일한 로직 사용
        async for message in self.process_chat_streaming(
            question, user_id, session_id, message_type, conversation_history
        ):
            yield message
    
    async def process_clarification(
        self,
        clarification_answer: str,
        session_id: Optional[int],
        user_id: int,
        request_id: Optional[str] = None,
        question_index: int = 1,
        total_questions: int = 1
    ) -> Dict[str, Any]:
        """명료화 답변 처리"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            request_id = request_id or str(uuid.uuid4())
            
            # 명료화 답변 저장
            await session_service.save_user_message(
                session_id=session_id,
                user_id=user_id,
                content=clarification_answer,
                message_type="user_clarification_response",
                request_id=request_id
            )
            
            return {
                "type": "clarification_complete",
                "message": "명료화 답변이 처리되었습니다",
                "session_id": session_id,
                "clarification_answer": clarification_answer
            }
            
        except Exception as e:
            logger.error(f"❌ 명료화 처리 오류: {str(e)}")
            raise
    
    async def get_user_sessions(self, user_id: int) -> List[Dict[str, Any]]:
        """사용자 세션 목록 조회"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            sessions = await session_service.get_user_sessions(user_id)
            
            return sessions
            
        except Exception as e:
            logger.error(f"❌ 세션 목록 조회 오류: {str(e)}")
            raise
    
    async def create_new_session(
        self,
        user_id: int,
        initial_question: Optional[str] = None
    ) -> int:
        """새 세션 생성"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            session_id = await session_service.create_new_session(
                user_id=user_id,
                initial_question=initial_question
            )
            
            return session_id
            
        except Exception as e:
            logger.error(f"❌ 세션 생성 오류: {str(e)}")
            raise
    
    async def get_session_info(self, session_id: int) -> Optional[Dict[str, Any]]:
        """세션 정보 조회"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            session_info = await session_service.get_session_info(session_id)
            
            if session_info:
                # 대화 히스토리 조회
                conversation_history = await session_service.get_conversation_history(session_id)
                
                # 프론트엔드 형식으로 메시지 변환
                messages = []
                for item in conversation_history:
                    if item.get('question_text'):
                        messages.append({
                            'id': f"user_{item['id']}",
                            'content': item['question_text'],
                            'sender': 'user',
                            'timestamp': item['created_at'] if isinstance(item.get('created_at'), str) else utc_to_kst(item.get('created_at'))
                        })
                    if item.get('answer_text'):
                        messages.append({
                            'id': f"ai_{item['id']}",
                            'content': item['answer_text'],
                            'sender': 'assistant',
                            'timestamp': item['created_at'] if isinstance(item.get('created_at'), str) else utc_to_kst(item.get('created_at'))
                        })
                
                session_info['conversation_history'] = messages
            
            return session_info
            
        except Exception as e:
            logger.error(f"❌ 세션 정보 조회 오류: {str(e)}")
            raise
    
    async def get_session_history(self, session_id: int) -> List[Dict[str, Any]]:
        """세션 대화 기록 조회"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            history = await session_service.get_conversation_history(session_id)
            
            # 프론트엔드 형식으로 메시지 변환
            messages = []
            for item in history:
                if item.get('content'):
                    messages.append({
                        'id': item['id'],
                        'content': item['content'],
                        'sender': item.get('sender', 'user'),
                        'message_type': item.get('message_type'),
                        'timestamp': item['created_at'] if isinstance(item.get('created_at'), str) else utc_to_kst(item.get('created_at')),
                        'request_id': item.get('request_id')
                    })
            
            return messages
            
        except Exception as e:
            logger.error(f"❌ 세션 대화 기록 조회 오류: {str(e)}")
            raise
    
    async def delete_session(self, session_id: int, user_id: int) -> bool:
        """세션 삭제"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            success = await session_service.delete_session(session_id, user_id)
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 세션 삭제 오류: {str(e)}")
            raise
    
    async def _process_freepass_streaming(
        self,
        question: str,
        user_id: int,
        session_id: Optional[int],
        message_type: str,
        conversation_history: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """프리패스 모드 스트리밍 처리"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            session_service = NewSessionService(self.db_session)
            agent_service = AIAgentService(session_service)
            
            # 서비스 초기화
            await agent_service.initialize()
            
            logger.info("✅ AIAgentService 프리패스 모드 초기화 완료")
            
            # 프리패스 모드로 스트리밍 채팅
            async for message in agent_service.process_freepass_streaming(
                question=question,
                conversation_history=conversation_history,
                user_id=user_id,
                session_id=session_id
            ):
                logger.info(f"📤 프리패스 메시지 전송: {message[:100]}...")
                yield message
                
        except Exception as e:
            logger.error(f"❌ 프리패스 스트리밍 오류: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'프리패스 처리 중 오류가 발생했습니다: {str(e)}'}, ensure_ascii=False)}\n\n"
    
    async def _process_agent_streaming(
        self,
        question: str,
        user_id: int,
        session_id: Optional[int],
        message_type: str,
        conversation_history: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """에이전트 모드 스트리밍 처리"""
        try:
            from app.services.maice.session_repository import NewSessionService
            
            # Redis 클라이언트 생성
            redis_client = RedisAgentClient()
            await redis_client.initialize()
            
            session_service = NewSessionService(self.db_session)
            agent_service = AIAgentService(session_service)
            chat_service = ChatService(session_service, agent_service, redis_client)
            
            # 서비스 초기화
            await chat_service.initialize()
            
            logger.info("✅ ChatService 초기화 완료")
            
            # 질문 처리 스트리밍
            async for message in chat_service.process_question_streaming(
                question=question,
                user_id=user_id,
                session_id=session_id,
                message_type=message_type,
                conversation_history=conversation_history,
                user_mode="agent"
            ):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 에이전트 스트리밍 오류: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'에이전트 처리 중 오류가 발생했습니다: {str(e)}'}, ensure_ascii=False)}\n\n"
