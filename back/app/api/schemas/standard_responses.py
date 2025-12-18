"""
표준화된 API 응답 스키마
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import uuid
from app.utils.timezone import get_current_kst, utc_to_kst


class BaseApiResponse(BaseModel):
    """기본 API 응답 모델"""
    success: bool = Field(..., description="성공 여부")
    message: str = Field(..., description="응답 메시지")
    data: Optional[Dict[str, Any]] = Field(None, description="응답 데이터")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class ErrorResponse(BaseModel):
    """에러 응답 모델"""
    success: bool = Field(False, description="성공 여부")
    message: str = Field(..., description="에러 메시지")
    error: Dict[str, Any] = Field(..., description="에러 정보")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class SuccessResponse(BaseModel):
    """성공 응답 모델"""
    success: bool = Field(True, description="성공 여부")
    message: str = Field(..., description="성공 메시지")
    data: Optional[Dict[str, Any]] = Field(None, description="응답 데이터")
    meta: Optional[Dict[str, Any]] = Field(None, description="메타데이터")


class PageMetaData(BaseModel):
    """페이지네이션 메타데이터"""
    total_count: int = Field(..., description="전체 항목 수")
    current_page: int = Field(..., description="현재 페이지")
    page_size: int = Field(..., description="페이지 크기") 
    total_pages: int = Field(..., description="전체 페이지 수")
    has_next: bool = Field(..., description="다음 페이지 존재 여부")
    has_prev: bool = Field(..., description="이전 페이지 존재 여부")


class ListResponseData(BaseModel):
    """목록 응답 데이터"""
    items: list = Field(..., description="데이터 목록")
    meta: PageMetaData = Field(..., description="페이지네이션 메타데이터")


class ApiMetaData(BaseModel):
    """API 메타데이터 모델"""
    timestamp: str = Field(default_factory=lambda: get_current_kst().isoformat(), description="응답 생성 시간 (KST)")
    request_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="요청 ID")
    processing_time: Optional[float] = Field(None, description="처리 시간 (초)")

    class Config:
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }
