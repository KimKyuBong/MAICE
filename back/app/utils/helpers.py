import os
import base64
import io
import uuid
from PIL import Image
from typing import Optional
from datetime import datetime, timedelta
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status, Request, UploadFile
from fastapi.security import OAuth2PasswordBearer
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.db.session import get_db
from app.models.models import UserModel, UserRole
import logging
from pydantic import BaseModel

# 로깅 설정
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# JWT 설정
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")  # 실제 배포 시에는 환경 변수로 관리
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간

# TokenData 클래스 정의
class TokenData(BaseModel):
    username: Optional[str] = None

def resize_image(image_data: bytes, max_size: int = 800) -> bytes:
    """이미지 크기를 조정합니다."""
    try:
        # 이미지 데이터를 PIL Image 객체로 변환
        image = Image.open(io.BytesIO(image_data))
        
        # 원본 크기 유지
        width, height = image.size
        
        # 최대 크기를 초과하는 경우에만 크기 조정
        if width > max_size or height > max_size:
            # 가로와 세로 중 큰 값을 기준으로 비율 계산
            ratio = max_size / max(width, height)
            new_width = int(width * ratio)
            new_height = int(height * ratio)
            
            # 이미지 크기 조정
            image = image.resize((new_width, new_height), Image.LANCZOS)
        
        # 이미지를 바이트로 변환
        output = io.BytesIO()
        image.save(output, format=image.format if image.format else 'JPEG')
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"이미지 크기 조정 중 오류 발생: {str(e)}")
        raise

def generate_unique_filename(original_filename: str) -> str:
    """고유한 파일 이름을 생성합니다."""
    try:
        # 파일 확장자 추출
        ext = os.path.splitext(original_filename)[1].lower()
        
        # UUID를 사용하여 고유한 파일 이름 생성
        unique_filename = f"{uuid.uuid4()}{ext}"
        
        return unique_filename
    except Exception as e:
        logger.error(f"파일 이름 생성 중 오류 발생: {str(e)}")
        raise

def save_uploaded_file(file_data: bytes, filename: str, upload_dir: str = "static/uploads") -> str:
    """업로드된 파일을 저장합니다."""
    try:
        # 업로드 디렉토리가 없으면 생성
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일 경로 생성
        file_path = os.path.join(upload_dir, filename)
        
        # 파일 저장
        with open(file_path, "wb") as f:
            f.write(file_data)
            
        return file_path
    except Exception as e:
        logger.error(f"파일 저장 중 오류 발생: {str(e)}")
        raise

def delete_file(file_path: str) -> bool:
    """파일을 삭제합니다."""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        logger.error(f"파일 삭제 중 오류 발생: {str(e)}")
        return False

class CustomOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        try:
            # API 요청인지 확인
            is_api_request = request.url.path.startswith("/api/")
            
            # 쿠키에서 토큰 확인
            token = request.cookies.get("access_token")
            if token:
                if token.startswith("Bearer "):
                    token = token.replace("Bearer ", "")
                logger.debug("쿠키에서 토큰 추출 성공")
                return token
                
            # 헤더에서 토큰 확인 (기존 OAuth2 방식)
            try:
                token = await super().__call__(request)
                if token and token.startswith("Bearer "):
                    token = token.replace("Bearer ", "")
                logger.debug("헤더에서 토큰 추출 성공")
                return token
            except HTTPException:
                pass
                
            logger.warning("토큰을 찾을 수 없음")
            
            # API 요청이 아닌 경우에만 리디렉션
            if not is_api_request:
                # URL 경로에 따라 적절한 로그인 페이지로 리디렉션
                path = request.url.path
                if path.startswith("/teacher"):
                    redirect_url = "/teacher/login"
                elif path.startswith("/student"):
                    redirect_url = "/student/login"
                else:
                    redirect_url = "/admin/login"
                    
                raise HTTPException(
                    status_code=status.HTTP_307_TEMPORARY_REDIRECT,
                    headers={"Location": redirect_url}
                )
            else:
                # API 요청의 경우 401 에러 반환
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"}
                )
                
        except Exception as e:
            logger.error(f"토큰 추출 중 오류: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication error",
                headers={"WWW-Authenticate": "Bearer"}
            )

