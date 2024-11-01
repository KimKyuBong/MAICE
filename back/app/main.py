from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
from dotenv import load_dotenv
import logging
import os
from pathlib import Path
from app.database import create_tables, engine, Base
from app.routers import init_routers
from contextlib import asynccontextmanager
from app.core.config import settings
from app.services.assistant.assistant_service import AssistantService
from app.services.analysis import ocr_service, consolidation_service
from app.services.assistant import assistant_service
from app.dependencies import init_app

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# .env 파일 로드
load_dotenv()

# OpenAI API 키 설정 (개발 환경용)
if not os.getenv("OPENAI_API_KEY"):
    os.environ["OPENAI_API_KEY"] = "sk-your-api-key-here"

logger.info(f"OPENAI_API_KEY loaded: {bool(settings.OPENAI_API_KEY)}")

async def init_db():
    """데이터베이스 초기화"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            logger.info("데이터베이스 테이블 생성 완료")
    except Exception as e:
        logger.error(f"데이터베이스 초기화 중 오류: {str(e)}")
        raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작/종료 시 실행되는 이벤트 핸들러"""
    # 시작 시
    await init_db()  # DB 초기화
    await init_app(app)  # 서비스 초기화
    yield
    # 종료 시
    # 필요한 cleanup 코드

# FastAPI 인스턴스 생성 시 lifespan 설정
app = FastAPI(lifespan=lifespan)

# CORS 설정 (필요시)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 서비스 시 필요한 도메인으로 제한하세요
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 정적 파일 서빙 설정 (절대 경로 사용)
BASE_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = BASE_DIR / "uploads"

if not UPLOAD_DIR.exists():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# 라우터 초기화
init_routers(app)

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 실행되는 이벤트"""
    try:
        # DB 초기화
        await init_db()
        logger.info("데이터베이스 테이블 생성 완료")
        
        # Assistant Service 초기화
        assistant_service = AssistantService()
        await assistant_service.initialize()
        app.state.assistant_service = assistant_service
        logger.info("Assistant Service 초기화 완료")
        
    except Exception as e:
        logger.error(f"Startup error: {str(e)}")
        raise

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=["app"]
    )