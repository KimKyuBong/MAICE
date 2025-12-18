"""
MAICE 서비스 유틸리티 모듈
메시지 포맷팅, 컨텍스트 빌딩 등의 공통 기능을 제공
"""

import json
import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)


# 메시지 타입 상수 정의
class MessageTypes:
    """메시지 타입 상수 모음"""
    # 사용자 메시지 타입
    USER_TYPES = [
        "question", "user_question", "question_text", 
        "freepass_user"
    ]
    
    # AI 답변 메시지 타입  
    ANSWER_TYPES = [
        "answer", "maice_answer", "freepass_answer", 
        "freepass"
    ]
    
    # 컴프레핸시브 타입들 (사용자 + 답변)
    ALL_CONVERSATION_TYPES = USER_TYPES + ANSWER_TYPES + [
        "user_clarification_response", 
        "freepass_answer"
    ]


class TimeConstants:
    """시간 관련 상수"""
    # 시간 관련 상수 정의
    CLARIFICATION_TIMEOUT = 2 * 60  # 2분
    FREEPASS_TIMEOUT = 2 * 60  # 2분  
    STREAMING_TIMEOUT = 2 * 60  # 2분
    DUPLICATE_DETECTION_SECONDS = 30


class MessageFormatter:
    """SSE 메시지 포맷팅 유틸리티"""
    
    @staticmethod
    def format_sse_message(message: Dict[str, Any]) -> str:
        """SSE 메시지 포맷팅"""
        return f"data: {json.dumps(message, ensure_ascii=False)}\n\n"
    
    @staticmethod
    def format_error_message(error_message: str, session_id: Optional[int] = None) -> str:
        """오류 메시지 포맷팅"""
        error_data = {
            "type": "error",
            "message": error_message,
            "timestamp": datetime.now().isoformat()
        }
        if session_id:
            error_data["session_id"] = session_id
            
        return MessageFormatter.format_sse_message(error_data)
    
    @staticmethod
    def format_session_info(session_id: int, message: str) -> str:
        """세션 정보 메시지 포맷팅"""
        session_data = {
            "type": "session_info",
            "session_id": session_id,
            "message": message
        }
        return MessageFormatter.format_sse_message(session_data)


