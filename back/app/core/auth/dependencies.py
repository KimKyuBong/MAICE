"""Authentication dependencies for FastAPI."""

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError
from typing import Optional, Union

from app.models.models import UserModel, UserRole
from .security import decode_access_token
from .constants import LOGIN_URL, COOKIE_NAME, ADMIN_LOGIN_URL
from app.core.db.session import get_db
from app.services.maice import get_chat_service, IChatService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_chat_service_dependency(db: AsyncSession = Depends(get_db)) -> IChatService:
    """Chat 서비스 인스턴스를 반환합니다."""
    from app.services.maice import configure_services
    configure_services(db)
    return await get_chat_service()

async def get_current_user(
    request: Request,
    db = Depends(get_db)
) -> Union[UserModel, RedirectResponse]:
    """현재 로그인한 사용자를 반환합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 쿠키에서 토큰 확인
    token = request.cookies.get(COOKIE_NAME)
    
    # 쿠키에 없으면 Authorization 헤더 확인
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        else:
            if request.headers.get("accept") == "application/json":
                raise credentials_exception
            return RedirectResponse(url=LOGIN_URL, status_code=302)
        
    try:
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        if username is None:
            if request.headers.get("accept") == "application/json":
                raise credentials_exception
            return RedirectResponse(url=LOGIN_URL, status_code=302)
    except JWTError as e:
        # 토큰이 만료되었거나 유효하지 않은 경우 쿠키 삭제
        response = RedirectResponse(url=LOGIN_URL, status_code=302)
        response.delete_cookie(COOKIE_NAME)
        response.delete_cookie("access_token")
        response.delete_cookie("maice_auth")
        response.delete_cookie("session_id")
        
        if request.headers.get("accept") == "application/json":
            raise credentials_exception
        return response
        
    # 사용자 조회
    query = select(UserModel).where(UserModel.username == username)
    result = await db.execute(query)
    user = result.scalars().first()
    
    if user is None:
        if request.headers.get("accept") == "application/json":
            raise credentials_exception
        return RedirectResponse(url=LOGIN_URL, status_code=302)
        
    return user

async def get_current_teacher(
    request: Request,
    db = Depends(get_db)
) -> UserModel:
    """현재 로그인한 교사 사용자를 반환합니다."""
    try:
        user = await get_current_user(request, db)
        if isinstance(user, RedirectResponse):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="로그인이 필요합니다."
            )
            
        if user.role not in [UserRole.TEACHER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="교사 또는 관리자 권한이 필요합니다."
            )
            
        return user
        
    except HTTPException:
        raise

async def get_current_admin(
    request: Request,
    db = Depends(get_db)
) -> UserModel:
    """현재 로그인한 관리자를 반환합니다."""
    try:
        user = await get_current_user(request, db)
        
        # RedirectResponse는 API 엔드포인트에서 반환하면 안 됨
        if isinstance(user, RedirectResponse):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="인증이 필요합니다."
            )
            
        if user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="관리자 권한이 필요합니다."
            )
            
        return user
        
    except HTTPException:
        raise


async def get_current_user_from_cookie(
    request: Request,
    db: AsyncSession
) -> Optional[UserModel]:
    """쿠키에서 사용자 정보를 추출합니다. (인증 상태 확인용)"""
    try:
        # 쿠키에서 토큰 확인
        token = request.cookies.get(COOKIE_NAME)
        
        if not token:
            return None
            
        # Bearer 접두사 제거
        if token.startswith("Bearer "):
            token = token.replace("Bearer ", "")
            
        # 토큰 디코딩
        payload = decode_access_token(token)
        username: str = payload.get("sub")
        
        if username is None:
            return None
            
        # 사용자 조회
        query = select(UserModel).where(UserModel.username == username)
        result = await db.execute(query)
        user = result.scalars().first()
        
        return user
        
    except Exception:
        # 모든 오류는 None 반환으로 처리
        return None 