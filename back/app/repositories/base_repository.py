"""
공통 Base Repository  
모든 Repository의 기본 클래스
"""

from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.orm import DeclarativeBase
import logging

logger = logging.getLogger(__name__)


class BaseRepository(ABC):
    """모든 Repository의 기본 클래스"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """쿼리 실행 및 결과 반환"""
        try:
            result = await self.db_session.execute(text(query), params or {})
            return result.fetchall()
        except Exception as e:
            logger.error(f"❌ 쿼리 실행 실패: {query[:100]}... - {str(e)}")
            raise
    
    async def execute_scalar(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """스칼라 쿼리 실행"""
        try:
            result = await self.db_session.execute(text(query), params or {})
            return result.scalar()
        except Exception as e:
            logger.error(f"❌ 스칼라 쿼리 실행 실패: {query[:100]}... - {str(e)}")
            raise
    
    def log_query_execution(self, query_type: str, table: str, **kwargs):
        """쿼리 실행 로깅"""
        logger.debug(f"📝 {query_type} 실행 - {table}", extra=kwargs)
    
    def create_where_clause(self, filters: Dict[str, Any]) -> tuple:
        """WHERE 절 생성"""
        if not filters:
            return "", {}
        
        conditions = []
        params = {}
        
        for key, value in filters.items():
            if value is not None:
                if isinstance(value, str):
                    conditions.append(f"{key} ILIKE :{key}")
                    params[key] = f"%{value}%"
                elif isinstance(value, list):
                    conditions.append(f"{key} IN :{key}")
                    params[key] = value
                else:
                    conditions.append(f"{key} = :{key}")
                    params[key] = value
        
        where_clause = " AND ".join(conditions) if conditions else ""
        return where_clause, params
    
    async def check_soft_delete_column(self, table_name: str) -> bool:
        """소프트 삭제 컬럼 존재 확인"""
        query = """
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = 'deleted_at'
        """
        result = await self.execute_scalar(query, {"table_name": table_name})
        return bool(result)


class BaseEntityRepository(BaseRepository):
    """특정 엔티티 대상 Repository 베이스 클래스"""
    
    def __init__(self, db_session: AsyncSession, entity_model: type):
        super().__init__(db_session)
        self.entity_model = entity_model
    
    async def get_by_id(self, entity_id: int, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
        """ID로 엔티티 조회"""
        try:
            query = self.db_session.query(self.entity_model)
            if hasattr(self.entity_model, 'deleted_at') and not include_deleted:
                query = query.filter(getattr(self.entity_model, 'deleted_at').is_(None))
            
            entity = await query.filter(self.entity_model.id == entity_id).first()
            return self._entity_to_dict(entity) if entity else None
            
        except Exception as e:
            logger.error(f"❌ 엔티티 조회 실패 (ID: {entity_id}): {str(e)}")
            raise
    
    async def get_list(
        self, 
        skip: int = 0, 
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        include_deleted: bool = False
    ) -> List[Dict[str, Any]]:
        """엔티티 목록 조회"""
        try:
            query = self.db_session.query(self.entity_model)
            
            # 소프트 삭제 필터링
            if hasattr(self.entity_model, 'deleted_at') and not include_deleted:
                query = query.filter(getattr(self.entity_model, 'deleted_at').is_(None))
            
            # 필터 적용
            if filters:
                for key, value in filters.items():
                    if hasattr(self.entity_model, key) and value is not None:
                        if isinstance(value, str):
                            column = getattr(self.entity_model, key)
                            query = query.filter(column.ilike(f"%{value}%"))
                        else:
                            query = query.filter(getattr(self.entity_model, key) == value)
            
            # 정렬
            if order_by and hasattr(self.entity_model, order_by.strip('-').strip('+')):
                if order_by.startswith('-'):
                    column = getattr(self.entity_model, order_by[1:])
                    query = query.order_by(column.desc())
                elif order_by.startswith('+'):
                    column = getattr(self.entity_model, order_by[1:])
                    query = query.order_by(column.asc())
                else:
                    column = getattr(self.entity_model, order_by)
                    query = query.order_by(column.asc())
            
            # 페이지네이션
            entities = query.offset(skip).limit(limit).all()
            return [self._entity_to_dict(entity) for entity in entities]
            
        except Exception as e:
            logger.error(f"❌ 엔티티 목록 조회 실패: {str(e)}")
            raise
    
    def _entity_to_dict(self, entity) -> Optional[Dict[str, Any]]:
        """엔티티를 딕셔너리로 변환"""
        if not entity:
            return None
        
        try:
            return {
                column.name: getattr(entity, column.name)
                for column in entity.__table__.columns
                if getattr(entity, column.name, None) is not None
            }
        except Exception as e:
            logger.error(f"❌ 엔티티 변환 실패: {str(e)}")
            return None

