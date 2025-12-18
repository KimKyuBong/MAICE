"""
공통 Base Controller
모든 API 컨트롤러의 기본 클래스
"""

from typing import Dict, Any, Optional
from fastapi import HTTPException, status
from datetime import datetime
import uuid
import logging
from app.utils.timezone import get_current_kst

logger = logging.getLogger(__name__)


class BaseController:
    """모든 API 컨트롤러의 기본 클래스"""
    
    @staticmethod
    def create_success_response(
        data: Dict[str, Any], 
        message: str = "Success",
        meta: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """표준화된 성공 응답 생성"""
        return {
            "success": True,
            "message": message,
            "data": data,
            "meta": meta or {
                "timestamp": get_current_kst().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        }
    
    @staticmethod
    def create_error_response(
        error_code: str,
        error_message: str,
        details: Optional[Dict[str, Any]] = None,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    ) -> HTTPException:
        """표준화된 에러 응답 생성"""
        error_data = {
            "success": False,
            "error": {
                "code": error_code,
                "message": error_message,
                "details": details
            },
            "meta": {
                "timestamp": get_current_kst().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        }
        return HTTPException(status_code=status_code, detail=error_data)
    
    @staticmethod
    def handle_exception(
        e: Exception,
        operation: str,
        default_message: str = "처리 중 오류가 발생했습니다"
    ) -> HTTPException:
        """표준화된 예외 처리"""
        logger.error(f"❌ {operation} 중 오류 발생: {str(e)}", exc_info=True)
        
        # 특정 예외 타입별 처리
        if isinstance(e, HTTPException):
            return e
        
        # 공통 에러 코드별 메시지 매핑
        error_mapping = {
            "not_found": ("NOT_FOUND_001", "요청한 리소스를 찾을 수 없습니다"),
            "validation_error": ("VALIDATION_001", "입력 데이터가 유효하지 않습니다"),
            "permission_denied": ("AUTH_001", "권한이 없습니다"),
            "conflict": ("CONFLICT_001", "이미 존재하는 리소스입니다"),
            "internal_error": ("INTERNAL_001", default_message)
        }
        
        error_code, error_message = error_mapping.get(
            getattr(e, 'error_type', 'internal_error'), 
            error_mapping['internal_error']
        )
        
        return BaseController.create_error_response(
            error_code=error_code,
            error_message=error_message,
            details={"original_error": str(e)} if logger.isEnabledFor(logging.DEBUG) else None
        )
    
    @staticmethod
    def log_request(operation: str, user_id: Optional[int] = None, **kwargs):
        """요청 로깅"""
        # LogRecord 예약어를 피하기 위해 safe 키로 변환
        reserved_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
            'filename', 'module', 'lineno', 'funcName', 'created', 
            'msecs', 'relativeCreated', 'thread', 'threadName', 
            'processName', 'process', 'getMessage', 'exc_info', 
            'exc_text', 'stack_info', 'message', 'asctime'
        }
        
        safe_kwargs = {}
        for key, value in kwargs.items():
            # 예약어 충돌 방지
            if key in reserved_fields:
                safe_key = f"request_{key}"
            else:
                safe_key = key
            safe_kwargs[safe_key] = value
        
        base_msg = f"🚀 {operation} 시작"
        if user_id:
            base_msg += f" - user_id: {user_id}"
        
        logger.info(base_msg, extra=safe_kwargs)
    
    @staticmethod  
    def log_response(operation: str, success: bool, **kwargs):
        """응답 로깅"""
        # LogRecord 예약어를 피하기 위해 safe 키로 변환
        reserved_fields = {
            'name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
            'filename', 'module', 'lineno', 'funcName', 'created', 
            'msecs', 'relativeCreated', 'thread', 'threadName', 
            'processName', 'process', 'getMessage', 'exc_info', 
            'exc_text', 'stack_info', 'message', 'asctime'
        }
        
        safe_kwargs = {}
        for key, value in kwargs.items():
            # 예약어 충돌 방지
            if key in reserved_fields:
                safe_key = f"response_{key}"
            else:
                safe_key = key
            safe_kwargs[safe_key] = value
        
        emoji = "✅" if success else "❌"
        response_msg = f"{emoji} {operation} 완료"
        if not success:
            response_msg += f" - success: {success}"
        
        logger.info(response_msg, extra=safe_kwargs)
