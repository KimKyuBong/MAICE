"""Password hashing utility functions."""

import bcrypt
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def hash_password(password: str) -> str:
    """비밀번호를 해시화합니다."""
    try:
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    except Exception as e:
        logger.error(f"비밀번호 해시화 중 오류 발생: {str(e)}")
        raise

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호가 올바른지 확인합니다."""
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except Exception as e:
        logger.error(f"비밀번호 검증 중 오류 발생: {str(e)}")
        raise 