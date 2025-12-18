"""
Authentication API routers
인증 관련 라우팅 정의
"""

# 계층화된 컨트롤러를 직접 import
from app.api.controllers.auth_controller import router

# 인증 라우팅 매핑:
# /auth/me → 현재 사용자 정보
# /auth/login → 로그인 (현재 비활성화 - Google OAuth 사용)
# /auth/logout → 로그아웃
# /auth/check → 인증 상태 확인
# /auth/admin/me → 관리자 정보
# /auth/teacher/me → 교사 정보