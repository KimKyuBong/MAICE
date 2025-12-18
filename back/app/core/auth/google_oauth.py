"""
Google OAuth 설정 및 유틸리티
"""

import os
import logging
from typing import Optional, Dict, Any
from google.auth.transport import requests
from google.oauth2 import id_token
from google_auth_oauthlib.flow import Flow
from google.auth.exceptions import GoogleAuthError

logger = logging.getLogger(__name__)

class GoogleOAuthConfig:
    """Google OAuth 설정 클래스"""
    
    def __init__(self):
        self.client_id = os.getenv("GOOGLE_CLIENT_ID")
        self.client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        self.redirect_uri = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:5173/auth/callback")
        
        # 환경변수 검증
        self._validate_config()
    
    def _validate_config(self):
        """Google OAuth 설정 검증"""
        missing_vars = []
        
        if not self.client_id:
            missing_vars.append("GOOGLE_CLIENT_ID")
        if not self.client_secret:
            missing_vars.append("GOOGLE_CLIENT_SECRET")
        
        if missing_vars:
            error_msg = f"Google OAuth 설정이 누락되었습니다: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info(f"Google OAuth 설정 완료 - Redirect URI: {self.redirect_uri}")
    
    def get_flow(self) -> Flow:
        """Google OAuth Flow 생성"""
        flow = Flow.from_client_config(
            client_config={
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=[
                "https://www.googleapis.com/auth/userinfo.email",
                "https://www.googleapis.com/auth/userinfo.profile",
                "openid"
            ]
        )
        flow.redirect_uri = self.redirect_uri
        return flow
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """Google OAuth 인증 URL 생성"""
        flow = self.get_flow()
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state
        )
        return auth_url

class GoogleOAuthService:
    """Google OAuth 서비스"""
    
    def __init__(self):
        self.config = GoogleOAuthConfig()
    
    async def verify_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Google ID 토큰 검증 및 사용자 정보 추출"""
        try:
            # ID 토큰 검증
            idinfo = id_token.verify_oauth2_token(
                token, 
                requests.Request(), 
                self.config.client_id
            )
            
            # 토큰이 유효한지 확인
            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')
            
            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'verified_email': idinfo.get('email_verified', False)
            }
            
        except GoogleAuthError as e:
            logger.error(f"Google 토큰 검증 실패: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Google OAuth 처리 중 오류: {str(e)}")
            return None
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """인증 URL 생성"""
        return self.config.get_authorization_url(state)
    
    async def exchange_code_for_token(self, code: str) -> Optional[Dict[str, Any]]:
        """인증 코드를 토큰으로 교환"""
        try:
            logger.info(f"토큰 교환 시작 - 코드: {code[:10]}...")
            flow = self.config.get_flow()
            logger.info("Flow 생성 완료, 토큰 요청 중...")
            flow.fetch_token(code=code)
            logger.info("토큰 교환 성공, 사용자 정보 요청 중...")
            
            # 사용자 정보 가져오기
            credentials = flow.credentials
            logger.info(f"Credentials 받음: {credentials.token[:20] if credentials.token else 'None'}...")
            
            user_info_response = flow.oauth2session.get(
                'https://www.googleapis.com/oauth2/v2/userinfo'
            )
            logger.info(f"사용자 정보 응답 상태: {user_info_response.status_code}")
            user_info = user_info_response.json()
            logger.info(f"사용자 정보: {user_info.get('email', 'Unknown')}")
            
            return {
                'google_id': user_info['id'],
                'email': user_info['email'],
                'name': user_info.get('name', ''),
                'picture': user_info.get('picture', ''),
                'verified_email': user_info.get('verified_email', False),
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token
            }
            
        except Exception as e:
            logger.error(f"토큰 교환 중 오류: {str(e)}", exc_info=True)
            return None

# 전역 인스턴스
# Google OAuth 서비스 인스턴스 생성 (환경변수 검증 포함)
try:
    google_oauth_service = GoogleOAuthService()
except ValueError as e:
    logger.error(f"Google OAuth 서비스 초기화 실패: {e}")
    google_oauth_service = None