# OAuth2 스키마 설정
oauth2_scheme = CustomOAuth2PasswordBearer(
    tokenUrl="admin/login",
    scheme_name="JWT"
)

# 이미지 처리 관련 상수
MAX_IMAGE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/gif']
UPLOAD_DIR = "static/uploads"

# 토큰 관련 함수
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """JWT 토큰을 생성합니다."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 사용자 인증 함수
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)) -> UserModel:
    """현재 인증된 사용자를 반환합니다."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        logger.debug("토큰 검증 시도")
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            logger.warning("토큰에 username 없음")
            raise credentials_exception
        token_data = TokenData(username=username)
        logger.debug(f"토큰 검증 성공: {username}")
    except JWTError as e:
        logger.error(f"JWT 검증 오류: {str(e)}")
        raise credentials_exception
    
    # AsyncSession을 사용한 쿼리
    query = select(UserModel).where(UserModel.username == token_data.username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    
    if user is None:
        logger.warning(f"DB에서 사용자를 찾을 수 없음: {token_data.username}")
        raise credentials_exception
    
    logger.debug(f"사용자 인증 성공: {user.username}, 역할: {user.role}")
    return user

# 역할 기반 접근 제어
async def get_current_active_user(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """활성 사용자인지 확인합니다."""
    return current_user

async def get_current_admin(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """관리자 권한이 있는지 확인합니다."""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_teacher(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """교사 권한이 있는지 확인합니다."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

async def get_current_student(current_user: UserModel = Depends(get_current_user)) -> UserModel:
    """학생 권한이 있는지 확인합니다."""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    return current_user

# 이미지 처리 함수
async def process_image(image_base64: str) -> Optional[str]:
    try:
        # base64 데이터에서 적절한 부분만 추출
        if ',' in image_base64:
            image_data = image_base64.split(',')[1]
        else:
            image_data = image_base64
        
        # 이미지 디코딩
        image_bytes = base64.b64decode(image_data)
        
        # 이미지 크기 체크
        if len(image_bytes) > MAX_IMAGE_SIZE:
            raise ValueError("이미지 크기가 5MB를 초과합니다.")
        
        # 이미지 열기
        image = Image.open(io.BytesIO(image_bytes))
        
        # 이미지 형식 검증
        if image.format.lower() not in ['jpeg', 'png', 'gif']:
            raise ValueError("지원하지 않는 이미지 형식입니다.")
        
        # 이미지 크기 조정 (필요한 경우)
        max_dimension = 1920
        if max(image.size) > max_dimension:
            ratio = max_dimension / max(image.size)
            new_size = tuple(int(dim * ratio) for dim in image.size)
            image = image.resize(new_size, Image.Resampling.LANCZOS)
        
        # 고유한 파일명 생성
        filename = f"{uuid.uuid4()}.{image.format.lower()}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        
        # 업로드 디렉토리 생성
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 이미지 저장
        image.save(filepath, quality=85, optimize=True)
        
        return filepath
    except Exception as e:
        print(f"이미지 처리 오류: {str(e)}")
        return None

async def process_upload_file(image: UploadFile) -> str:
    """UploadFile을 처리하여 파일 경로를 반환합니다."""
    try:
        # 업로드 디렉토리 생성
        upload_dir = "uploads"
        os.makedirs(upload_dir, exist_ok=True)
        
        # 파일명 생성
        file_extension = os.path.splitext(image.filename)[1]
        filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(upload_dir, filename)
        
        # 파일 저장
        with open(file_path, "wb") as f:
            content = await image.read()
            f.write(content)
        
        return file_path
        
    except Exception as e:
        logger.error(f"이미지 처리 오류: {str(e)}")
        raise HTTPException(status_code=500, detail="이미지 처리 중 오류가 발생했습니다.") 