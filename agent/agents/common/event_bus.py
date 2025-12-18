"""
MAICE 에이전트 이벤트 버스 - 새로운 3개 채널 구조
"""

import asyncio
import json
import logging
import os
from typing import Dict, Any, Callable, Awaitable, List
from datetime import datetime

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# 새로운 4개 채널 구조
BACKEND_TO_AGENT = "maice.backend_to_agent"    # 백엔드 → 에이전트
AGENT_TO_BACKEND = "maice.agent_to_backend"    # 에이전트 → 백엔드
AGENT_STATUS = "maice.agent_status"            # 에이전트 상태
AGENT_TO_AGENT = "maice.agent_to_agent"        # 에이전트 ↔ 에이전트

class MessageType:
    """메시지 타입 상수"""
    # 백엔드 → 에이전트
    CLASSIFY_QUESTION = "classify_question"
    PROCESS_CLARIFICATION = "process_clarification"
    GENERATE_ANSWER = "generate_answer"
    OBSERVE_LEARNING = "observe_learning"
    GENERATE_SUMMARY = "generate_summary"
    
    # 에이전트 → 백엔드
    CLASSIFICATION_RESULT = "classification_result"
    CLASSIFICATION_COMPLETE = "classification_complete"
    CLASSIFICATION_FAILED = "classification_failed"
    CLASSIFICATION_ERROR = "classification_error"
    
    # 명료화 관련
    CLARIFICATION_START = "clarification_start"
    CLARIFICATION_PROGRESS = "clarification_progress"
    CLARIFICATION_QUESTION = "clarification_question"
    CLARIFICATION_SUFFICIENT = "clarification_sufficient"
    
    # 답변 관련
    ANSWER_CHUNK = "answer_chunk"
    ANSWER_RESULT = "answer_result"
    ANSWER_COMPLETE = "answer_complete"
    
    # 요약 관련
    SUMMARY_START = "summary_start"
    SUMMARY_PROGRESS = "summary_progress"
    SUMMARY_COMPLETE = "summary_complete"
    
    # 기타
    OBSERVATION_RESULT = "observation_result"
    SUMMARY_RESULT = "summary_result"
    
    # 에이전트 상태
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    
    # 에이전트 ↔ 에이전트
    NEED_CLARIFICATION = "need_clarification"      # 분류 → 명료화
    READY_FOR_ANSWER = "ready_for_answer"          # 분류/명료화 → 답변생성
    CLARIFICATION_COMPLETE = "clarification_complete"  # 명료화 → 답변생성
    ADDITIONAL_CLARIFICATION = "additional_clarification"  # 추가 명료화 질문
    
    # 답변 생성 관련
    ANSWER_GENERATED = "answer_generated"           # 답변 생성 완료
    ANSWER_GENERATION_FAILED = "answer_generation_failed"  # 답변 생성 실패
    ANSWER_GENERATION_ERROR = "answer_generation_error"    # 답변 생성 오류
    
    # 학습 관찰 관련
    OBSERVE_LEARNING = "observe_learning"          # 학습 관찰 요청

async def publish_event(channel: str, data: Dict[str, Any]):
    """이벤트 발행"""
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        redis_client = redis.from_url(redis_url)
        
        message_data = {
            "timestamp": datetime.utcnow().isoformat(),
            **data
        }
        
        await redis_client.publish(channel, json.dumps(message_data))
        logger.info(f"📤 이벤트 발행: {channel}")
        
        await redis_client.close()
        
    except Exception as e:
        logger.error(f"❌ 이벤트 발행 실패: {e}")

async def subscribe_and_listen(channels: List[str], handler: Callable[[str, Dict[str, Any]], Awaitable[None]], agent_instance=None):
    """채널 구독 및 메시지 수신"""
    redis_client = None
    pubsub = None
    
    try:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        
        # 각 에이전트가 고유한 클라이언트 이름을 가지도록 설정
        client_name = f"agent_{agent_instance.name if agent_instance else 'unknown'}_{id(agent_instance)}"
        redis_client = redis.from_url(redis_url, client_name=client_name)
        
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(*channels)
        
        logger.info(f"🔍 채널 구독 시작: {channels}")
        
        try:
            async for message in pubsub.listen():
                # 에이전트가 중지되었는지 확인
                if agent_instance and hasattr(agent_instance, 'is_running') and not agent_instance.is_running:
                    logger.info(f"🔍 에이전트 {agent_instance.name} 중지됨, 구독 종료")
                    break
                
                if message["type"] == "message":
                    try:
                        data = json.loads(message["data"])
                        channel = message["channel"].decode()
                        
                        await handler(channel, data)
                        
                    except json.JSONDecodeError as e:
                        logger.error(f"메시지 파싱 오류: {e}")
                    except Exception as e:
                        logger.error(f"메시지 처리 오류: {e}")
                        
        except asyncio.CancelledError:
            logger.info(f"🔍 구독 취소됨: {agent_instance.name if agent_instance else 'unknown'}")
            raise
        except Exception as e:
            logger.error(f"🔍 구독 중 오류: {e}")
            raise
                        
    except Exception as e:
        logger.error(f"❌ 채널 구독 실패: {e}")
        raise
    finally:
        # 안전한 정리
        try:
            if pubsub:
                await pubsub.aclose()
                logger.info(f"🔍 pubsub 정리 완료: {agent_instance.name if agent_instance else 'unknown'}")
        except Exception as e:
            logger.warning(f"⚠️ pubsub 정리 실패: {e}")
        
        try:
            if redis_client:
                await redis_client.aclose()
                logger.info(f"🔍 redis 클라이언트 정리 완료: {agent_instance.name if agent_instance else 'unknown'}")
        except Exception as e:
            logger.warning(f"⚠️ redis 클라이언트 정리 실패: {e}")


