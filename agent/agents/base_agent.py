"""
기본 AI 에이전트 클래스
분산식 구성을 위한 공통 베이스 에이전트
"""

import logging
import json
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from openai import AsyncOpenAI
import os
import time

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """에이전트 상태 열거형"""
    IDLE = "idle"
    THINKING = "thinking"
    ACTING = "acting"
    COMPLETE = "complete"
    ERROR = "error"

@dataclass
class Task:
    """에이전트 작업 데이터 클래스"""
    id: str
    description: str
    metadata: Dict[str, Any]
    created_at: Optional[datetime] = None

class Tool(ABC):
    """에이전트 도구 기본 추상 클래스"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행 - 하위 클래스에서 구현해야 함"""
        pass

class BaseAgent(ABC):
    """기본 AI 에이전트 추상 클래스 - 분산식 구성용"""
    
    def __init__(self, 
                 name: str, 
                 role: str, 
                 system_prompt: str = "",
                 tools: List[Tool] = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.state = AgentState.IDLE
        self.tools = {tool.name: tool for tool in (tools or [])}
        
        # OpenAI 클라이언트 초기화
        try:
            self.openai_client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        except Exception as e:
            logger.warning(f"OpenAI 클라이언트 초기화 실패: {e}")
            self.openai_client = None
        
        # 공통 로거 초기화
        self.logger = logging.getLogger(f"agents.{self.name}")
        
        # 분산식 구성을 위한 설정
        self.is_running = False
        self._subscriber_task: Optional[asyncio.Task] = None
        self._background_tasks: set = set()  # 백그라운드 태스크 추적
        
        # 데이터베이스 연결 (지연 초기화)
        self.db = None
        self._db_initialized = False
        
        # 공통 세션 관리 (중복 처리 방지)
        self.processed_sessions = set()
        self.sessions_lock = asyncio.Lock()
        
        # Redis 클라이언트 (필요한 에이전트에서 사용)
        self.redis_client = None
        
        # 메트릭 수집기 (지연 초기화)
        self.metrics = None
        self._metrics_initialized = False
    
    async def initialize_database(self):
        """PostgreSQL 데이터베이스 연결 초기화"""
        if not self._db_initialized:
            try:
                # 이미 데이터베이스가 설정되어 있으면 사용
                if self.db is not None:
                    self._db_initialized = True
                    self.logger.info(f"✅ {self.name} 기존 데이터베이스 연결 사용")
                    return
                
                # 새로운 데이터베이스 연결 시도
                from database.postgres_db import get_postgres_agent_db
                self.db = await get_postgres_agent_db()
                self._db_initialized = True
                self.logger.info(f"✅ {self.name} 데이터베이스 연결 완료")
            except Exception as e:
                self.logger.error(f"❌ {self.name} 데이터베이스 연결 실패: {e}")
                self.db = None
                self._db_initialized = False
    
    async def ensure_database_connection(self):
        """데이터베이스 연결이 필요한 경우 초기화"""
        if not self._db_initialized:
            await self.initialize_database()
        return self.db is not None

    async def ensure_redis_connection(self):
        """Redis 연결이 필요한 경우 초기화"""
        if not self.redis_client:
            await self.initialize_redis()
        return self.redis_client is not None
    
    async def initialize(self):
        """에이전트 초기화 (공통 리소스 설정)"""
        try:
            self.logger.info(f"[{self.name}] 에이전트 초기화 시작")
            
            # 데이터베이스 연결 초기화
            await self.ensure_database_connection()
            
            # Redis 연결 초기화
            await self.ensure_redis_connection()
            
            # 메트릭 수집기 초기화
            await self.initialize_metrics()
            
            # 에이전트 실행 상태 설정
            self.is_running = True
            
            self.logger.info(f"[{self.name}] 에이전트 초기화 완료")
            
        except Exception as e:
            self.logger.error(f"[{self.name}] 에이전트 초기화 실패: {e}")
            raise
    
    async def initialize_metrics(self):
        """메트릭 수집기 초기화"""
        if not self._metrics_initialized:
            try:
                from core.metrics import AgentMetrics
                redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
                self.metrics = AgentMetrics(self.name, redis_url)
                await self.metrics.initialize()
                self._metrics_initialized = True
                self.logger.info(f"✅ [{self.name}] 메트릭 수집기 초기화 완료")
            except Exception as e:
                self.logger.warning(f"⚠️ [{self.name}] 메트릭 수집기 초기화 실패 (계속 진행): {e}")
                self._metrics_initialized = False
    
    async def cleanup(self):
        """에이전트 정리 (리소스 해제)"""
        try:
            self.logger.info(f"[{self.name}] 에이전트 정리 시작")
            
            # 에이전트 실행 상태 해제
            self.is_running = False
            
            # 구독자 중지
            await self.stop_subscriber()
            
            # 백그라운드 태스크 정리
            await self._cleanup_background_tasks()
            
            # 메트릭 수집기 정리
            if self.metrics:
                await self.metrics.cleanup()
            
            # Redis 연결 종료
            if self.redis_client:
                try:
                    await self.redis_client.aclose()
                except Exception as e:
                    self.logger.warning(f"Redis 클라이언트 정리 실패: {e}")
                finally:
                    self.redis_client = None
            
            self.logger.info(f"[{self.name}] 에이전트 정리 완료")
            
        except Exception as e:
            self.logger.error(f"[{self.name}] 에이전트 정리 실패: {e}")
    
    async def initialize_redis(self):
        """Redis 클라이언트 초기화 (공통 메서드)"""
        if not self.redis_client:
            try:
                import redis.asyncio as redis
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
                self.redis_client = redis.from_url(redis_url)
                await self.redis_client.ping()
                self.logger.info("✅ Redis 클라이언트 초기화 완료")
            except Exception as e:
                self.logger.error(f"❌ Redis 클라이언트 초기화 실패: {e}")
                self.redis_client = None
    
    def add_tool(self, tool: Tool):
        """도구 추가"""
        self.tools[tool.name] = tool
    
    async def think(self, context: str) -> str:
        """추론 수행 - DEPRECATED: 현재 에이전트들에서 사용하지 않음"""
        self.state = AgentState.THINKING
        
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"상황: {context}\n\n위 상황에 대해 분석하고 다음 행동을 계획하세요."}
            ]
            
            # LLMTool 사용 (프롬프트 로깅 포함)
            from .common.llm_tool import LLMTool, LLMConfig
            
            llm_tool = LLMTool(f"{self.name}_thinker")
            
            # 타임아웃 설정으로 무한 대기 방지
            try:
                result = await llm_tool.execute(
                    prompt=messages,
                    config_override=LLMConfig(
                        max_tokens=1000,
                        timeout=30
                    )
                )
                
                if result["success"]:
                    thought = result["content"]
                    self.logger.info(f"[{self.name}] 생각: {thought}")
                    return thought
                else:
                    self.logger.error(f"[{self.name}] LLM 호출 실패: {result['error']}")
                    return f"LLM 호출 실패: {result['error']}"
                
            except asyncio.TimeoutError:
                self.logger.error(f"[{self.name}] LLM 응답 타임아웃 (30초)")
                return "LLM 응답 타임아웃으로 인한 추론 실패"
            except Exception as llm_error:
                self.logger.error(f"[{self.name}] LLM 호출 오류: {llm_error}")
                return f"LLM 호출 실패: {llm_error}"
            
        except Exception as e:
            self.logger.error(f"[{self.name}] 추론 오류: {e}")
            return f"추론 중 오류 발생: {e}"
    
    async def use_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """도구 사용 - DEPRECATED: 현재 에이전트들에서 사용하지 않음"""
        if tool_name not in self.tools:
            return {"error": f"도구 '{tool_name}'을 찾을 수 없습니다.", "success": False}
        
        self.state = AgentState.ACTING
        tool = self.tools[tool_name]
        
        try:
            result = await tool.execute(**kwargs)
            self.logger.info(f"[{self.name}] 도구 '{tool_name}' 사용 결과: {result}")
            return result
        except Exception as e:
            self.logger.error(f"[{self.name}] 도구 '{tool_name}' 사용 오류: {e}")
            return {"error": str(e), "success": False}
    
    async def check_duplicate_request(self, request_id: str) -> bool:
        """중복 요청 체크 (공통 메서드)"""
        async with self.sessions_lock:
            if request_id in self.processed_sessions:
                self.logger.info(f"이미 처리된 요청 스킵: {request_id}")
                return True
            self.processed_sessions.add(request_id)
            return False
    
    @abstractmethod
    async def process_task(self, task: Task) -> Any:
        """작업 처리 (에이전트별로 구현)"""
        pass
    
    async def run_subscriber(self):
        """Redis 이벤트 구독자 실행 (분산식 구성용)"""
        self.is_running = True
        self.logger.info(f"[{self.name}] 구독자 시작")
        
        try:
            # 에이전트별 구독 채널 설정
            channels = self._get_subscription_channels()
            
            # 이벤트 핸들러 등록
            from .common.event_bus import subscribe_and_listen
            await subscribe_and_listen(channels, self._handle_event)
            
        except Exception as e:
            self.logger.error(f"[{self.name}] 구독자 실행 오류: {e}")
            self.is_running = False
    
    def _get_subscription_channels(self) -> List[str]:
        """구독할 채널 목록 반환 (에이전트별로 오버라이드)"""
        return []
    
    async def _handle_event(self, channel: str, payload: Dict[str, Any]):
        """이벤트 처리 (에이전트별로 오버라이드)"""
        self.logger.info(f"[{self.name}] 이벤트 수신: {channel}")
    
    async def process_message_parallel(self, message_type: str, payload: Dict[str, Any]):
        """메시지를 병렬로 처리하는 공통 메서드"""
        try:
            # 에이전트별 메시지 처리 메서드 호출
            if hasattr(self, 'process_message'):
                # 백그라운드 태스크로 병렬 처리
                task = asyncio.create_task(self.process_message(message_type, payload))
                self._add_background_task(task)
                self.logger.info(f"[{self.name}] 메시지 병렬 처리 시작: {message_type}")
            else:
                self.logger.warning(f"[{self.name}] process_message 메서드가 구현되지 않음")
        except Exception as e:
            self.logger.error(f"[{self.name}] 병렬 메시지 처리 오류: {e}")
    
    async def process_message(self, message_type: str, payload: Dict[str, Any]):
        """메시지 처리 메서드 (에이전트별로 오버라이드)"""
        self.logger.info(f"[{self.name}] 메시지 처리: {message_type}")
        # 기본 구현: process_task 호출
        if hasattr(self, 'process_task'):
            task = Task(
                id=payload.get('session_id', 'unknown'),
                description=payload.get('question', ''),
                metadata=payload
            )
            await self.process_task(task)
    
    async def stop_subscriber(self):
        """구독자 중지"""
        self.is_running = False
        if self._subscriber_task and not self._subscriber_task.done():
            self._subscriber_task.cancel()
            try:
                await self._subscriber_task
            except asyncio.CancelledError:
                self.logger.info(f"[{self.name}] 구독자 태스크 취소됨")
            except Exception as e:
                self.logger.warning(f"[{self.name}] 구독자 정리 중 오류: {e}")
        self.logger.info(f"[{self.name}] 구독자 중지")
    
    async def _cleanup_background_tasks(self):
        """백그라운드 태스크 정리"""
        if not self._background_tasks:
            return
            
        self.logger.info(f"[{self.name}] {len(self._background_tasks)}개 백그라운드 태스크 정리 중...")
        
        # 모든 태스크 취소
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        
        # 모든 태스크 완료 대기 (타임아웃 5초)
        if self._background_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._background_tasks, return_exceptions=True),
                    timeout=5.0
                )
                self.logger.info(f"[{self.name}] 백그라운드 태스크 정리 완료")
            except asyncio.TimeoutError:
                self.logger.warning(f"[{self.name}] 백그라운드 태스크 정리 타임아웃")
            except Exception as e:
                self.logger.warning(f"[{self.name}] 백그라운드 태스크 정리 중 오류: {e}")
        
        self._background_tasks.clear()
    
    def _add_background_task(self, task: asyncio.Task):
        """백그라운드 태스크 추가"""
        self._background_tasks.add(task)
        task.add_done_callback(self._background_tasks.discard)
    
    async def start(self):
        """에이전트 시작 (구독자 실행)"""
        try:
            self.logger.info(f"[{self.name}] 에이전트 시작")
            await self.run_subscriber()
        except Exception as e:
            self.logger.error(f"[{self.name}] 에이전트 시작 실패: {e}")
            raise
    
    async def stop(self):
        """에이전트 중지"""
        try:
            self.logger.info(f"[{self.name}] 에이전트 중지")
            await self.stop_subscriber()
        except Exception as e:
            self.logger.error(f"[{self.name}] 에이전트 중지 실패: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """에이전트 상태 반환"""
        status = {
            "name": self.name,
            "role": self.role,
            "state": self.state.value,
            "is_running": self.is_running,
            "tools_count": len(self.tools),
            "processed_sessions_count": len(self.processed_sessions),
            "database_connected": self._db_initialized,
            "redis_connected": self.redis_client is not None,
            "metrics_enabled": self._metrics_initialized
        }
        
        # 메트릭 정보 추가
        if self.metrics:
            status["metrics"] = {
                "requests_total": self.metrics.get_counter("requests_total"),
                "errors_total": self.metrics.get_counter("errors_total"),
                "active_sessions": self.metrics.get_gauge("active_sessions")
            }
        
        return status
    
    # ========== 메트릭 헬퍼 메서드 ==========
    
    def record_operation_start(self, operation: str):
        """작업 시작 기록"""
        if self.metrics:
            self.metrics.increment_counter(f"{operation}_started")
            self.metrics.set_gauge("active_sessions", len(self.processed_sessions))
    
    def record_operation_success(self, operation: str, duration: float = None):
        """작업 성공 기록"""
        if self.metrics:
            self.metrics.record_request(operation, success=True, duration=duration)
    
    def record_operation_error(self, operation: str, error_type: str = None):
        """작업 실패 기록"""
        if self.metrics:
            self.metrics.record_request(operation, success=False)
            if error_type:
                self.metrics.record_error(error_type, operation)