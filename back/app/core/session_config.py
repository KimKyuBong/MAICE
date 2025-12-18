"""
세션 관리 시스템 설정 및 초기화
다양한 세션 관리 방식을 위한 통합 설정
"""

import os
import logging
from typing import Optional, Dict, Any
from pydantic import BaseSettings, Field
from enum import Enum

logger = logging.getLogger(__name__)


class SessionBackendType(str, Enum):
    """세션 백엔드 타입"""
    DATABASE_ONLY = "database_only"
    HYBRID = "hybrid"  # Redis + PostgreSQL
    JWT_STATELESS = "jwt_stateless"
    WEBSOCKET = "websocket"


class SessionConfig(BaseSettings):
    """세션 관리 설정"""
    
    # 기본 설정
    session_backend: SessionBackendType = Field(
        default=SessionBackendType.DATABASE_ONLY,
        env="SESSION_BACKEND"
    )
    
    # Redis 설정
    redis_url: Optional[str] = Field(default=None, env="REDIS_URL")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_db: int = Field(default=0, env="REDIS_DB")
    
    # 캐시 설정
    session_cache_ttl: int = Field(default=3600, env="SESSION_CACHE_TTL")  # 1시간
    message_cache_ttl: int = Field(default=1800, env="MESSAGE_CACHE_TTL")  # 30분
    context_cache_ttl: int = Field(default=7200, env="CONTEXT_CACHE_TTL")  # 2시간
    
    # JWT 설정
    jwt_secret_key: str = Field(default="your-secret-key", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_session_expire_hours: int = Field(default=24, env="JWT_SESSION_EXPIRE_HOURS")
    jwt_context_expire_hours: int = Field(default=2, env="JWT_CONTEXT_EXPIRE_HOURS")
    
    # WebSocket 설정
    websocket_heartbeat_interval: int = Field(default=30, env="WEBSOCKET_HEARTBEAT_INTERVAL")
    websocket_max_connections: int = Field(default=1000, env="WEBSOCKET_MAX_CONNECTIONS")
    websocket_message_queue_size: int = Field(default=100, env="WEBSOCKET_MESSAGE_QUEUE_SIZE")
    
    # 성능 최적화 설정
    enable_background_tasks: bool = Field(default=True, env="ENABLE_BACKGROUND_TASKS")
    batch_update_size: int = Field(default=50, env="BATCH_UPDATE_SIZE")
    max_history_cache_size: int = Field(default=100, env="MAX_HISTORY_CACHE_SIZE")
    
    # 분석 및 모니터링 설정
    enable_session_analytics: bool = Field(default=True, env="ENABLE_SESSION_ANALYTICS")
    analytics_retention_days: int = Field(default=90, env="ANALYTICS_RETENTION_DAYS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# 전역 설정 인스턴스
session_config = SessionConfig()


def get_session_config() -> SessionConfig:
    """세션 설정 반환"""
    return session_config


def validate_session_config() -> Dict[str, Any]:
    """세션 설정 검증 및 상태 반환"""
    config = get_session_config()
    status = {
        "backend_type": config.session_backend,
        "features": {
            "caching": False,
            "websocket": False,
            "jwt_tokens": False,
            "analytics": config.enable_session_analytics,
            "background_tasks": config.enable_background_tasks
        },
        "warnings": [],
        "errors": []
    }
    
    # Redis 설정 검증
    if config.session_backend in [SessionBackendType.HYBRID, SessionBackendType.WEBSOCKET]:
        if not config.redis_url:
            status["errors"].append("Redis URL이 설정되지 않았습니다")
        else:
            status["features"]["caching"] = True
    
    # JWT 설정 검증
    if config.session_backend == SessionBackendType.JWT_STATELESS:
        if config.jwt_secret_key == "your-secret-key":
            status["warnings"].append("기본 JWT 시크릿 키를 사용하고 있습니다. 보안을 위해 변경해주세요")
        status["features"]["jwt_tokens"] = True
    
    # WebSocket 설정 검증
    if config.session_backend == SessionBackendType.WEBSOCKET:
        if not config.redis_url:
            status["errors"].append("WebSocket 모드에는 Redis가 필요합니다")
        else:
            status["features"]["websocket"] = True
    
    return status


def log_session_config():
    """세션 설정을 로그로 출력"""
    config = get_session_config()
    validation = validate_session_config()
    
    logger.info("🔧 세션 관리 시스템 설정:")
    logger.info(f"  - 백엔드 타입: {config.session_backend}")
    logger.info(f"  - Redis URL: {'설정됨' if config.redis_url else '설정되지 않음'}")
    logger.info(f"  - 캐싱 활성화: {validation['features']['caching']}")
    logger.info(f"  - WebSocket 활성화: {validation['features']['websocket']}")
    logger.info(f"  - JWT 토큰 활성화: {validation['features']['jwt_tokens']}")
    logger.info(f"  - 분석 활성화: {validation['features']['analytics']}")
    logger.info(f"  - 백그라운드 태스크: {validation['features']['background_tasks']}")
    
    # 경고 및 오류 출력
    for warning in validation["warnings"]:
        logger.warning(f"⚠️ {warning}")
    
    for error in validation["errors"]:
        logger.error(f"❌ {error}")
    
    return validation


# 환경별 설정 프리셋
PRESET_CONFIGS = {
    "development": {
        "session_backend": SessionBackendType.DATABASE_ONLY,
        "enable_background_tasks": False,
        "enable_session_analytics": False,
        "redis_url": None
    },
    "testing": {
        "session_backend": SessionBackendType.DATABASE_ONLY,
        "enable_background_tasks": False,
        "enable_session_analytics": False,
        "redis_url": None,
        "session_cache_ttl": 60,  # 짧은 TTL
        "message_cache_ttl": 30
    },
    "staging": {
        "session_backend": SessionBackendType.HYBRID,
        "enable_background_tasks": True,
        "enable_session_analytics": True,
        "redis_url": "redis://redis-staging:6379"
    },
    "production": {
        "session_backend": SessionBackendType.HYBRID,
        "enable_background_tasks": True,
        "enable_session_analytics": True,
        "redis_url": "redis://redis-prod:6379",
        "websocket_max_connections": 5000,
        "batch_update_size": 100
    }
}


def apply_preset_config(preset: str):
    """프리셋 설정 적용"""
    if preset not in PRESET_CONFIGS:
        raise ValueError(f"알 수 없는 프리셋: {preset}")
    
    preset_config = PRESET_CONFIGS[preset]
    
    # 환경 변수로 설정 적용
    for key, value in preset_config.items():
        if value is not None:
            os.environ[key.upper()] = str(value)
    
    logger.info(f"✅ '{preset}' 프리셋 설정이 적용되었습니다")
    
    # 설정 재로드
    global session_config
    session_config = SessionConfig()
    
    return session_config


def get_recommended_config(
    user_count: int, 
    concurrent_sessions: int, 
    message_volume_per_day: int
) -> Dict[str, Any]:
    """사용량 기반 권장 설정"""
    
    recommendations = {
        "backend_type": SessionBackendType.DATABASE_ONLY,
        "features": [],
        "settings": {},
        "reasoning": []
    }
    
    # 소규모 (< 100 사용자)
    if user_count < 100:
        recommendations["backend_type"] = SessionBackendType.DATABASE_ONLY
        recommendations["reasoning"].append("소규모 사용자 기반으로 데이터베이스만 사용")
        
    # 중간 규모 (100-1000 사용자)
    elif user_count < 1000:
        recommendations["backend_type"] = SessionBackendType.HYBRID
        recommendations["features"].append("Redis 캐싱")
        recommendations["settings"]["session_cache_ttl"] = 1800  # 30분
        recommendations["reasoning"].append("중간 규모로 Redis 캐싱 권장")
        
    # 대규모 (1000+ 사용자)
    else:
        recommendations["backend_type"] = SessionBackendType.HYBRID
        recommendations["features"].extend(["Redis 캐싱", "WebSocket", "배치 처리"])
        recommendations["settings"]["session_cache_ttl"] = 3600  # 1시간
        recommendations["settings"]["batch_update_size"] = 100
        recommendations["reasoning"].append("대규모로 전체 기능 활성화 권장")
    
    # 높은 동시 접속 (> 100)
    if concurrent_sessions > 100:
        recommendations["features"].append("WebSocket 실시간 통신")
        recommendations["settings"]["websocket_max_connections"] = concurrent_sessions * 2
        recommendations["reasoning"].append("높은 동시 접속으로 WebSocket 권장")
    
    # 높은 메시지 볼륨 (> 10000/일)
    if message_volume_per_day > 10000:
        recommendations["features"].append("백그라운드 처리")
        recommendations["features"].append("배치 업데이트")
        recommendations["settings"]["enable_background_tasks"] = True
        recommendations["reasoning"].append("높은 메시지 볼륨으로 백그라운드 처리 권장")
    
    return recommendations
