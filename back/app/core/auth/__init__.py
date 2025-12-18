"""
Authentication package for the MAICE Web application.
This package handles all authentication related functionality including:
- User authentication
- Token management
- Password hashing
- Security constants
"""

from .security import (
    create_access_token,
    generate_auth_token,
    should_generate_auth_token,
    verify_auth_token,
    decode_access_token
)

from .constants import (
    SECRET_KEY,
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    COOKIE_NAME,
    COOKIE_MAX_AGE,
    LOGIN_URL,
    DASHBOARD_URL,
    ADMIN_DASHBOARD_URL
)

from .handlers import login_user, logout_user

__all__ = [
    'create_access_token',
    'generate_auth_token',
    'should_generate_auth_token',
    'verify_auth_token',
    'decode_access_token',
    'login_user',
    'logout_user',
    'SECRET_KEY',
    'ALGORITHM',
    'ACCESS_TOKEN_EXPIRE_MINUTES',
    'COOKIE_NAME',
    'COOKIE_MAX_AGE',
    'LOGIN_URL',
    'DASHBOARD_URL',
    'ADMIN_DASHBOARD_URL'
] 