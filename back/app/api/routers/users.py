"""
User management API routers
사용자 관련 라우팅을 정의하는 엔트리 포인트
"""

# 계층화된 컨트롤러를 직접 import
from app.api.controllers.users_controller import router

# 모든 라우팅 로직은 컨트롤러에서 처리됨:
# /users/* → UsersController에서 처리
# - POST /users → 생성
# - GET /users → 목록 조회  
# - GET /users/{id} → 개별 조회
# - PUT /users/{id} → 수정
# - DELETE /users/{id} → 삭제