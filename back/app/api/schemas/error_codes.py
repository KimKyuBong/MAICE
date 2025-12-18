"""
표준화된 에러 코드 상수
"""

from enum import Enum


class ApiErrorCode(Enum):
    """API 에러 코드 정의"""
    
    # 인증/인가 관련 에러 (AUTH_xxx)
    UNAUTHORIZED = "AUTH_001"
    TOKEN_EXPIRED = "AUTH_002" 
    TOKEN_INVALID = "AUTH_003"
    PERMISSION_DENIED = "AUTH_004"
    INVALID_CREDENTIALS = "AUTH_005"
    
    # 입력 데이터 관련 에러 (VALIDATION_xxx)
    VALIDATION_ERROR = "VALIDATION_001"
    REQUIRED_FIELD_MISSING = "VALIDATION_002"
    INVALID_FIELD_FORMAT = "VALIDATION_003"
    FIELD_TOO_LONG = "VALIDATION_004"
    FIELD_TOO_SHORT = "VALIDATION_005"
    
    # 리소스 관련 에러 (RESOURCE_xxx)
    NOT_FOUND = "RESOURCE_001"
    ALREADY_EXISTS = "RESOURCE_002"
    RESOURCE_CONFLICT = "RESOURCE_003"
    RESOURCE_LOCKED = "RESOURCE_004"
    
    # 비즈니스 로직 관련 에러 (BUSINESS_xxx)
    BUSINESS_RULE_VIOLATION = "BUSINESS_001"
    QUOTA_EXCEEDED = "BUSINESS_002"
    OPERATION_NOT_ALLOWED = "BUSINESS_003"
    INVALID_OPERATION = "BUSINESS_004"
    
    # 시스템 관련 에러 (SYSTEM_xxx)
    INTERNAL_ERROR = "SYSTEM_001"
    SERVICE_UNAVAILABLE = "SYSTEM_002"
    DATABASE_ERROR = "SYSTEM_003"
    EXTERNAL_SERVICE_ERROR = "SYSTEM_004"
    TIMEOUT_ERROR = "SYSTEM_005"
    
    # MAICE 특화 에러 (MAICE_xxx)
    SESSION_NOT_FOUND = "MAICE_001"
    SESSION_EXPIRED = "MAICE_002"
    CHAT_INVALID = "MAICE_003"
    AGENT_SERVICE_UNAVAILABLE = "MAICE_004"
    CONVERSATION_LIMIT_EXCEEDED = "MAICE_005"


class ErrorMessages:
    """에러 메시지 상수"""
    
    ERROR_MESSAGE_MAPPING = {
        ApiErrorCode.UNAUTHORIZED: "인증이 필요합니다",
        ApiErrorCode.TOKEN_EXPIRED: "토큰이 만료되었습니다",
        ApiErrorCode.TOKEN_INVALID: "유효하지 않은 토큰입니다",
        ApiErrorCode.PERMISSION_DENIED: "권한이 없습니다",
        ApiErrorCode.INVALID_CREDENTIALS: "인증 정보가 올바르지 않습니다",
        
        ApiErrorCode.VALIDATION_ERROR: "입력 데이터가 유효하지 않습니다",
        ApiErrorCode.REQUIRED_FIELD_MISSING: "필수 필드가 누락되었습니다",
        ApiErrorCode.INVALID_FIELD_FORMAT: "필드 형식이 올바르지 않습니다",
        ApiErrorCode.FIELD_TOO_LONG: "필드가 최대 길이를 초과했습니다",
        ApiErrorCode.FIELD_TOO_SHORT: "필드가 최소 길이에 미달합니다",
        
        ApiErrorCode.NOT_FOUND: "요청한 리소스를 찾을 수 없습니다",
        ApiErrorCode.ALREADY_EXISTS: "이미 존재하는 리소스입니다",
        ApiErrorCode.RESOURCE_CONFLICT: "리소스 충돌이 발생했습니다",
        ApiErrorCode.RESOURCE_LOCKED: "리소스가 잠겨있습니다",
        
        ApiErrorCode.BUSINESS_RULE_VIOLATION: "비즈니스 규칙을 위반했습니다",
        ApiErrorCode.QUOTA_EXCEEDED: "사용 한도를 초과했습니다",
        ApiErrorCode.OPERATION_NOT_ALLOWED: "허용되지 않는 작업입니다",
        ApiErrorCode.INVALID_OPERATION: "유효하지 않은 작업입니다",
        
        ApiErrorCode.INTERNAL_ERROR: "내부 서버 오류가 발생했습니다",
        ApiErrorCode.SERVICE_UNAVAILABLE: "서비스를 이용할 수 없습니다",
        ApiErrorCode.DATABASE_ERROR: "데이터베이스 오류가 발생했습니다",
        ApiErrorCode.EXTERNAL_SERVICE_ERROR: "외부 서비스 오류가 발생했습니다",
        ApiErrorCode.TIMEOUT_ERROR: "요청 시간이 초과되었습니다",
        
        ApiErrorCode.SESSION_NOT_FOUND: "세션을 찾을 수 없습니다",
        ApiErrorCode.SESSION_EXPIRED: "세션이 만료되었습니다",
        ApiErrorCode.CHAT_INVALID: "유효하지 않은 채팅입니다",
        ApiErrorCode.AGENT_SERVICE_UNAVAILABLE: "AI 에이전트 서비스를 이용할 수 없습니다",
        ApiErrorCode.CONVERSATION_LIMIT_EXCEEDED: "대화 한도를 초과했습니다",
    }
    
    @classmethod
    def get_message(cls, error_code: ApiErrorCode, default_message: str = "알 수 없는 오류가 발생했습니다") -> str:
        """에러 코드에 해당하는 메시지 반환"""
        return cls.ERROR_MESSAGE_MAPPING.get(error_code, default_message)