class ContextBuilder:
    """컨텍스트 빌딩 유틸리티"""
    
    @staticmethod
    async def build_streaming_context(session_service, session_id: int, 
                                     is_followup: bool = False) -> tuple[str, List[str]]:
        """
        슬라이딩 윈도우 + 요약 방식의 컨텍스트 구성
        - 후속질문의 경우 더 많은 맥락 정보를 포함하여 맥락 유지 강화
        - 최근 10턴(20개 메시지)은 원문 그대로 포함
        - 10턴 이전의 대화는 요약본으로 압축
        
        Args:
            is_followup: 후속질문 여부. True면 더 많은 맥락 정보 제공
        
        Returns:
            tuple: (full_context, context_parts)
        """
        context_parts = []
        RECENT_TURNS_LIMIT = 10  # 최근 10턴 (사용자+MAICE 쌍 10개 = 20개 메시지)
        
        # 1. 누적 요약 가져오기 (후속질문은 더 강화된 요약 정보 포함)
        try:
            session_summary = await session_service.get_session_summary(session_id)
            if session_summary and session_summary.strip():
                if is_followup:
                    context_parts.append(f"=== 대화 맥락 요약 (후속질문 참조용) ===\n{session_summary}")
                    logger.info(f"🔍 후속질문 - 누적 요약 포함: {session_summary[:100]}...")
                else:
                    context_parts.append(f"=== 이전 대화 요약 (10턴 이전) ===\n{session_summary}")
                    logger.info(f"🔍 누적 요약 포함: {session_summary[:100]}...")
        except Exception as e:
            logger.warning(f"⚠️ 세션 요약 조회 실패: {e}")
        
        # 2. 최근 대화 히스토리 원문 포함 (후속질문은 더 많은 메시지 포함)
        try:
            conversation_history = await session_service.get_conversation_history(session_id)
            if conversation_history:
                # 후속질문의 경우 더 많은 메시지를 포함하여 맥락 유지 강화
                if is_followup:
                    max_messages = RECENT_TURNS_LIMIT * 3  # 후속질문은 30개 메시지 (15턴)
                    logger.info(f"🔍 후속질문 - 더 많은 맥락 포함: 최대 {max_messages}개 메시지")
                else:
                    max_messages = RECENT_TURNS_LIMIT * 2  # 일반질문은 20개 메시지 (10턴)
                
                recent_messages = []
                message_count = 0
                
                for conv in reversed(conversation_history):
                    if message_count >= max_messages:
                        break
                    
                    content = conv.get('content', '')
                    message_type = conv.get('message_type', '')
                    
                    # 의미 있는 메시지만 포함
                    if content and message_type in MessageTypes.ALL_CONVERSATION_TYPES:
                        # 발신자 구분
                        if message_type in MessageTypes.USER_TYPES:
                            sender = "사용자"
                        elif message_type in MessageTypes.ANSWER_TYPES:
                            sender = "MAICE"
                        elif message_type == "maice_clarification_question":
                            sender = "MAICE (명료화)"
                        else:
                            continue
                        
                        recent_messages.insert(0, f"**{sender}**: {content}")
                        message_count += 1
                
                if recent_messages:
                    # 후속질문일 때와 일반 질문일 때 다른 헤더 사용
                    if is_followup:
                        context_parts.append(f"=== 대화 맥락 (최근 {len(recent_messages)}개 메시지) - 후속질문 참조용 ===\n" + "\n\n".join(recent_messages))
                        logger.info(f"🔍 후속질문 - 최근 {len(recent_messages)}개 메시지 원문 포함")
                    else:
                        context_parts.append(f"=== 최근 대화 내역 (최근 {len(recent_messages)}개 메시지) ===\n" + "\n\n".join(recent_messages))
                        logger.info(f"🔍 최근 {len(recent_messages)}개 메시지 원문 포함")
                    
                    # 10턴 초과 여부 체크 (자동 요약 트리거)
                    total_messages = len(conversation_history)
                    if total_messages > max_messages:
                        logger.info(f"⚠️ 대화 {total_messages}개 메시지 - 10턴 초과! 요약 업데이트 권장")
                        # 백그라운드 요약 트리거 (비동기, 응답 차단 안 함)
                        asyncio.create_task(
                            ContextBuilder._trigger_summary_update(session_service, session_id, conversation_history, max_messages)
                        )
                else:
                    logger.warning(f"⚠️ 유효한 대화 메시지를 찾을 수 없음")
        except Exception as e:
            logger.warning(f"⚠️ 대화 히스토리 조회 실패: {e}")
        
        # 3. 전체 컨텍스트 구성
        if context_parts:
            full_context = "\n\n".join(context_parts)
            if is_followup:
                # 후속질문일 때 명확한 안내 추가
                followup_header = "=== 후속 질문입니다 - 위 대화 맥락을 참조하여 이어지는 답변을 제공하세요 ===\n\n"
                full_context = followup_header + full_context
                logger.info(f"🔍 후속질문 강화된 컨텍스트 구성: {len(full_context)}자 (요약 + 최근 대화 + 후속질문 안내)")
            else:
                logger.info(f"🔍 강화된 컨텍스트 구성: {len(full_context)}자 (요약 + 최근 대화)")
        else:
            if is_followup:
                full_context = "=== 후속 질문입니다 ===\n이전 대화 내용을 찾을 수 없습니다. 일반적인 답변을 제공하세요."
            else:
                full_context = "이전 대화 내용 없음"
            logger.info(f"🔍 컨텍스트 없음")
        
        return full_context, context_parts
    
    @staticmethod
    async def _trigger_summary_update(session_service, session_id: int, 
                                     conversation_history: List[Dict], 
                                     recent_window_size: int):
        """
        백그라운드 요약 업데이트 - 10턴 이전 대화를 요약
        
        Args:
            session_service: 세션 서비스
            session_id: 세션 ID
            conversation_history: 전체 대화 히스토리
            recent_window_size: 최근 윈도우 크기 (예: 20)
        """
        try:
            # 10턴 이전의 오래된 대화만 추출
            old_messages = conversation_history[:-recent_window_size] if len(conversation_history) > recent_window_size else []
            
            if not old_messages:
                logger.info(f"🔍 요약할 이전 대화 없음")
                return
            
            # 오래된 대화를 텍스트로 변환
            old_conversation_text = []
            for msg in old_messages:
                content = msg.get('content', '')
                message_type = msg.get('message_type', '')
                
                if content and message_type in MessageTypes.ALL_CONVERSATION_TYPES:
                    sender = "사용자" if message_type in MessageTypes.USER_TYPES else "MAICE"
                    old_conversation_text.append(f"{sender}: {content}")
            
            if not old_conversation_text:
                return
            
            # ObserverAgent에게 요약 요청 (pub/sub 이벤트)
            from agents.common.event_bus import publish_event, AGENT_TO_AGENT
            import uuid
            
            request_id = str(uuid.uuid4())
            await publish_event(
                AGENT_TO_AGENT,
                {
                    "type": "update_summary",
                    "target_agent": "ObserverAgent",
                    "session_id": session_id,
                    "request_id": request_id,
                    "conversation_text": "\n".join(old_conversation_text),
                    "update_type": "incremental",  # 누적 요약
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            logger.info(f"📤 ObserverAgent에게 누적 요약 업데이트 요청: 세션 {session_id} ({len(old_messages)}개 이전 메시지)")
            
        except Exception as e:
            logger.error(f"❌ 요약 업데이트 트리거 실패: {e}")
    
    @staticmethod
    async def build_freepass_history(session_service, session_id: int,
                                   conversation_history: Optional[List] = None) -> List[Dict[str, Any]]:
        """프리패스 모드용 대화 히스토리 구성"""
        actual_conversation_history = conversation_history or []
        
        if session_id:
            try:
                session_history = await session_service.get_conversation_history(session_id)
                if session_history:
                    # DB 히스토리를 프리토커 에이전트 형식으로 변환
                    actual_conversation_history = []
                    for msg in session_history:
                        if msg.get("message_type") in MessageTypes.ALL_CONVERSATION_TYPES:
                            # 사용자 메시지와 마이스 메시지 역할 분리
                            if msg.get("message_type") in MessageTypes.USER_TYPES:
                                role = "user"
                            else:
                                role = "assistant"
                            
                            content = msg.get("content", "") or msg.get("question_text", "")
                            if content:
                                actual_conversation_history.append({
                                    "role": role,
                                    "content": content
                                })
                    logger.info(f"📚 세션 히스토리 로드: {len(actual_conversation_history)}개 메시지")
            except Exception as e:
                logger.error(f"❌ 세션 히스토리 조회 실패: {e}")
                actual_conversation_history = conversation_history or []
        
        return actual_conversation_history


class ResponseHelper:
    """응답 처리 헬퍼 유틸리티"""
    
    @staticmethod
    async def save_streaming_response(session_service, session_id: int, user_id: int,
                                   response_type: str, content: str, 
                                   message_type: str, request_id: str = None) -> None:
        """스트리밍 응답 메시지 저장"""
        try:
            import uuid
            if not request_id:
                request_id = str(uuid.uuid4())
                
            await session_service.save_maice_message(
                session_id=session_id,
                user_id=user_id,
                content=content,
                message_type=message_type,
                request_id=request_id
            )
            logger.info(f"✅ {response_type} DB 저장 완료")
        except Exception as e:
            logger.error(f"❌ {response_type} DB 저장 실패: {e}")
    
    @staticmethod
    async def update_session_state(session_service, session_id: int, 
                                 current_stage: str = None, last_message_type: str = None, **kwargs) -> None:
        """세션 상태 업데이트 헬퍼"""
        try:
            await session_service.update_session_state(
                session_id=session_id,
                current_stage=current_stage,
                last_message_type=last_message_type,
                **kwargs
            )
            logger.info(f"✅ 세션 {session_id} 상태 업데이트 완료")
        except Exception as e:
            logger.error(f"❌ 세션 {session_id} 상태 업데이트 실패: {e}")
