from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
# StaticFiles removed - backend is now API-only
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import os
from dotenv import load_dotenv
import logging
from contextlib import asynccontextmanager
# fastapi-sessions 제거 - 대화 세션은 별도 관리

# 로거 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)
logger.info("🚀 MAICE Backend 서버 초기화 중...")

# 내부 모듈 임포트
from app.core.db.session import get_db, init_db
from app.models.models import UserModel, UserRole
from api_router import api_router
# views 디렉토리 제거됨 - 순수 API 서버로 변경
from app.core.middleware.auth import AuthMiddleware



load_dotenv()

# SQLAlchemy 로그 레벨 설정
logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)

# 시작 시 데이터베이스 및 Redis 초기화
@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup
    logger.info("🚀 백엔드 시작 이벤트 실행 시작")
    try:
        # 데이터베이스 초기화
        logger.info("🔄 데이터베이스 초기화 시작...")
        await init_db()
        logger.info("✅ 데이터베이스 초기화 완료")
        
        # Redis 클라이언트 초기화
        logger.info("🔄 Redis 클라이언트 초기화 시작...")
        from app.utils.redis_client import get_redis_client
        logger.info("📦 Redis 클라이언트 모듈 임포트 완료")
        redis_client = await get_redis_client()
        logger.info("✅ Redis 클라이언트 초기화 완료")
        
        # Redis 연결 테스트만 수행
        logger.info("🔄 Redis 연결 테스트 완료")
        # 에이전트 통신은 MAICEService에서 초기화될 때 시작됨
        
        logger.info("✅ 백엔드 웹 서비스 시작 완료")
    except Exception as e:
        logger.error(f"❌ 백엔드 웹 서비스 시작 실패: {e}")
        logger.exception("상세 에러 정보:")
        raise
    
    yield
    
    # Shutdown
    try:
        # Redis 클라이언트 정리
        from app.utils.redis_client import close_redis_client
        await close_redis_client()
        logger.info("✅ Redis 클라이언트 정리 완료")
        
        logger.info("✅ 백엔드 웹 서비스 종료 완료")
    except Exception as e:
        logger.error(f"❌ 백엔드 웹 서비스 종료 실패: {e}")

app = FastAPI(
    title="MAICE",
    docs_url=None,  # /docs 비활성화
    redoc_url=None,  # /redoc 비활성화
    lifespan=lifespan
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # 개발 환경
        "http://localhost:3000",  # 개발 환경 (대체)
        "https://maice.kbworks.xyz",  # 프로덕션 환경
        "http://maice.kbworks.xyz",   # 프로덕션 환경 (HTTP)
        "https://kbworks.xyz",        # 최상위 도메인
        "http://kbworks.xyz",         # 최상위 도메인 (HTTP)
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 대화 세션은 conversation_sessions 테이블에서 별도 관리

# 인증 미들웨어 등록
app.add_middleware(AuthMiddleware)

# API 라우터 등록 (JSON 응답)
app.include_router(api_router, prefix="/api", tags=["api"])

# 페이지 라우터 등록 (HTML 응답)
# views 라우터들 제거됨 - 순수 API 서버로 변경



# 메인 페이지 - 프론트엔드로 리다이렉트
@app.get("/")
async def main_page():
    """루트 페이지 - 프론트엔드로 리다이렉트"""
    return RedirectResponse(url="http://localhost:5173", status_code=302)

# 헬스 체크 엔드포인트
@app.get("/health")
async def health_check():
    """간단하고 안정적인 헬스체크 엔드포인트"""
    from datetime import datetime
    import redis.asyncio as redis
    
    try:
        # 기본 상태 정보
        api_status = "healthy"
        database_status = "healthy"
        redis_status = "healthy"
        
        # 데이터베이스 연결 확인
        try:
            from app.core.db.session import check_db_connection
            db_status = await check_db_connection()
            database_status = "healthy" if db_status else "unhealthy"
        except Exception as e:
            logger.error(f"데이터베이스 헬스 체크 실패: {e}")
            database_status = "unhealthy"
        
        # Redis 연결 확인
        try:
            redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
            redis_client = await redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            await redis_client.close()
        except Exception as e:
            logger.error(f"Redis 헬스 체크 실패: {e}")
            redis_status = "unhealthy"
        
        # 전체 상태 결정
        overall_status = "healthy" if all([
            api_status == "healthy",
            database_status == "healthy",
            redis_status == "healthy"
        ]) else "degraded"
        
        return {
            "status": overall_status,
            "api_status": api_status,
            "database_status": database_status,
            "redis_status": redis_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": "1.0.1",
            "environment": os.getenv("ENVIRONMENT", "unknown"),
            "message": "MAICE Backend is running"
        }
        
    except Exception as e:
        logger.error(f"헬스 체크 오류: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "api_status": "unhealthy",
            "database_status": "unknown",
            "redis_status": "unknown",
            "timestamp": datetime.utcnow().isoformat(),
            "message": "Health check error",
            "error": str(e)[:100]
        }

# 간단한 헬스체크 엔드포인트 (로드밸런서용)
@app.get("/health/simple")
async def simple_health_check():
    """로드밸런서용 간단한 헬스체크"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()} 