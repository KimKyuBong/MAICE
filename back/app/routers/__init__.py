from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.dependencies import get_grading_service
from .student import router as student_router
from .submission import router as submission_router
from .grading import router as grading_router
from .criteria import router as criteria_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup
    logger.info("서버 시작: 어시스턴트 초기화 중...")
    grading_service = get_grading_service()
    await grading_service.initialize()
    logger.info("서버 시작: 어시스턴트 초기화 완료")
    
    yield
    
    # Shutdown
    logger.info("서버 종료: 리소스 정리 중...")
    logger.info("서버 종료: 리소스 정리 완료")

def init_routers(app: FastAPI):
    """라우터 초기화"""
    app.include_router(student_router, prefix="/api")
    app.include_router(submission_router, prefix="/api")
    app.include_router(grading_router, prefix="/api")
    app.include_router(criteria_router, prefix="/api")

def create_app() -> FastAPI:
    """애플리케이션 팩토리"""
    app = FastAPI(lifespan=lifespan)
    init_routers(app)
    return app
