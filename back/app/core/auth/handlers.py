"""Authentication handlers for login and logout."""

import logging
from fastapi import HTTPException, Request, status, Depends
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Union, TYPE_CHECKING

from .security import (
    create_access_token,
    generate_auth_token,
    should_generate_auth_token,
    verify_auth_token
)
from .constants import (
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    DASHBOARD_URL,
    ADMIN_DASHBOARD_URL,
    LOGIN_URL
)
from app.core.db.session import get_db

if TYPE_CHECKING:
    from app.models.models import UserModel

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

async def login_user(
    request: Request,
    username: str,
    password: str,
    db: AsyncSession = Depends(get_db),
    role: Optional[str] = None
) -> Union[RedirectResponse, JSONResponse]:
    """사용자 로그인을 처리합니다."""
    try:
        logger.debug(f"로그인 시도: {username}, 역할: {role}")
        
        # 사용자 조회 쿼리 구성
        from app.models.models import UserModel, verify_password  # 런타임에 임포트
        query = select(UserModel).where(UserModel.username == username)
        if role:
            # 관리자(ADMIN)는 모든 권한이 있으므로 ADMIN 역할도 허용
            if role == "teacher":
                query = query.where((UserModel.role == role) | (UserModel.role == "admin"))
            else:
                query = query.where(UserModel.role == role)
            
        # 사용자 조회
        result = await db.execute(query)
        user = result.scalars().first()
        
        # 사용자 검증
        if not user or not verify_password(password, user.password_hash):
            logger.warning(f"로그인 실패: {username}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "잘못된 사용자명 또는 비밀번호입니다."}
            )
        
        # UUID 인증 토큰 확인 및 생성 (학생/교사)
        if should_generate_auth_token(user.role) and not user.access_token:
            user.access_token = generate_auth_token()
            logger.info(f"새 UUID 토큰 생성: {user.username}")
            await db.commit()
        
        # 사용자 모드 확인 및 할당 (모드가 None인 경우)
        if user.assigned_mode is None:
            try:
                from app.services.user_mode_service import UserModeService
                user_mode_service = UserModeService(db)
                assigned_mode = await user_mode_service.assign_random_mode(user.id)
                logger.info(f"✅ 로그인 시 사용자 {user.id}에게 모드 '{assigned_mode}' 자동 할당 완료")
            except Exception as e:
                logger.error(f"❌ 로그인 시 사용자 {user.id} 모드 할당 실패: {str(e)}")
                # 모드 할당 실패해도 로그인은 계속 진행
        
        # JWT 세션 토큰 생성
        session_token = create_access_token({"sub": user.username})
        
        # 역할에 따른 리다이렉트 URL 설정
        redirect_url = DASHBOARD_URL
        if user.role == "admin":
            redirect_url = ADMIN_DASHBOARD_URL
        
        logger.info(f"로그인 성공: {username}, 역할: {user.role}")
        
        # 응답 생성
        response = RedirectResponse(url=redirect_url, status_code=303)
        response.set_cookie(
            key=COOKIE_NAME,
            value=f"Bearer {session_token}",
            httponly=True,
            max_age=COOKIE_MAX_AGE,
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"로그인 처리 중 오류 발생: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="로그인 처리 중 오류가 발생했습니다."
        )

async def logout_user(request: Request) -> RedirectResponse:
    """사용자 로그아웃을 처리합니다."""
    response = RedirectResponse(url=LOGIN_URL, status_code=303)
    
    # 모든 인증 관련 쿠키 삭제
    response.delete_cookie(COOKIE_NAME)
    response.delete_cookie("access_token")
    response.delete_cookie("maice_auth")
    response.delete_cookie("session_id")
    
    # Google OAuth 관련 쿠키도 삭제
    response.delete_cookie("google_auth")
    response.delete_cookie("oauth_state")
    response.delete_cookie("oauth_code")
    
    # 쿠키 도메인과 경로 설정으로 확실히 삭제
    response.delete_cookie(COOKIE_NAME, path="/", domain=None)
    response.delete_cookie("access_token", path="/", domain=None)
    response.delete_cookie("maice_auth", path="/", domain=None)
    
    logger.info("✅ 사용자 로그아웃 완료 - 모든 인증 쿠키 삭제됨")
    return response 