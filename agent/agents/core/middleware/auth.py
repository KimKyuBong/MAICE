"""Authentication middleware for the application."""

from fastapi import Request
from fastapi.responses import RedirectResponse, JSONResponse
from typing import Dict, List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import contextlib

from app.models.models import UserModel, UserRole
from app.core.auth.security import decode_access_token
from app.core.auth.constants import COOKIE_NAME
from app.core.db.session import get_db

logger = logging.getLogger(__name__)

# 각 역할별 접근 가능한 경로 설정
ROLE_PATHS: Dict[UserRole, List[str]] = {
    UserRole.ADMIN: ["/admin/", "/api/admin/"],
    UserRole.TEACHER: ["/teacher/", "/api/teacher/"],
    UserRole.STUDENT: ["/student/", "/api/student/"]
}

# 인증이 필요없는 공개 경로
PUBLIC_PATHS = [
    "/",
    "/static/",
    "/login",
    "/api/auth/login",
    "/api/auth/logout",
    "/.well-known/",
    "/favicon.ico"
]

@contextlib.asynccontextmanager
async def get_async_session():
    """비동기 DB 세션을 생성하고 관리합니다."""
    async for session in get_db():
        try:
            yield session
        finally:
            await session.close()

class AuthMiddleware:
    """인증 상태를 관리하는 미들웨어."""
    
    def __init__(self, app: Callable):
        """미들웨어 초기화."""
        self.app = app
        
    async def get_current_user(self, request: Request, db: AsyncSession) -> Optional[UserModel]:
        """현재 사용자를 가져옵니다."""
        try:
            # 쿠키에서 토큰 확인
            token = request.cookies.get(COOKIE_NAME)
            if not token:
                return None
                
            # 토큰 디코드
            token = token.replace("Bearer ", "")
            payload = decode_access_token(token)
            username = payload.get("sub")
            if not username:
                return None
                
            # DB에서 사용자 조회
            query = select(UserModel).where(UserModel.username == username)
            result = await db.execute(query)
            user = result.scalar_one_or_none()
            
            return user
        except Exception as e:
            logger.error(f"사용자 조회 오류: {str(e)}")
            return None
            
    def is_public_path(self, path: str) -> bool:
        """공개 접근 가능한 경로인지 확인합니다."""
        return any(path.startswith(public_path) for public_path in PUBLIC_PATHS)
        
    def get_login_url(self, path: str) -> str:
        """현재 경로에 맞는 로그인 URL을 반환합니다."""
        return "/login"  # 통합 로그인 페이지
        
    def can_access_path(self, user: UserModel, path: str) -> bool:
        """사용자가 해당 경로에 접근 가능한지 확인합니다."""
        if user.role == UserRole.ADMIN:  # 관리자는 모든 경로 접근 가능
            return True
            
        allowed_paths = ROLE_PATHS.get(user.role, [])
        return any(path.startswith(allowed_path) for allowed_path in allowed_paths)
        
    async def __call__(self, scope, receive, send):
        """미들웨어 핵심 로직을 처리합니다."""
        if scope["type"] != "http":  # http 요청만 처리
            return await self.app(scope, receive, send)
            
        request = Request(scope)
        path = request.url.path
        
        async with get_async_session() as db:
            try:
                # 공개 경로는 인증 없이 접근 가능
                if self.is_public_path(path):
                    request.state.db = db  # DB 세션을 request에 저장
                    return await self.app(scope, receive, send)
                    
                # 현재 사용자 확인
                user = await self.get_current_user(request, db)
                
                # 로그인하지 않은 경우
                if not user:
                    if request.headers.get("accept") == "application/json":
                        response = JSONResponse(
                            status_code=401,
                            content={"detail": "로그인이 필요합니다."}
                        )
                        return await response(scope, receive, send)
                    response = RedirectResponse(
                        url=self.get_login_url(path),
                        status_code=302
                    )
                    return await response(scope, receive, send)
                    
                # 권한 확인
                if not self.can_access_path(user, path):
                    if request.headers.get("accept") == "application/json":
                        response = JSONResponse(
                            status_code=403,
                            content={"detail": "접근 권한이 없습니다."}
                        )
                        return await response(scope, receive, send)
                    response = RedirectResponse(
                        url=self.get_login_url(path),
                        status_code=302
                    )
                    return await response(scope, receive, send)
                    
                # 사용자 정보와 DB 세션을 request에 저장
                request.state.user = user
                request.state.db = db
                
                return await self.app(scope, receive, send)
                
            except Exception as e:
                logger.error(f"인증 미들웨어 오류: {str(e)}")
                if request.headers.get("accept") == "application/json":
                    response = JSONResponse(
                        status_code=500,
                        content={"detail": "서버 오류가 발생했습니다."}
                    )
                    return await response(scope, receive, send)
                response = RedirectResponse(
                    url=self.get_login_url(path),
                    status_code=302
                )
                return await response(scope, receive, send) 