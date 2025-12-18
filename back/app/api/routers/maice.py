"""
MAICE API routers
MAICE 채팅 및 세션 관련 라우팅 정의
"""

# 계층화된 컨트롤러를 직접 import
from app.api.controllers.maice_controller import router

# MAICE 라우팅 매핑:
# /maice/chat → 채팅 처리 (스트리밍)
# /maice/test/chat → 테스트용 채팅
# /maice/sessions → 세션 관리  
# /maice/health → 서비스 상태 확인
# - 복잡한 MAICE 비즈니스 로직은 Service 계층으로 분리
# - 세션/데이터 관리는 Repository 계층으로 분리
