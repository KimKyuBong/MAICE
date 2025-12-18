"""
MAICE API Controller
MAICE 관련 API 엔드포인트를 처리하는 계층화된 구조
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status, UploadFile, File
from fastapi.responses import StreamingResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict, Any, List
import logging
from app.utils.timezone import get_current_kst

from app.core.db.session import get_db
from app.core.auth.dependencies import get_current_user
from app.services.maice_service import MaiceService
from app.services.image_to_latex_service import ImageToLatexService
from app.api.controllers.base_controller import BaseController
from app.api.schemas.error_codes import ApiErrorCode
from app.api.schemas.maice_requests import ChatRequest, SessionRequest
from app.schemas.schemas import User, SSEErrorMessage
import json

logger = logging.getLogger(__name__)
router = APIRouter(tags=["MAICE"])


async def get_maice_service(db: AsyncSession = Depends(get_db)) -> MaiceService:
    """MaiceService 의존성 주입"""
    return MaiceService(db)


async def get_image_to_latex_service() -> ImageToLatexService:
    """ImageToLatexService 의존성 주입"""
    return ImageToLatexService()


@router.post("/chat")
async def chat_with_maice_stream(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    MAICE 채팅 API - 통합된 질문 처리 (사용자별 랜덤 모드 할당)
    
    - 질문 분류, 명료화, 답변 생성을 통합 처리
    - SSE 스트리밍으로 실시간 응답 제공
    - 표준화된 응답 형식 사용
    - 사용자별 자동 모드 할당 (agent/freepass)
    """
    try:
        # 현재 사용자가 RedirectResponse인 경우 처리
        if hasattr(current_user, 'status_code') and current_user.status_code == 302:
            return current_user
        
        BaseController.log_request("MAICE 채팅", current_user.id, message=request.message[:50])
        
        # 스트리밍 채팅 처리
        maice_service = MaiceService(db)
        stream_generator = maice_service.process_chat_streaming(
            question=request.message,
            user_id=current_user.id,
            session_id=request.session_id,
            message_type=request.message_type,
            conversation_history=request.conversation_history
        )
        
        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "X-Accel-Buffering": "no",
            }
        )
        
    except Exception as e:
        error = BaseController.handle_exception(e, "MAICE 채팅", "채팅 처리 중 오류가 발생했습니다")
        raise error


@router.post("/chat-test")
async def test_chat_with_maice_stream(
    request: ChatRequest,
    user_id: int = 13,  # 테스트용 사용자 ID (기본값 13)
    db: AsyncSession = Depends(get_db)
):
    """
    테스트용 MAICE 채팅 API - 실제 운영 환경과 동일한 로직 (인증만 제외)
    """
    try:
        BaseController.log_request("테스트 MAICE 채팅", user_id, message=request.message[:50])
        
        # 디버깅: 요청 데이터 로깅
        logger.info(f"🔍 테스트 채팅 요청 데이터: session_id={request.session_id}, message_type={request.message_type}, conversation_history_length={len(request.conversation_history) if request.conversation_history else 0}")
        
        # 스트리밍 채팅 처리
        maice_service = MaiceService(db)
        stream_generator = maice_service.process_test_chat_streaming(
            question=request.message,
            user_id=user_id,
            session_id=request.session_id,
            message_type=request.message_type,
            conversation_history=request.conversation_history
        )
        
        return StreamingResponse(
            stream_generator,
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "*"
            }
        )
        
    except Exception as e:
        error_msg = SSEErrorMessage(
            message=f"테스트 처리 중 오류가 발생했습니다: {str(e)}"
        )
        return f"data: {error_msg.model_dump_json()}\n\n"


@router.get("/sessions")
async def get_sessions(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """사용자의 세션 목록 조회 API"""
    try:
        # RedirectResponse인 경우 인증 실패로 처리
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다."
            )
        
        BaseController.log_request("세션 목록 조회", current_user.id)
        
        maice_service = MaiceService(db)
        sessions = await maice_service.get_user_sessions(current_user.id)
        response = BaseController.create_success_response(
            data={"sessions": sessions, "total_count": len(sessions)},
            message="세션 목록을 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("세션 목록 조회", True, session_count=len(sessions))
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "세션 목록 조회", "세션 목록 조회 중 오류가 발생했습니다")
        raise error


