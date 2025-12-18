"""
Authentication API Controller
인증 관련 API 엔드포인트를 처리하는 계층화된 구조
"""

from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import logging
from typing import Optional

from app.models.models import UserModel, UserRole
from app.schemas.schemas import Token, User, ResearchConsentUpdate, ResearchConsentResponse
from app.core.db.session import get_db
from app.core.auth.handlers import login_user, logout_user
from app.core.auth.dependencies import get_current_user, get_current_admin, get_current_teacher
from app.api.controllers.base_controller import BaseController
from app.api.schemas.error_codes import ApiErrorCode
from app.services.user_service import UserService

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """일반 로그인 API - Google OAuth만 지원하므로 비활성화"""
    try:
        BaseController.log_request("로그인 시도", message="일반 로그인 비활성화됨")
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="일반 로그인은 더 이상 지원되지 않습니다. Google OAuth를 사용해주세요."
        )
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "로그인", "인증 처리 중 오류가 발생했습니다")
        raise error


@router.post("/logout")
async def logout(request: Request):
    """사용자 로그아웃 API"""
    try:
        BaseController.log_request("로그아웃")
        response = await logout_user(request)
        result = {"message": "로그아웃되었습니다."}
        
        BaseController.log_response("로그아웃", True)
        return result
        
    except Exception as e:
        BaseController.log_response("로그아웃", False, error=str(e))
        error = BaseController.handle_exception(e, "로그아웃", "로그아웃 처리 중 오류가 발생했습니다")
        raise error


@router.get("/me")
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_user)
):
    """현재 로그인한 사용자 정보 조회"""
    try:
        BaseController.log_request("사용자 정보 조회", current_user.id)
        
        user_info = {
            "id": current_user.id,
            "username": current_user.username,
            "role": current_user.role.value,
            "email": current_user.google_email,  # google_email 사용
            "name": current_user.google_name,  # google_name 사용
            "google_id": current_user.google_id,
            "google_email": current_user.google_email,
            "google_name": current_user.google_name,
            "google_picture": current_user.google_picture,
            "google_verified_email": current_user.google_verified_email,
            # 연구 동의 정보 추가
            "research_consent": current_user.research_consent,
            "research_consent_date": current_user.research_consent_date.isoformat() if current_user.research_consent_date else None,
            "research_consent_version": current_user.research_consent_version,
            "research_consent_withdrawn_at": current_user.research_consent_withdrawn_at.isoformat() if current_user.research_consent_withdrawn_at else None
        }
        
        BaseController.log_response("사용자 정보 조회", True)
        return user_info
        
    except Exception as e:
        error = BaseController.handle_exception(e, "사용자 정보 조회", "사용자 정보 조회 중 오류가 발생했습니다")
        raise error


@router.get("/admin/me", response_model=User)
async def get_current_admin_info(
    current_user: UserModel = Depends(get_current_admin)
):
    """현재 로그인한 관리자 정보 조회"""
    try:
        BaseController.log_request("관리자 정보 조회", current_user.id)
        
        BaseController.log_response("관리자 정보 조회", True)
        return current_user
        
    except Exception as e:
        error = BaseController.handle_exception(e, "관리자 정보 조회", "관리자 정보 조회 중 오류가 발생했습니다")
        raise error


@router.get("/teacher/me", response_model=User)
async def get_current_teacher_info(
    current_user: UserModel = Depends(get_current_teacher)
):
    """현재 로그인한 교사 정보 조회"""
    try:
        BaseController.log_request("교사 정보 조회", current_user.id)
        
        BaseController.log_response("교사 정보 조회", True)
        return current_user
        
    except Exception as e:
        error = BaseController.handle_exception(e, "교사 정보 조회", "교사 정보 조회 중 오류가 발생했습니다")
        raise error


@router.get("/check")
async def check_auth_status(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """현재 인증 상태 확인 API"""
    try:
        BaseController.log_request("인증 상태 확인")
        
        from app.core.auth.dependencies import get_current_user_from_cookie
        
        try:
            user = await get_current_user_from_cookie(request, db)
            status_data = {
                "authenticated": True,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role.value
                }
            }
        except HTTPException:
            status_data = {
                "authenticated": False,
                "user": None
            }
        
        BaseController.log_response("인증 상태 확인", True)
        return status_data
        
    except Exception as e:
        error = BaseController.handle_exception(e, "인증 상태 확인", "인증 상태 확인 중 오류가 발생했습니다")
        raise error


@router.get("/research-consent", response_model=ResearchConsentResponse)
async def get_research_consent_status(
    current_user = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """현재 사용자의 연구 참여 동의 상태 조회"""
    try:
        # RedirectResponse인 경우 인증 실패로 처리
        if isinstance(current_user, RedirectResponse):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다."
            )
        
        BaseController.log_request("연구 동의 상태 조회", current_user.id)
        
        user_service = UserService(db)
        consent_status = await user_service.get_research_consent_status(current_user.id)
        
        if consent_status is None:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자 정보를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        BaseController.log_response("연구 동의 상태 조회", True)
        return ResearchConsentResponse(**consent_status)
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "연구 동의 상태 조회", "연구 동의 상태 조회 중 오류가 발생했습니다")
        raise error


@router.put("/research-consent", response_model=ResearchConsentResponse)
async def update_research_consent(
    consent_data: ResearchConsentUpdate,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """연구 참여 동의 업데이트"""
    try:
        BaseController.log_request("연구 동의 업데이트", current_user.id, consent=consent_data.research_consent)
        
        # 모든 사용자 동의 가능 (학생, 교사, 관리자 모두)
        # 역할 제한 제거됨
        
        user_service = UserService(db)
        
        # 동의 데이터 준비
        update_data = {
            'research_consent': consent_data.research_consent,
            'consent_version': consent_data.consent_version
        }
        
        # 동의 업데이트 수행
        updated_user = await user_service.update_research_consent(current_user.id, update_data)
        
        if updated_user is None:
            raise BaseController.create_error_response(
                ApiErrorCode.NOT_FOUND,
                "사용자 정보를 찾을 수 없습니다",
                status_code=status.HTTP_404_NOT_FOUND
            )
        
        # 업데이트된 동의 상태 조회
        consent_status = await user_service.get_research_consent_status(current_user.id)
        
        BaseController.log_response("연구 동의 업데이트", True, consent=consent_data.research_consent)
        return ResearchConsentResponse(**consent_status)
        
    except HTTPException:
        raise
    except Exception as e:
        error = BaseController.handle_exception(e, "연구 동의 업데이트", "연구 동의 업데이트 중 오류가 발생했습니다")
        raise error

