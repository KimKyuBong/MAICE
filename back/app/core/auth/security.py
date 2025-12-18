"""Security related utility functions."""

import logging
from datetime import datetime, timedelta
from typing import Optional, TYPE_CHECKING
from jose import jwt
import uuid
from passlib.context import CryptContext

from .constants import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

if TYPE_CHECKING:
    from app.models.models import UserModel

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    """비밀번호를 해시화합니다."""
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호를 검증합니다."""
    return pwd_context.verify(plain_password, hashed_password)

# UUID 토큰 관련 함수
def generate_auth_token() -> str:
    """사용자 인증을 위한 UUID 토큰을 생성합니다."""
    try:
        logger.debug("UUID 토큰 생성 시도")
        token = str(uuid.uuid4())
        logger.debug("UUID 토큰 생성 완료")
        return token
    except Exception as e:
        logger.error(f"UUID 토큰 생성 오류: {str(e)}", exc_info=True)
        raise

def should_generate_auth_token(role: str) -> bool:
    """주어진 역할에 대해 UUID 토큰을 생성해야 하는지 확인합니다."""
    return role in ["student", "teacher"]

def verify_auth_token(token: str) -> bool:
    """UUID 토큰의 유효성을 검증합니다."""
    try:
        # UUID 형식 검증
        uuid.UUID(token)
        return True
    except ValueError:
        return False

# JWT 세션 토큰 관련 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 세션 토큰을 생성합니다."""
    try:
        logger.debug("JWT 세션 토큰 생성 시도")
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug("JWT 세션 토큰 생성 완료")
        return encoded_jwt
    except Exception as e:
        logger.error(f"JWT 세션 토큰 생성 오류: {str(e)}", exc_info=True)
        raise

def create_user_access_token(user: "UserModel", expires_delta: Optional[timedelta] = None) -> str:
    """사용자 정보를 포함한 JWT 토큰을 생성합니다."""
    try:
        logger.debug("사용자 정보 포함 JWT 토큰 생성 시도")
        to_encode = {
            "sub": user.username,
            "id": user.id,
            "role": user.role.value,
            "email": user.google_email,  # Google 이메일 사용
            "name": user.google_name,    # Google 이름 사용
            "google_id": user.google_id,
            "google_email": user.google_email,
            "google_name": user.google_name,
            "google_picture": user.google_picture,
            "google_verified_email": user.google_verified_email
        }
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug("사용자 정보 포함 JWT 토큰 생성 완료")
        return encoded_jwt
    except Exception as e:
        logger.error(f"사용자 정보 포함 JWT 토큰 생성 오류: {str(e)}", exc_info=True)
        raise

def decode_access_token(token: str) -> dict:
    """JWT 토큰을 디코딩합니다."""
    try:
        logger.debug("JWT 토큰 디코딩 시도")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        logger.debug("JWT 토큰 디코딩 완료")
        return payload
    except jwt.JWTError as e:
        logger.error(f"JWT 토큰 디코딩 오류: {str(e)}")
        raise

def create_refresh_token(data: dict) -> str:
    """리프레시 토큰을 생성합니다."""
    try:
        logger.debug("리프레시 토큰 생성 시도")
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=7)  # 리프레시 토큰은 7일간 유효
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
        logger.debug("리프레시 토큰 생성 완료")
        return encoded_jwt
    except Exception as e:
        logger.error(f"리프레시 토큰 생성 오류: {str(e)}", exc_info=True)
        raise

def generate_user_token() -> str:
    """사용자 토큰을 생성합니다. (UUID v4 사용)"""
    try:
        logger.debug("사용자 토큰 생성 시도")
        token = str(uuid.uuid4())
        logger.debug("사용자 토큰 생성 완료")
        return token
    except Exception as e:
        logger.error(f"사용자 토큰 생성 오류: {str(e)}", exc_info=True)
        raise

def should_generate_token(role: str) -> bool:
    """주어진 역할에 대해 토큰을 생성해야 하는지 확인합니다."""
    return role in ["student", "teacher"] 