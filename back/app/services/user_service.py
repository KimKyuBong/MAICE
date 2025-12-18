"""
사용자 비즈니스 로직 Service
사용자 관련 비즈니스 로직을 처리
"""

from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from app.repositories.user_repository import UserRepository
from app.services.shared.base_service import BaseService
from app.models.models import UserRole, UserModel
from app.schemas.schemas import UserCreate, UserUpdate
import logging

logger = logging.getLogger(__name__)


class UserService(BaseService):
    """사용자 비즈니스 로직 서비스"""
    
    def __init__(self, db_session: AsyncSession):
        super().__init__(db_session)
        self.user_repository = UserRepository(db_session)
    
    async def get_users(
        self,
        role: Optional[UserRole] = None,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """사용자 목록 조회"""
        await self.log_operation("사용자 목록 조회", role=role, skip=skip, limit=limit, search=search)
        return await self.user_repository.get_users_by_role(role, skip, limit, search)
    
    async def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 ID로 조회"""
        await self.log_operation("사용자 조회", user_id=user_id)
        return await self.user_repository.get_user_by_id(user_id)
    
    async def create_user(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """사용자 생성"""
        await self.log_operation("사용자 생성", username=user_data.get('username'))
        
        # 사용자명 중복 확인
        existing_user = await self.user_repository.get_user_by_username(user_data['username'])
        if existing_user:
            raise ValueError("이미 존재하는 사용자명입니다")
        
        # 비즈니스 로직: 학생이 아니면 max_questions 초기화
        if user_data.get('role') != UserRole.STUDENT:
            user_data['max_questions'] = None
        
        return await self.user_repository.create_user(user_data)
    
    async def update_user(self, user_id: int, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """사용자 정보 업데이트"""
        await self.log_operation("사용자 업데이트", user_id=user_id)
        
        # 사용자 존재 확인
        existing_user = await self.user_repository.get_user_by_id(user_id)
        if not existing_user:
            return None
        
        # 사용자명 변경 시 중복 확인
        if update_data.get('username') and update_data['username'] != existing_user.get('username'):
            duplicate_user = await self.user_repository.get_user_by_username(update_data['username'])
            if duplicate_user:
                raise ValueError("이미 존재하는 사용자명입니다")
        
        # 비즈니스 로직: 역할 변경 시 max_questions 처리
        if update_data.get('role') and update_data.get('role') != UserRole.STUDENT:
            update_data['max_questions'] = None
        
        return await self.user_repository.update_user(user_id, update_data)
    
    async def delete_user(self, user_id: int) -> bool:
        """사용자 삭제"""
        await self.log_operation("사용자 삭제", user_id=user_id)
        
        # 관리자 삭제 방지
        existing_user = await self.user_repository.get_user_by_id(user_id)
        if existing_user and existing_user.get('role') == UserRole.ADMIN.value:
            raise ValueError("관리자 계정은 삭제할 수 없습니다")
        
        return await self.user_repository.delete_user(user_id)
    
    async def get_user_stats(self, user_id: int) -> Optional[Dict[str, Any]]:
        """사용자 통계 조회"""
        await self.log_operation("사용자 통계 조회", user_id=user_id)
        return await self.user_repository.get_user_stats(user_id)
    
    async def get_students_with_stats(self) -> List[Dict[str, Any]]:
        """학생 통계 목록"""
        await self.log_operation("학생 통계 목록 조회")
        return await self.user_repository.get_students_with_stats()
    
    async def bulk_update_student_quota(
        self,
        grade: Optional[str] = None,
        class_num: Optional[str] = None,
        quota: int = 0,
        operation: str = 'set'
    ) -> Dict[str, int]:
        """학생 질문 한도 일괄 설정"""
        await self.log_operation("학생 한도 일괄 업데이트", grade=grade, class_num=class_num, quota=quota, operation=operation)
        
        if not quota or quota <= 0:
            raise ValueError("유효한 질문 한도를 입력해주세요")
        
        return await self.user_repository.bulk_update_student_quota(grade, class_num, quota, operation)
    
    async def update_research_consent(self, user_id: int, consent_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """연구 참여 동의 업데이트"""
        await self.log_operation("연구 동의 업데이트", user_id=user_id, consent=consent_data.get('research_consent'))
        
        # 사용자 존재 확인
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return None
        
        # 동의 데이터 처리
        update_data = {}
        if consent_data.get('research_consent'):
            # 동의하는 경우
            update_data['research_consent'] = True
            update_data['research_consent_date'] = datetime.utcnow()
            update_data['research_consent_version'] = consent_data.get('consent_version', '1.0')
            update_data['research_consent_withdrawn_at'] = None
        else:
            # 동의 철회하는 경우
            update_data['research_consent'] = False
            update_data['research_consent_withdrawn_at'] = datetime.utcnow()
        
        return await self.user_repository.update_user(user_id, update_data)
    
    async def get_research_consent_status(self, user_id: int) -> Optional[Dict[str, Any]]:
        """연구 참여 동의 상태 조회"""
        await self.log_operation("연구 동의 상태 조회", user_id=user_id)
        
        user = await self.user_repository.get_user_by_id(user_id)
        if not user:
            return None
        
        return {
            'research_consent': user.get('research_consent', False),
            'research_consent_date': user.get('research_consent_date'),
            'research_consent_version': user.get('research_consent_version'),
            'research_consent_withdrawn_at': user.get('research_consent_withdrawn_at')
        }


class UserValidationService:
    """사용자 데이터 검증 서비스"""
    
    @staticmethod
    def validate_user_create(user_data: UserCreate) -> Dict[str, Any]:
        """사용자 생성 데이터 검증"""
        data_dict = user_data.dict()
        
        # 필수 필드 검증
        required_fields = ['username', 'password', 'role']
        for field in required_fields:
            if not getattr(user_data, field, None):
                raise ValueError(f"필수 필드가 누락되었습니다: {field}")
        
        # 비밀번호 강도 검증
        if len(user_data.password) < 4:
            raise ValueError("비밀번호는 4자 이상이어야 합니다")
        
        return data_dict
    
    @staticmethod
    def validate_user_update(user_id: int, update_data: UserUpdate) -> Dict[str, Any]:
        """사용자 업데이트 데이터 검증"""
        data_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        # 사용자명 검증
        if 'username' in data_dict:
            if len(data_dict['username']) < 2:
                raise ValueError("사용자명은 2자 이상이어야 합니다")
        
        # 비밀번호 검증
        if 'password' in data_dict and data_dict['password']:
            if len(data_dict['password']) < 4:
                raise ValueError("비밀번호는 4자 이상이어야 합니다")
        
        return data_dict

