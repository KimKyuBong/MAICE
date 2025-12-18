"""
의존성 주입 컨테이너
서비스들의 의존성을 관리하고 인스턴스를 생성합니다.
"""

import logging
from typing import Dict, Type, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from .interfaces import ISessionService, IAgentService, IChatService
from .session_repository import NewSessionService
from .streaming_processor import AIAgentService
from .conversation_orchestrator import ChatService
from app.utils.redis_client import RedisAgentClient

logger = logging.getLogger(__name__)


class DIContainer:
    """단순화된 의존성 주입 컨테이너 - 핵심 기능만 유지"""
    
    def __init__(self):
        self._services: Dict[Type, Any] = {}
        self._singletons: Dict[Type, Any] = {}
        self._db_session: Optional[AsyncSession] = None
        self._redis_client: Optional[RedisAgentClient] = None
    
    def register_database(self, db_session: AsyncSession):
        """데이터베이스 세션을 등록합니다."""
        self._db_session = db_session
        logger.info("✅ 데이터베이스 세션 등록 완료")
    
    def get_redis_client(self) -> RedisAgentClient:
        """Redis 클라이언트를 반환합니다."""
        if self._redis_client is None:
            self._redis_client = RedisAgentClient()
        return self._redis_client
    
    def register_singleton(self, interface: Type, implementation: Type):
        """싱글톤 서비스를 등록합니다."""
        self._services[interface] = implementation
        logger.info(f"✅ 싱글톤 서비스 등록: {interface.__name__} -> {implementation.__name__}")
    
    def register_transient(self, interface: Type, implementation: Type):
        """일시적 서비스를 등록합니다 (매번 새 인스턴스 생성)."""
        self._services[interface] = implementation
        logger.info(f"✅ 일시적 서비스 등록: {interface.__name__} -> {implementation.__name__}")
    
    def get(self, interface: Type) -> Any:
        """서비스 인스턴스를 반환합니다."""
        if interface not in self._services:
            raise ValueError(f"서비스가 등록되지 않았습니다: {interface.__name__}")
        
        # 싱글톤으로 등록된 경우 캐시된 인스턴스 반환
        if interface in self._singletons:
            return self._singletons[interface]
        
        # 새 인스턴스 생성
        instance = self._create_instance(self._services[interface])
        
        # 싱글톤으로 등록된 경우 캐시
        if interface in self._services and interface not in self._singletons:
            self._singletons[interface] = instance
        
        return instance
    
    def _create_instance(self, implementation: Type) -> Any:
        """서비스 인스턴스를 생성합니다."""
        if implementation == NewSessionService:
            if not self._db_session:
                raise ValueError("데이터베이스 세션이 등록되지 않았습니다.")
            return NewSessionService(self._db_session)
        
        elif implementation == AIAgentService:
            session_service = self.get(ISessionService)
            return AIAgentService(session_service)
        
        elif implementation == ChatService:
            session_service = self.get(ISessionService)
            agent_service = self.get(IAgentService)
            redis_client = self.get_redis_client()
            return ChatService(session_service, agent_service, redis_client)
        
        else:
            return implementation()
    
    async def initialize_services(self):
        """모든 서비스를 초기화합니다."""
        try:
            redis_client = self.get_redis_client()
            await redis_client.initialize()
            
            chat_service = self.get(IChatService)
            await chat_service.initialize()
            logger.info("✅ 모든 서비스 초기화 완료")
            
        except Exception as e:
            logger.error(f"❌ 서비스 초기화 실패: {e}")
            raise


# 전역 컨테이너 인스턴스
container = DIContainer()


def configure_services(db_session: AsyncSession):
    """서비스들을 구성합니다."""
    # 데이터베이스 세션 등록
    container.register_database(db_session)
    
    # 서비스 등록
    container.register_singleton(ISessionService, NewSessionService)
    container.register_singleton(IAgentService, AIAgentService)
    container.register_singleton(IChatService, ChatService)
    
    logger.info("✅ 서비스 구성 완료")


async def get_chat_service() -> IChatService:
    """ChatService 인스턴스를 가져옵니다."""
    return container.get(IChatService)


async def get_session_service() -> ISessionService:
    """SessionService 인스턴스를 가져옵니다."""
    return container.get(ISessionService)


async def get_agent_service() -> IAgentService:
    """AIAgentService 인스턴스를 가져옵니다."""
    return container.get(IAgentService)
