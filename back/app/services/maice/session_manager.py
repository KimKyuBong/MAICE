"""
세션별 독립 라우팅 서비스
복잡한 병렬처리 로직을 단순하고 명확한 구조로 개선
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, AsyncGenerator
from datetime import datetime
import time
import uuid

from app.services.maice.interfaces import ISessionService, IAgentService
from app.utils.redis_client import RedisAgentClient
from app.models.models import MessageType
from .utils import MessageFormatter

logger = logging.getLogger(__name__)


class SessionRouter:
    """세션별 독립 라우팅 핸들러 - 단일 진입점"""
    
    def __init__(self, session_service: ISessionService, agent_service: IAgentService, redis_client: RedisAgentClient):
        self.session_service = session_service
        self.agent_service = agent_service
        self.redis_client = redis_client
        self._session_processors: Dict[int, SessionProcessor] = {}
    
    async def process_session_message(
        self, 
        question: str, 
        user_id: int, 
        session_id: int,
        message_type: str = "question",
        user_mode: str = "agent"
    ) -> AsyncGenerator[str, None]:
        """
        세션별 메시지 처리 - 핵심 라우팅만 담당
        
        각 세션은 완전히 독립적으로 처리되며, Redis Streams 채널이 분리됨
        """
        try:
            # 1. 세션 생명주기 관리
            session_created = False 
            if not session_id:
                session_id = await self.session_service.create_new_session(user_id, question) 
                session_created = True
                logger.info(f"✅ 새 세션 생성: {session_id}")
                
                # 새 세션 즉시 정보 전달
                yield MessageFormatter.format_session_info(
                    session_id, "새 세션이 시작되었습니다."
                )

            # 2. 세션별 처리기 조회/생성 
            processor_id = session_id or 0  # 임시 처리기를 위한 식별자
            if processor_id not in self._session_processors:
                processor = SessionProcessor(session_id, self.session_service, self.agent_service, self.redis_client, user_mode)
                await processor.initialize()
                self._session_processors[processor_id] = processor
                logger.info(f"✅ 세션 {session_id} 처리기 생성")
            
            processor = self._session_processors[processor_id]
            
            # 3. 세션 상태 기반 라우팅 
            routing_result = await processor.determine_route(question, message_type)
            
            # 4. 독립적 처리 실행
            async for message in processor.execute_route(routing_result, question, user_id):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 세션 {session_id} 처리 오류: {e}")
            yield MessageFormatter.format_error_message(
                f"세션 처리 중 오류: {str(e)}", session_id
            )
    
    async def cleanup_session(self, session_id: int):
        """세션별 정리"""
        if session_id in self._session_processors:
            processor = self._session_processors[session_id]
            await processor.cleanup()
            del self._session_processors[session_id]
            logger.info(f"✅ 세션 {session_id} 정리 완료")


class SessionProcessor:
    """개별 세션 전용 처리기 - 완전히 독립적"""
    
    def __init__(self, session_id: int, session_service: ISessionService, 
                 agent_service: IAgentService, redis_client: RedisAgentClient,
                 user_mode: str = "agent"):
        self.session_id = session_id
        self.session_service = session_service
        self.agent_service = agent_service
        self.redis_client = redis_client
        self.user_mode = user_mode
        self._is_initialized = False
        
        # 세션별 독립 상태
        self.current_stage = None
        self.last_message_type = None
        
    async def initialize(self):
        """세션 처리기 초기화"""
        try:
            # 세션 상태 조회
            session_state = await self.session_service.get_session_state(self.session_id)
            self.current_stage = session_state.get("current_stage", "unknown")
            self.last_message_type = session_state.get("last_message_type", "unknown")
            
            self._is_initialized = True
            logger.info(f"✅ 세션 {self.session_id} 처리기 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 세션 {self.session_id} 처리기 초기화 실패: {e}")
            raise
    
    async def determine_route(self, question: str, message_type: str) -> Dict[str, Any]:
        """세션 상태 기반 라우팅 결정 - 단순하고 명확한 로직"""
        logger.info(f"🔍 세션 {self.session_id} 라우팅 판단")
        
        # 라우팅 규칙을 명확하게 정의
        if (self.current_stage == "clarification" and 
            self.last_message_type in ["clarification", MessageType.MAICE_CLARIFICATION_QUESTION]):
            logger.info(f"✅ 세션 {self.session_id} → 명료화 답변 처리")
            return {
                "type": "clarification_response",
                "question": question
            }
        
        elif (self.last_message_type == MessageType.MAICE_ANSWER or 
              self.last_message_type in ["maice_answer", "answer", "freepass_answer"]):
            logger.info(f"✅ 세션 {self.session_id} → 후속 질문 처리 (마지막 메시지 타입: {self.last_message_type})")
            return {
                "type": "followup_question", 
                "question": question
            }
        
        else:
            logger.info(f"✅ 세션 {self.session_id} → 새로운 질문 처리")
            return {
                "type": "new_question",
                "question": question
            }
    
    async def execute_route(self, routing: Dict[str, Any], question: str, user_id: int) -> AsyncGenerator[str, None]:
        """라우팅 결과에 따른 실행"""
        route_type = routing["type"]
        
        if route_type == "clarification_response":
            async for message in self._process_clarification(question, user_id):
                yield message
                
        elif route_type == "followup_question":
            async for message in self._process_followup(question, user_id):
                yield message
                
        else:  # new_question
            async for message in self._process_new_question(question, user_id):
                yield message
    
    async def _process_clarification(self, clarification_answer: str, user_id: int) -> AsyncGenerator[str, None]:
        """명료화 답변 처리 - 세션 독립"""
        try:
            logger.info(f"🔄 세션 {self.session_id} 명료화 답변 처리")
            
            # 명료화 답변을 DB에 저장
            request_id = str(uuid.uuid4())
            await self.session_service.save_user_message(
                session_id=self.session_id,
                user_id=user_id,
                content=clarification_answer,
                message_type=MessageType.USER_CLARIFICATION_RESPONSE,
                request_id=request_id
            )
            
            # 명료화 에이전트로 직접 전달 (세션 격리)
            async for message in self.agent_service.process_clarification_response_parallel(
                self.session_id, clarification_answer, request_id, user_id
            ):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 세션 {self.session_id} 명료화 처리 실패: {e}")
            yield MessageFormatter.format_error_message(
                f"명료화 처리 중 오류: {str(e)}", self.session_id
            )
    
    async def _process_followup(self, question: str, user_id: int) -> AsyncGenerator[str, None]:
        """후속 질문 처리 - 세션 독립"""
        try:
            logger.info(f"🔗 세션 {self.session_id} 후속 질문 처리")
            
            # 후속 질문을 DB에 저장
            request_id = str(uuid.uuid4())
            await self.session_service.save_user_message(
                session_id=self.session_id,
                user_id=user_id,
                content=question,
                message_type=MessageType.USER_FOLLOW_UP,
                request_id=request_id
            )
            
            # 에이전트 서비스로 후속 질문 전달 (세션 격리)
            async for message in self.agent_service.process_with_streaming_parallel(
                question, self.session_id, request_id, user_id, is_followup=True
            ):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 세션 {self.session_id} 후속 질문 처리 실패: {e}")
            error_msg = {
                "type": "error",
                "session_id": self.session_id,
                "message": f"후속 질문 처리 중 오류: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=True)}\n\n"
    
    async def _process_new_question(self, question: str, user_id: int) -> AsyncGenerator[str, None]:
        """새로운 질문 처리 - 모드 구분 없이 통일된 처리"""
        try:
            logger.info(f"🆕 세션 {self.session_id} 새로운 질문 처리 (모드: {self.user_mode})")
            
            # 새로운 질문을 DB에 저장
            request_id = str(uuid.uuid4())
            await self.session_service.save_user_message(
                session_id=self.session_id,
                user_id=user_id,
                content=question,
                message_type=MessageType.USER_QUESTION,
                request_id=request_id
            )
            
            # 통일된 스트리밍 처리 - 모드는 내부적으로 판단
            logger.info(f"🚀 세션 {self.session_id} 통일된 스트리밍 처리 시작")
            
            # 런타임은 상시 에이전트 모드로만 동작 (DB의 assigned_mode는 변경하지 않음)
            async for message in self.agent_service.process_with_streaming_parallel(
                question, self.session_id, request_id, user_id, is_followup=False
            ):
                yield message
                
        except Exception as e:
            logger.error(f"❌ 세션 {self.session_id} 새로운 질문 처리 실패: {e}")
            error_msg = {
                "type": "error",
                "session_id": self.session_id,
                "message": f"새로운 질문 처리 중 오류: {str(e)}"
            }
            yield f"data: {json.dumps(error_msg, ensure_ascii=True)}\n\n"
    
    async def cleanup(self):
        """세션 정리"""
        try:
            # 세션 상태 정리 (필요시)
            logger.info(f"✅ 세션 {self.session_id} 처리기 정리 완료")
        except Exception as e:
            logger.error(f"❌ 세션 {self.session_id} 처리기 정리 실패: {e}")
