"""Authentication related constants."""

import os
from datetime import timedelta

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # 실제 배포 시에는 환경 변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# 쿠키 설정
COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = ACCESS_TOKEN_EXPIRE_MINUTES * 60  # 초 단위로 변환

# 비밀번호 해싱 설정
PWD_HASH_ALGORITHM = "bcrypt"
PWD_SALT_ROUNDS = 12

# 로그인 관련 설정
MAX_LOGIN_ATTEMPTS = 5
LOGIN_COOLDOWN_MINUTES = 15

# 리다이렉션 URL
LOGIN_URL = "/login"
DASHBOARD_URL = "/teacher/"
ADMIN_LOGIN_URL = "/login"
ADMIN_DASHBOARD_URL = "/dashboard" 