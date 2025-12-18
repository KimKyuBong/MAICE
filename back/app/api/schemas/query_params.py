"""
API Query Parameter 스키마
"""

from typing import Optional
from pydantic import BaseModel, Field
from app.models.models import UserRole


class UserQueryParams(BaseModel):
    """사용자 목록 조회 쿼리 파라미터"""
    role: Optional[UserRole] = Field(None, description="역할별 필터링")
    skip: int = Field(default=0, ge=0, description="건너뛸 항목 수")
    limit: int = Field(default=100, ge=1, le=1000, description="반환할 항목 수")
    search: Optional[str] = Field(None, min_length=1, max_length=100, description="사용자명 검색")


class SessionQueryParams(BaseModel):
    """세션 목록 조회 쿼리 파라미터"""
    skip: int = Field(default=0, ge=0, description="건너뛸 항목 수")
    limit: int = Field(default=50, ge=1, le=500, description="반환할 항목 수")
    is_active: Optional[bool] = Field(None, description="활성 세션만 필터링")


class QuestionQueryParams(BaseModel):
    """질문 목록 조회 쿼리 파라미터"""
    skip: int = Field(default=0, ge=0, description="건너뛸 항목 수")
    limit: int = Field(default=50, ge=1, le=500, description="반환할 항목 수")
    search: Optional[str] = Field(None, min_length=1, max_length=200, description="질문 내용 검색")
    has_answer: Optional[bool] = Field(None, description="답변 여부별 필터링")


class PaginationParams(BaseModel):
    """페이지네이션 기본 파라미터"""
    skip: int = Field(default=0, ge=0, description="건너뛸 항목 수")
    limit: int = Field(default=50, ge=1, le=1000, description="반환할 항목 수")


class FilterParams(BaseModel):
    """기본 필터링 파라미터"""
    search: Optional[str] = Field(None, min_length=1, description="검색어")
    active_only: Optional[bool] = Field(None, description="활성 상태만 필터링")