@router.get("/sessions-test")
async def get_sessions_test(
    user_id: int = 13,  # 테스트용 사용자 ID (기본값 13)
    db: AsyncSession = Depends(get_db)
):
    """테스트용 세션 목록 조회 API - 인증 없이 지정된 사용자의 세션 조회"""
    try:
        BaseController.log_request("테스트 세션 목록 조회", user_id)
        
        maice_service = MaiceService(db)
        sessions = await maice_service.get_user_sessions(user_id)
        response = BaseController.create_success_response(
            data={"sessions": sessions, "total_count": len(sessions)},
            message="테스트 세션 목록을 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("테스트 세션 목록 조회", True, session_count=len(sessions))
        return response
        
    except Exception as e:
        error = BaseController.handle_exception(e, "테스트 세션 목록 조회", "테스트 세션 목록 조회 중 오류가 발생했습니다")
        raise error


@router.post("/sessions")
async def create_session(
    request: SessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """새 채팅 세션 생성 API"""
    try:
        BaseController.log_request("세션 생성", current_user.id)
        
        maice_service = MaiceService(db)
        session_id = await maice_service.create_new_session(
            user_id=current_user.id,
            initial_question=request.initial_question
        )
        
        response_data = {
            "type": "session_created",
            "session_id": session_id,
            "message": "새 세션이 성공적으로 생성되었습니다"
        }
        
        if request.initial_question:
            response_data.update({
                "initial_question": request.initial_question,
                "processing_started": True
            })
        
        response = BaseController.create_success_response(response_data, session_id)
        BaseController.log_response("세션 생성", True, session_id=session_id)
        return response
        
    except Exception as e:
        error = BaseController.handle_exception(e, "세션 생성", "세션 생성 중 오류가 발생했습니다")
        raise error


@router.get("/sessions/{session_id}")
async def get_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 정보 조회 API"""
    try:
        BaseController.log_request("세션 조회", current_user.id, session_id=session_id)
        
        maice_service = MaiceService(db)
        session_info = await maice_service.get_session_info(session_id)
        if not session_info:
            raise BaseController.create_error_response(
                ApiErrorCode.SESSION_NOT_FOUND.value,
                "세션을 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        response = BaseController.create_success_response(
            data={"type": "session_info", "session": session_info},
            message="세션 정보를 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("세션 조회", True, session_id=session_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "세션 조회", "세션 조회 중 오류가 발생했습니다")
        raise error


@router.get("/sessions/{session_id}/history")
async def get_session_history(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 대화 기록 조회 API"""
    try:
        BaseController.log_request("세션 대화 기록 조회", current_user.id, session_id=session_id)
        
        maice_service = MaiceService(db)
        history = await maice_service.get_session_history(session_id)
        
        response = BaseController.create_success_response(
            data={"type": "session_history", "history": history},
            message="세션 대화 기록을 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("세션 대화 기록 조회", True, session_id=session_id)
        return response
        
    except Exception as e:
        error = BaseController.handle_exception(e, "세션 대화 기록 조회", "세션 대화 기록 조회 중 오류가 발생했습니다")
        raise error


@router.get("/sessions-test/{session_id}/history")
async def get_session_history_test(
    session_id: int,
    user_id: int = 13,  # 테스트용 사용자 ID (기본값 13)
    db: AsyncSession = Depends(get_db)
):
    """테스트용 세션 대화 기록 조회 API - 인증 없이 지정된 사용자의 세션 기록 조회"""
    try:
        BaseController.log_request("테스트 세션 대화 기록 조회", user_id, session_id=session_id)
        
        maice_service = MaiceService(db)
        history = await maice_service.get_session_history(session_id)
        
        response = BaseController.create_success_response(
            data={"type": "session_history", "history": history},
            message="테스트 세션 대화 기록을 성공적으로 조회했습니다"
        )
        
        BaseController.log_response("테스트 세션 대화 기록 조회", True, session_id=session_id)
        return response
        
    except Exception as e:
        error = BaseController.handle_exception(e, "테스트 세션 대화 기록 조회", "테스트 세션 대화 기록 조회 중 오류가 발생했습니다")
        raise error


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """세션 삭제 API"""
    try:
        BaseController.log_request("세션 삭제", current_user.id, session_id=session_id)
        
        maice_service = MaiceService(db)
        success = await maice_service.delete_session(session_id, current_user.id)
        if not success:
            raise BaseController.create_error_response(
                ApiErrorCode.SESSION_NOT_FOUND.value,
                "세션을 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        response = BaseController.create_success_response(
            data={"type": "session_deleted", "message": "세션이 성공적으로 삭제되었습니다"}
        )
        
        BaseController.log_response("세션 삭제", True, session_id=session_id)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "세션 삭제", "세션 삭제 중 오류가 발생했습니다")
        raise error


@router.post("/convert-image-to-latex")
async def convert_image_to_latex(
    image: UploadFile = File(..., description="수학 공식이 포함된 이미지 파일"),
    current_user: User = Depends(get_current_user),
    image_service: ImageToLatexService = Depends(get_image_to_latex_service)
):
    """
    이미지 → LaTeX 변환 API
    Gemini Vision API를 사용하여 이미지에서 수학 공식을 LaTeX로 변환
    
    Args:
        image: 업로드된 이미지 파일 (JPG, PNG, WebP 지원)
        current_user: 현재 로그인한 사용자
        image_service: 이미지 변환 서비스
        
    Returns:
        dict: 변환된 LaTeX 문자열과 메타데이터
    """
    try:
        # RedirectResponse인 경우 인증 실패로 처리
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다."
            )
        
        logger.info(f"이미지 변환 요청 시작 - 사용자: {current_user.id}, 파일명: {image.filename}, 크기: {image.size}")
        BaseController.log_request("이미지 → LaTeX 변환", current_user.id, filename=image.filename)
        
        # 이미지 → LaTeX 변환
        latex_result = await image_service.convert_image_to_latex(image)
        
        # 응답 데이터 구성
        response_data = {
            "type": "image_to_latex_conversion",
            "latex": latex_result,
            "filename": image.filename,
            "file_size": image.size,
            "content_type": image.content_type,
            "success": True
        }
        
        response = BaseController.create_success_response(
            data=response_data,
            message="이미지가 성공적으로 LaTeX로 변환되었습니다"
        )
        
        BaseController.log_response("이미지 → LaTeX 변환", True, latex_length=len(latex_result))
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "이미지 → LaTeX 변환", "이미지 변환 중 오류가 발생했습니다")
        raise error


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """MAICE 서비스 헬스 체크"""
    try:
        import redis.asyncio as redis
        import os
        
        BaseController.log_request("헬스 체크")
        
        # API 서버 상태
        api_status = "healthy"
        
        # 데이터베이스 상태 확인
        database_status = "healthy"
        try:
            await db.execute(select(func.count()).select_from(UserModel))
        except Exception as e:
            logger.error(f"데이터베이스 헬스 체크 실패: {e}")
            database_status = "unhealthy"
        
        # Redis 상태 확인
        redis_status = "healthy"
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            redis_client = await redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
        except Exception as e:
            logger.error(f"Redis 헬스 체크 실패: {e}")
            redis_status = "unhealthy"
        
        # 전체 상태 결정
        overall_status = "healthy" if all([
            api_status == "healthy",
            database_status == "healthy", 
            redis_status == "healthy"
        ]) else "degraded"
        
        health_data = {
            "type": "health_check",
            "status": overall_status,
            "api_status": api_status,
            "database_status": database_status,
            "redis_status": redis_status,
            "timestamp": get_current_kst().isoformat()
        }
        
        response = BaseController.create_success_response(
            data=health_data,
            message="MAICE 서비스가 정상적으로 작동하고 있습니다"
        )
        
        BaseController.log_response("헬스 체크", True)
        return response
        
    except Exception as e:
        error = BaseController.handle_exception(e, "헬스 체크", "서비스 상태 확인 중 오류가 발생했습니다")
        raise error
