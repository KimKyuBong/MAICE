import logging
from typing import Optional
from fastapi import FastAPI, Depends
from app.services.assistant.assistant_service import AssistantService
from app.services.analysis.ocr_service import OCRService
from app.services.grading.grading_service import GradingService
from app.services.file.file_service import FileService
from app.core.config import settings
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db

logger = logging.getLogger(__name__)

# 설정 로깅
logger.info(f"OPENAI_API_KEY exists: {bool(settings.OPENAI_API_KEY)}")

class ServiceContainer:
    _instance: Optional['ServiceContainer'] = None
    assistant_service: Optional[AssistantService] = None
    
    @classmethod
    def get_instance(cls) -> 'ServiceContainer':
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance

async def init_services():
    """서비스 초기화"""
    container = ServiceContainer.get_instance()
    if container.assistant_service is None:
        container.assistant_service = AssistantService()
        await container.assistant_service.initialize()
    return container

async def get_assistant_service() -> AssistantService:
    """AssistantService 싱글톤 인스턴스 반환"""
    container = ServiceContainer.get_instance()
    if container.assistant_service is None:
        raise RuntimeError("Services not initialized")
    return container.assistant_service

async def get_file_service():
    return FileService()

async def get_ocr_service(
    assistant_service: AssistantService = Depends(get_assistant_service)
) -> OCRService:
    return OCRService(assistant_service)

async def get_grading_service(
    assistant_service: AssistantService = Depends(get_assistant_service)
) -> GradingService:
    return GradingService(assistant_service)

async def get_db_session():
    async with AsyncSession() as session:
        yield session

async def init_app(app: FastAPI):
    """앱 초기화"""
    try:
        await init_services()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Service initialization failed: {str(e)}")
        raise
