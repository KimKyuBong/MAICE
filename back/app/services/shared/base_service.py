"""
공통 Base Service
모든 비즈니스 서비스의 기본 클래스
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class BaseService(ABC):
    """모든 비즈니스 서비스의 기본 클래스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def __aenter__(self):
        """컨텍스트 매니저 진입"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """컨텍스트 매니저 종료"""
        if exc_type:
            await self.db_session.rollback()
            logger.error(f"❌ {self.__class__.__name__} 트랜잭션 롤백: {exc_val}")
        else:
            await self.db_session.commit()
    
    async def validate_required_fields(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """필수 필드 검증"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            raise ValueError(f"필수 필드가 누락되었습니다: {missing_fields}")
        return True
    
    async def log_operation(self, operation: str, **kwargs):
        """작업 로깅"""
        logger.info(f"💼 {operation} - {self.__class__.__name__}", extra=kwargs)
    
    def generate_request_id(self) -> str:
        """요청 ID 생성"""
        return str(uuid.uuid4())
    
    def get_current_timestamp(self) -> str:
        """현재 타임스탬프 반환"""
        return datetime.utcnow().isoformat()


class BaseCRUDService(BaseService):
    """기본 CRUD 기능을 제공하는 서비스 베이스 클래스"""
    
    @abstractmethod
    async def get_by_id(self, entity_id: int) -> Optional[Dict[str, Any]]:
        """ID로 엔티티 조회"""
        pass
    
    @abstractmethod  
    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 100, 
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """엔티티 목록 조회"""
        pass
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """엔티티 생성"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: int, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """엔티티 업데이트"""
        pass
    
    @abstractmethod  
    async def delete(self, entity_id: int) -> bool:
        """엔티티 삭제"""
        pass

