"""
Health Check 및 상태 관리 스키마
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum
from app.utils.timezone import utc_to_kst


class HealthStatus(str, Enum):
    """헬스체크 상태"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    WARNING = "warning"
    MAINTENANCE = "maintenance"


class ServiceStatus(BaseModel):
    """서비스별 상태 모델"""
    name: str = Field(..., description="서비스명")
    status: HealthStatus = Field(..., description="상태")
    message: Optional[str] = Field(None, description="상세 메시지")
    response_time: Optional[float] = Field(None, description="응답 시간 (초)")
    last_checked: datetime = Field(default_factory=datetime.utcnow, description="마지막 체크 시간")


class HealthCheckResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: HealthStatus = Field(..., description="전체 상태")
    version: str = Field(..., description="애플리케이션 버전")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="체크 시간")
    uptime_seconds: float = Field(..., description="운영 시간 (초)")
    services: List[ServiceStatus] = Field(..., description="서비스 목록")
    database_status: HealthStatus = Field(..., description="데이터베이스 상태")
    redis_status: Optional[HealthStatus] = Field(None, description="Redis 상태")
    
    class Config:
        json_encoders = {
            datetime: lambda v: utc_to_kst(v) if v else None
        }

