from fastapi import Depends, HTTPException, status, Cookie, Request
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from typing import Optional

from app.core.db.session import get_db
from app.models.models import UserModel, UserRole
from .helpers import SECRET_KEY, ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

async def get_current_user(
    access_token: Optional[str] = Cookie(None),
    db: AsyncSession = Depends(get_db)
) -> UserModel:
    """현재 로그인한 사용자를 반환합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        if not access_token:
            raise credentials_exception
            
        token = access_token.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
            
        query = select(UserModel).where(UserModel.username == username)
        result = await db.execute(query)
        user = result.scalars().first()
        
        if user is None:
            raise credentials_exception
            
        return user
        
    except JWTError:
        raise credentials_exception

async def get_current_teacher(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
):
    """현재 로그인한 교사 사용자를 반환합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="로그인이 필요합니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 쿠키에서 토큰 확인
    if not token and request.cookies.get("access_token"):
        token = request.cookies.get("access_token").replace("Bearer ", "")

    if not token:
        if request.headers.get("accept") == "application/json":
            raise credentials_exception
        return RedirectResponse(url="/teacher/login", status_code=302)

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            if request.headers.get("accept") == "application/json":
                raise credentials_exception
            return RedirectResponse(url="/teacher/login", status_code=302)
    except JWTError:
        if request.headers.get("accept") == "application/json":
            raise credentials_exception
        return RedirectResponse(url="/teacher/login", status_code=302)

    # 사용자 조회
    query = select(UserModel).where(
        (UserModel.username == username) &
        ((UserModel.role == UserRole.TEACHER) | (UserModel.role == UserRole.ADMIN))
    )
    result = await db.execute(query)
    user = result.scalars().first()

    if user is None:
        if request.headers.get("accept") == "application/json":
            raise credentials_exception
        return RedirectResponse(url="/teacher/login", status_code=302)

    return user 