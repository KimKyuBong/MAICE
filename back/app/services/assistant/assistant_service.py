from typing import Dict, List, Optional, Any
import logging
from openai import AsyncOpenAI
import os
from app.services.base_service import BaseService
from app.core.config import settings

logger = logging.getLogger(__name__)

class AssistantService(BaseService):
    def __init__(self):
        super().__init__(settings)
        self.client = None
        self.client = self._initialize_client()
        self.assistants: Dict[str, Any] = {}

    def _initialize_client(self):
        """OpenAI 클라이언트 초기화"""
        try:
            client = AsyncOpenAI(
                api_key=self.settings.OPENAI_API_KEY,
                organization=self.settings.OPENAI_ORG_ID,
                max_retries=3,
                timeout=60.0,
            )
            logger.info("OpenAI client initialized successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise

    async def initialize(self):
        """모든 Assistant 초기화"""
        try:
            # OCR Assistant 생성
            self.assistants['ocr'] = await self._create_or_get_assistant(
                name="OCR Assistant",
                description="Analyzes images to extract mathematical expressions and text",
                model="gpt-4o-mini",
                tools=[{"type": "retrieval"}],
                instructions="""
                1. Analyze the provided image carefully.
                2. Extract all mathematical expressions and text exactly as they appear in the image.
                3. Do not add any explanations, summaries, or interpretations.
                4. Do not separate text and mathematical expressions.
                5. Return the extracted data in JSON format with only the required fields.
                """
            )
            
            # Grading Assistant 생성
            self.assistants['grading'] = await self._create_or_get_assistant(
                name="Grading Assistant",
                description="Grades mathematical solutions based on criteria",
                model="gpt-4o-mini",
                tools=[{"type": "retrieval"}],
                instructions="""
                1. Review the solution against provided criteria
                2. Assign scores based on the rubric
                3. Provide detailed feedback
                4. Highlight areas for improvement
                """
            )
            
            logger.info("All assistants initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize assistants: {e}")
            raise

    async def _create_or_get_assistant(
        self,
        name: str,
        description: str,
        model: str,
        tools: List[Dict],
        instructions: str,
        file_ids: List[str] = None
    ):
        """Assistant 생성 또는 가져오기"""
        try:
            # 기존 assistant 찾기
            assistants = await self.client.beta.assistants.list()
            for assistant in assistants.data:
                if assistant.name == name:
                    logger.info(f"Found existing assistant: {assistant.id}")
                    return assistant
            
            # 새 assistant 생성
            assistant = await self.client.beta.assistants.create(
                name=name,
                description=description,
                model=model,
                tools=tools,
                instructions=instructions
            )
            logger.info(f"Created new assistant: {assistant.id}")
            return assistant
            
        except Exception as e:
            logger.error(f"Failed to create or get assistant: {e}")
            raise

    def get_client(self) -> AsyncOpenAI:
        """OpenAI 클라이언트 반환"""
        if not self.client:
            raise RuntimeError("OpenAI client not initialized")
        return self.client

    def get_assistant(self, assistant_type: str):
        """특정 타입의 Assistant 가져오기"""
        assistant = self.assistants.get(assistant_type)
        if not assistant:
            raise ValueError(f"Assistant type '{assistant_type}' not found")
        return assistant
