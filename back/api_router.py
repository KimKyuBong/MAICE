"""
API router integration.
Combines all API endpoints under /api prefix.
"""

from fastapi import APIRouter
from app.api.routers.auth import router as auth_router
from app.api.routers.google_auth import router as google_auth_router  
from app.api.routers.users import router as users_router
from app.api.routers.exports import router as exports_router
from app.api.routers.admin import router as admin_router
from app.api.routers.maice import router as maice_router
from app.api.routers.monitoring import router as monitoring_router
from app.api.routers.teacher import router as teacher_router


# 메인 API 라우터
api_router = APIRouter()

# 하위 라우터 등록
api_router.include_router(auth_router, prefix="/auth", tags=["authentication"])
api_router.include_router(google_auth_router, prefix="/auth", tags=["google-oauth"])
api_router.include_router(users_router, prefix="/users", tags=["users"])
api_router.include_router(exports_router, prefix="/exports", tags=["exports"])
api_router.include_router(admin_router, prefix="/admin", tags=["admin"])
api_router.include_router(maice_router, prefix="/student", tags=["student"])
api_router.include_router(monitoring_router, prefix="/monitoring", tags=["monitoring"])
api_router.include_router(teacher_router, prefix="/teacher", tags=["teacher"])