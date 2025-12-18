"""
Google OAuth 인증 API
"""

import logging
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.responses import RedirectResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.core.db.session import get_db
from app.core.auth.google_oauth import google_oauth_service
from app.core.auth.security import create_access_token, create_user_access_token
from app.models.models import UserModel, UserRole
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/google/login")
async def google_login(request: Request, state: Optional[str] = None):
    """Google OAuth 로그인 시작"""
    try:
        # Google OAuth 서비스 확인
        if google_oauth_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth가 설정되지 않았습니다. 환경변수를 확인하세요."
            )
        
        # Google OAuth 설정 확인
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth가 설정되지 않았습니다."
            )
        
        # 상태값 생성 (CSRF 보호용)
        if not state:
            import uuid
            state = str(uuid.uuid4())
        
        # Google 인증 URL 생성
        auth_url = google_oauth_service.get_authorization_url(state)
        
        logger.info(f"Google OAuth 로그인 시작: state={state}")
        return RedirectResponse(url=auth_url, status_code=302)
        
    except Exception as e:
        logger.error(f"Google 로그인 시작 오류: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google 로그인을 시작할 수 없습니다."
        )

@router.post("/google/callback")
async def google_callback(
    request: dict,
    db: AsyncSession = Depends(get_db)
):
    """Google OAuth 콜백 처리 - authorization code를 받아서 JWT 토큰 반환"""
    try:
        logger.info(f"Google OAuth 콜백 요청 받음: {request}")
        
        # Google OAuth 서비스 확인
        if google_oauth_service is None:
            logger.error("Google OAuth 서비스가 초기화되지 않음")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth가 설정되지 않았습니다. 환경변수를 확인하세요."
            )
        
        code = request.get("code")
        if not code:
            logger.error("Authorization code가 없음")
            raise HTTPException(status_code=400, detail="Authorization code가 필요합니다.")
        
        logger.info(f"Authorization code 받음: {code[:10]}...")
        
        # 인증 코드를 토큰으로 교환
        logger.info("Google 토큰 교환 시작...")
        google_data = await google_oauth_service.exchange_code_for_token(code)
        if not google_data:
            logger.error("Google 토큰 교환 실패")
            raise HTTPException(status_code=400, detail="Google 토큰 교환에 실패했습니다.")
        
        logger.info(f"Google OAuth 성공: {google_data['email']}")
        
        # 기존 사용자 확인
        query = select(UserModel).where(
            (UserModel.google_id == google_data['google_id']) |
            (UserModel.google_email == google_data['email'])
        )
        result = await db.execute(query)
        user = result.scalars().first()
        
        if user:
            # 기존 사용자 - Google 정보 업데이트
            user.google_id = google_data['google_id']
            user.google_email = google_data['email']
            user.google_name = google_data.get('name', user.google_name)
            user.google_picture = google_data.get('picture', user.google_picture)
            user.google_verified_email = google_data.get('verified_email', False)
            await db.commit()
            logger.info(f"기존 사용자 Google 정보 업데이트: {user.username}")
        else:
            # 새 사용자 생성 (기본적으로 학생 역할)
            user = UserModel.create_google_user(google_data, UserRole.STUDENT)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"새 Google 사용자 생성: {user.username}")
            
            # Google 사용자 생성 후 모드 자동 할당
            try:
                from app.services.user_mode_service import UserModeService
                user_mode_service = UserModeService(db)
                assigned_mode = await user_mode_service.assign_random_mode(user.id)
                logger.info(f"✅ Google 사용자 {user.id}에게 모드 '{assigned_mode}' 자동 할당 완료")
            except Exception as e:
                logger.error(f"❌ Google 사용자 {user.id} 모드 할당 실패: {str(e)}")
                # 모드 할당 실패해도 로그인은 계속 진행
        
        # JWT 토큰 생성 (사용자 정보 포함)
        access_token = create_user_access_token(user)
        
        # 사용자 정보와 함께 응답 반환
        return {
            "access_token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role.value,
                "email": user.google_email,  # Google 이메일 사용
                "name": user.google_name,    # Google 이름 사용
                "google_id": user.google_id,
                "google_email": user.google_email,
                "google_name": user.google_name,
                "google_picture": user.google_picture,
                "google_verified_email": user.google_verified_email
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google OAuth 콜백 처리 오류: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Google OAuth 처리 중 오류가 발생했습니다.")

@router.post("/google/verify")
async def verify_google_token(
    request: Request,
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """Google ID 토큰 검증 (프론트엔드용)"""
    try:
        # Google OAuth 서비스 확인
        if google_oauth_service is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Google OAuth가 설정되지 않았습니다. 환경변수를 확인하세요."
            )
        
        # Google 토큰 검증
        google_data = await google_oauth_service.verify_token(token)
        if not google_data:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="유효하지 않은 Google 토큰입니다."
            )
        
        # 사용자 조회 또는 생성
        query = select(UserModel).where(
            (UserModel.google_id == google_data['google_id']) |
            (UserModel.google_email == google_data['email'])
        )
        result = await db.execute(query)
        user = result.scalars().first()
        
        if not user:
            # 새 사용자 생성
            user = UserModel.create_google_user(google_data, UserRole.STUDENT)
            db.add(user)
            await db.commit()
            await db.refresh(user)
            logger.info(f"새 Google 사용자 생성 (토큰 검증): {user.username}")
        else:
            # 기존 사용자 정보 업데이트
            user.google_id = google_data['google_id']
            user.google_email = google_data['email']
            user.google_name = google_data.get('name', user.google_name)
            user.google_picture = google_data.get('picture', user.google_picture)
            user.google_verified_email = google_data.get('verified_email', False)
            await db.commit()
            logger.info(f"기존 사용자 Google 정보 업데이트 (토큰 검증): {user.username}")
        
        # JWT 토큰 생성
        access_token = create_access_token(data={"sub": user.username})
        
        return JSONResponse(content={
            "access_token": access_token,
            "token_type": "bearer",
            "role": user.role.value,
            "username": user.username,
            "id": user.id,
            "is_google_user": user.is_google_user(),
            "google_name": user.google_name,
            "google_picture": user.google_picture
        })
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google 토큰 검증 오류: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Google 토큰 검증 중 오류가 발생했습니다."
        )
