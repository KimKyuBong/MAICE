"""
LLM 호출을 위한 공통 툴
- 다양한 LLM 모델 지원
- 프롬프트 템플릿 관리
- 설정 중앙화
- 에러 처리 통일
"""

import asyncio
import logging
import os
import tiktoken
import json
import uuid
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from datetime import datetime
import asyncpg

# chat_completion은 이 파일에 직접 구현됨
from agents.base_agent import Tool

# 추가 import for multi-provider support
try:
    import anthropic
except ImportError:
    anthropic = None

try:
    import google.generativeai as genai
except ImportError:
    genai = None

try:
    import httpx
    import aiohttp
    import json
except ImportError:
    httpx = None
    json = None

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """지원하는 LLM 프로바이더"""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    MCP = "mcp"


# chat_completion 함수 추가 (기존 llm.py에서 이동)
async def chat_completion(
    messages: List[Dict[str, Any]],
    *,
    model: Optional[str] = None,
    max_completion_tokens: int = 1000,
    stream: bool = False,
    **kwargs,
):
    """LLM 호출 함수 - OpenAI 직접 호출"""
    try:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        model_name = model or os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini")

        # GPT-5-mini는 temperature 파라미터를 지원하지 않으므로 제거
        api_params = {
            "model": model_name,
            "messages": messages,
            "max_completion_tokens": max_completion_tokens,
            "stream": stream,
        }

        # temperature는 기본값(1)만 지원하므로 제거
        # temperature=kwargs.get("temperature", 0.7)  # GPT-5-mini에서 지원하지 않음

        response = await client.chat.completions.create(**api_params)

        return response

    except Exception as e:
        logger.error(f"OpenAI API 호출 실패: {e}")
        raise


def count_tokens(text: str, model: str = "gpt-4") -> int:
    """텍스트의 토큰 수를 계산합니다."""
    try:
        # model이 None이거나 빈 문자열인 경우 기본값 사용
        if not model or model.strip() == "":
            model = "gpt-4"

        model = str(model).lower()

        # MCP/penGPT 모델의 경우 기본 cl100k_base 사용
        if "pengpt" in model or "mcp" in model or "pen" in model.lower():
            encoding = tiktoken.get_encoding("cl100k_base")
        # gpt-5 시리즈는 cl100k_base 인코딩 사용
        elif model in ["gpt-5-mini", "gpt-5-nano", "gpt-5"]:
            encoding = tiktoken.get_encoding("cl100k_base")
        # Claude 모델들은 cl100k_base 사용
        elif model.startswith("claude"):
            encoding = tiktoken.get_encoding("cl100k_base")
        # Gemini 모델들은 대략적인 계산 (tiktoken이 지원하지 않음)
        elif model.startswith("gemini"):
            return len(text) // 4  # 대략적인 계산
        else:
            try:
                encoding = tiktoken.get_encoding(
                    "cl100k_base"
                )  # 기본값으로 cl100k_base 사용
            except:
                # 모든 방법이 실패하는 경우 UTF-8 바이트 길이 기준 추정
                return len(text.encode("utf-8")) // 3

        return len(encoding.encode(text))
    except Exception as e:
        logger.warning(f"토큰 계산 실패: {e}")
        # 대략적인 추정 (영어 기준 4자당 1토큰)
        return len(text) // 4


def count_messages_tokens(messages: List[Dict[str, str]], model: str = "gpt-4") -> int:
    """메시지 리스트의 총 토큰 수를 계산합니다."""
    total_tokens = 0
    for message in messages:
        content = message.get("content", "")
        total_tokens += count_tokens(content, model)
    return total_tokens


@dataclass
class LLMConfig:
    """LLM 설정"""

    provider: LLMProvider = LLMProvider(os.getenv("LLM_PROVIDER", "openai"))
    model: str = ""
    max_tokens: int = 1000
    temperature: Optional[float] = None
    stream: bool = False
    timeout: int = 120
    max_retries: int = 3
    retry_delay: float = 2.0
    json_response: bool = False

    def __post_init__(self):
        """프로바이더에 따라 기본 모델 설정"""
        if not self.model:
            if self.provider == LLMProvider.OPENAI:
                self.model = os.getenv("OPENAI_CHAT_MODEL", "gpt-5-mini")
            elif self.provider == LLMProvider.ANTHROPIC:
                self.model = os.getenv(
                    "ANTHROPIC_CHAT_MODEL", "claude-sonnet-4-20250514"
                )
            elif self.provider == LLMProvider.GOOGLE:
                self.model = os.getenv("GOOGLE_CHAT_MODEL", "gemini-2.5-flash-lite")
            elif self.provider == LLMProvider.MCP:
                self.model = os.getenv("MCP_MODEL", "penGPT")


@dataclass
class PromptTemplate:
    """프롬프트 템플릿"""

    system_prompt: str
    user_template: str
    variables: Dict[str, Any] = None


class LLMTool(Tool):
    """LLM 호출을 위한 공통 툴"""

    def __init__(
        self,
        name: str = "llm_tool",
        config: LLMConfig = None,
        prompt_template: PromptTemplate = None,
    ):
        super().__init__(name)
        self.config = config or LLMConfig()
        self.prompt_template = prompt_template
        self.logger = logging.getLogger(f"tools.{name}")

        # DB 연결 정보 설정
        self.db_url = os.getenv(
            "AGENT_DATABASE_URL",
            "postgresql://postgres:postgres@localhost:5432/maice_agent",
        )

    async def _save_prompt_to_db(
        self,
        messages: List[Dict[str, str]],
        config: LLMConfig,
        prompt_input: Union[str, PromptTemplate, Dict, None] = None,
        variables: Dict[str, Any] = None,
        message_id: str = None,
        session_id: int = None,
        user_id: int = None,
        input_tokens: int = None,
    ):
        """프롬프트를 데이터베이스에 저장 - maice_agent DB 스키마 준수

        Returns:
            int: 저장된 프롬프트의 ID
        """
        try:
            conn = await asyncpg.connect(self.db_url)

            # message_id가 없는 경우 기본값 생성
            if not message_id:
                message_id = str(uuid.uuid4())

            # 프롬프트 전체 내용 구성
            prompt_content = json.dumps(
                {
                    "messages": messages,
                    "prompt_input": str(prompt_input) if prompt_input else None,
                    "variables": variables,
                    "config": {
                        "provider": config.provider.value,
                        "model": config.model,
                        "max_tokens": config.max_tokens,
                        "stream": config.stream,
                        "temperature": config.temperature,
                    },
                },
                ensure_ascii=False,
            )

            # llm_prompt_logs 테이블 스키마 맞춤 (원격 DB) - ID 반환
            prompt_id = await conn.fetchval(
                """
                INSERT INTO llm_prompt_logs (
                    tool_name, provider, model, session_id, user_id, agent_name,
                    input_prompt, input_tokens, max_tokens, temperature, stream,
                    timeout, max_retries, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
                RETURNING id
            """,
                self.name,  # tool_name (NOT NULL)
                config.provider.value,  # provider (NOT NULL)
                config.model,  # model (NOT NULL)
                session_id or 0,  # session_id
                user_id or 0,  # user_id
                self.name,  # agent_name
                prompt_content,  # input_prompt
                input_tokens or 0,  # input_tokens
                config.max_tokens,  # max_tokens
                float(config.temperature)
                if config.temperature is not None
                else None,  # temperature
                config.stream,  # stream
                config.timeout,  # timeout
                config.max_retries,  # max_retries
                datetime.now(),  # created_at
            )

            await conn.close()
            self.logger.info(
                f"✅ 프롬프트 DB 저장 완료: ID={prompt_id}, 세션 {session_id}, {self.name}"
            )
            return prompt_id

        except Exception as e:
            self.logger.error(f"❌ 프롬프트 DB 저장 실패: {e}")
            import traceback

            self.logger.error(f"스택 트레이스: {traceback.format_exc()}")
            # DB 저장 실패해도 LLM 호출은 계속 진행
            return None

    async def _save_response_to_db(
        self,
        response_content: str,
        config: LLMConfig,
        input_tokens: int,
        response_time: float = None,
        message_id: str = None,
        session_id: int = None,
        user_id: int = None,
        prompt_id: int = None,
    ):
        """응답을 데이터베이스에 저장 - maice_agent DB 스키마 준수

        Args:
            response_content: 응답 내용
            config: LLM 설정
            input_tokens: 입력 토큰 수
            response_time: 응답 시간 (초)
            message_id: 메시지 ID
            session_id: 세션 ID
            user_id: 사용자 ID
            prompt_id: 프롬프트 ID (프롬프트와 응답 연결)
        """
        try:
            conn = await asyncpg.connect(self.db_url)

            # 응답 데이터 삽입 (원격 DB 스키마 준수) - prompt_id 포함
            await conn.execute(
                """
                INSERT INTO llm_response_logs (
                    tool_name, provider, model, prompt_id, session_id, user_id, agent_name, 
                    response_content, response_tokens, response_time_ms, success, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            """,
                self.name,  # tool_name (NOT NULL)
                config.provider.value,  # provider (NOT NULL)
                config.model,  # model (NOT NULL)
                prompt_id,  # prompt_id - 프롬프트와 응답 연결
                session_id or 0,  # session_id
                user_id or 0,  # user_id
                self.name,  # agent_name
                response_content,  # response_content
                count_tokens(response_content, config.model),  # response_tokens
                int(response_time * 1000) if response_time else 0,  # response_time_ms
                True,  # success
                datetime.now(),  # created_at
            )

            await conn.close()
            self.logger.info(
                f"✅ 응답 DB 저장 완료: 세션 {session_id}, 프롬프트 ID={prompt_id}, {self.name}"
            )

        except Exception as e:
            self.logger.error(f"❌ 응답 DB 저장 실패: {e}")
            import traceback

            self.logger.error(f"스택 트레이스: {traceback.format_exc()}")
            # DB 저장 실패해도 계속 진행

    async def execute(
        self,
        prompt: Union[str, PromptTemplate] = None,
        variables: Dict[str, Any] = None,
        config_override: LLMConfig = None,
        message_id: str = None,
        session_id: int = None,
        streams_client=None,
        request_id: str = None,
        json_response: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        # request_id를 저장해두어서 스트리밍 중에도 참조할 수 있도록 함
        self._current_request_id = request_id
        """
        LLM 호출 실행
        
        Args:
            prompt: 프롬프트 문자열 또는 템플릿
            variables: 템플릿 변수
            config_override: 설정 오버라이드
            **kwargs: 추가 파라미터
        
        Returns:
            Dict[str, Any]: LLM 응답 결과
        """
        try:
            # json_response 파라미터를 config_override에 반영
            if json_response:
                if config_override is None:
                    config_override = LLMConfig()
                config_override.json_response = json_response

            # 설정 병합
            config = self._merge_config(config_override)

            # 프롬프트 처리
            messages = self._prepare_messages(prompt, variables)

            # 토큰 수 계산 및 로그
            input_tokens = count_messages_tokens(messages, config.model)
            self.logger.debug(
                f"📊 입력 토큰 수: {input_tokens} (제한: {config.max_tokens})"
            )

            # 프롬프트 요약 정보만 로깅
            # if isinstance(prompt, dict):
            #     self.logger.info(f"🚀 LLM 호출 시작 - system: {len(prompt.get('system', ''))}자, user: {len(prompt.get('user', ''))}자")
            # else:
            #     self.logger.info(f"🚀 LLM 호출 시작 - 프롬프트: {len(str(prompt))}자")

            # 프롬프트를 DB에 저장 (세션 ID, 사용자 ID 포함) - ID 반환받음
            prompt_id = await self._save_prompt_to_db(
                messages,
                config,
                prompt,
                variables,
                message_id,
                session_id,
                kwargs.get("user_id"),
                input_tokens,
            )

            # LLM 호출 시작 시간 기록
            start_time = asyncio.get_event_loop().time()
            response = await self._call_llm_with_retry(messages, config)
            end_time = asyncio.get_event_loop().time()
            response_time = end_time - start_time

            # 스트리밍 처리
            if config.stream:
                # 스트리밍 응답을 처리하여 최종 content 반환 (실시간 청크 전송 포함)
                full_content = await self._process_streaming_response(
                    response, config, session_id, streams_client
                )

                # 스트리밍 완료 후 응답을 DB에 저장 - prompt_id 전달하여 연결
                await self._save_response_to_db(
                    full_content,
                    config,
                    input_tokens,
                    response_time,
                    message_id,
                    session_id,
                    kwargs.get("user_id"),
                    prompt_id,
                )

                return {
                    "success": True,
                    "content": full_content,
                    "usage": None,
                    "model": config.model,
                    "provider": config.provider.value,
                }
            else:
                # MCP 프로바이더의 경우 content가 리스트일 수 있음
                content = response.choices[0].message.content
                if isinstance(content, list):
                    # 리스트인 경우 첫 번째 요소의 text 추출
                    if (
                        len(content) > 0
                        and isinstance(content[0], dict)
                        and "text" in content[0]
                    ):
                        content = content[0]["text"]
                    else:
                        content = str(content[0]) if content else ""
                elif not isinstance(content, str):
                    content = str(content)

                # 응답을 DB에 저장 (세션 ID, 사용자 ID 포함) - prompt_id 전달하여 연결
                await self._save_response_to_db(
                    content,
                    config,
                    input_tokens,
                    response_time,
                    message_id,
                    session_id,
                    kwargs.get("user_id"),
                    prompt_id,
                )

                # LLM 호출 완료 로깅
                self.logger.info(
                    f"✅ LLM 호출 완료 - 응답: {len(content)}자, 소요시간: {response_time:.2f}초"
                )

                return {
                    "success": True,
                    "content": content,
                    "usage": getattr(response, "usage", None),
                    "model": config.model,
                    "provider": config.provider.value,
                }

        except Exception as e:
            self.logger.error(f"LLM 호출 실패: {e}")
            return {"success": False, "error": str(e), "content": None}

    def _merge_config(self, override: Optional[LLMConfig]) -> LLMConfig:
        """설정 병합"""
        if not override:
            return self.config

        # 기존 설정을 복사하고 오버라이드 적용
        merged = LLMConfig(
            provider=override.provider or self.config.provider,
            model=override.model or self.config.model,
            max_tokens=override.max_tokens or self.config.max_tokens,
            temperature=override.temperature
            if override.temperature is not None
            else self.config.temperature,
            stream=override.stream
            if override.stream is not None
            else self.config.stream,
            timeout=override.timeout or self.config.timeout,
            max_retries=override.max_retries or self.config.max_retries,
            retry_delay=override.retry_delay or self.config.retry_delay,
            json_response=override.json_response
            if override.json_response is not None
            else self.config.json_response,
        )
        return merged

    def _prepare_messages(
        self,
        prompt: Union[str, PromptTemplate, Dict, None],
        variables: Dict[str, Any] = None,
    ) -> List[Dict[str, str]]:
        """메시지 준비"""
        if isinstance(prompt, PromptTemplate):
            # 템플릿 사용
            system_prompt = self._format_template(prompt.system_prompt, variables or {})
            user_content = self._format_template(prompt.user_template, variables or {})
        elif isinstance(prompt, dict):
            # 딕셔너리 형태 (PromptBuilderV2 결과)
            system_prompt = prompt.get("system", "")
            user_content = prompt.get("user", "")
        elif isinstance(prompt, str):
            # 단순 문자열
            system_prompt = (
                self.prompt_template.system_prompt if self.prompt_template else ""
            )
            user_content = prompt
        else:
            # 기본 템플릿 사용
            if not self.prompt_template:
                raise ValueError("프롬프트나 템플릿이 제공되지 않았습니다")
            system_prompt = self.prompt_template.system_prompt
            user_content = self._format_template(
                self.prompt_template.user_template, variables or {}
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": user_content})

        return messages

    def _format_template(self, template: str, variables: Dict[str, Any]) -> str:
        """스마트 템플릿 포맷팅 - 누락된 변수 자동 감지 및 처리"""
        if not template:
            return template

        if not variables:
            return template

        # 1. 템플릿에서 사용되는 변수들 자동 추출
        import re

        template_vars = set(re.findall(r"\{([^}]+)\}", template))
        provided_vars = set(variables.keys())
        missing_vars = template_vars - provided_vars

        # 2. 누락된 변수들에 대한 기본값 생성
        smart_variables = variables.copy()
        for var in missing_vars:
            smart_variables[var] = self._generate_smart_default(var, template)
            self.logger.info(f"스마트 변수 생성: {var} = {smart_variables[var]}")

        try:
            # 3. 안전한 템플릿 치환
            result = template.format(**smart_variables)

            # 4. JSON 형식 요구사항 보존 확인
            if (
                "JSON 형식으로만 응답하세요" not in result
                and "JSON 형식으로만 응답하세요" in template
            ):
                result = self._restore_json_requirements(template, result)

            return result

        except Exception as e:
            self.logger.error(f"템플릿 포맷팅 오류: {e}")
            # 폴백: 단순 치환 방식
            result = template
            for key, value in smart_variables.items():
                result = result.replace(f"{{{key}}}", str(value))
            return result

    def _generate_smart_default(self, var_name: str, template: str) -> str:
        """변수명을 기반으로 스마트한 기본값 생성"""
        var_lower = var_name.lower()

        # JSON 응답 형식 변수들
        if "knowledge_code" in var_lower:
            return "K1|K2|K3|K4 중 선택"
        elif "quality" in var_lower:
            return "answerable|needs_clarify|unanswerable 중 선택"
        elif "missing_fields" in var_lower:
            return "실제 누락된 정보들"
        elif "unit_tags" in var_lower:
            return "실제 단원 태그들"
        elif "policy_flags" in var_lower:
            return "위반 사항"
        elif "reasoning" in var_lower:
            return "실제 분류 근거"
        elif "clarification_questions" in var_lower:
            return "가장 중요한 명료화 질문 1개만"
        elif "clarification_reasoning" in var_lower:
            return "선택한 명료화 질문이 해당 K1~K4 유형의 특성과 missing_fields를 어떻게 해결하는지에 대한 근거"
        elif "unanswerable_response" in var_lower:
            return "unanswerable인 경우 적절한 안내 메시지 (수학 외 영역, 평가윤리, 교과 불일치에 따라 구분)"

        # K1-K4 정의 변수들
        elif "k1_definition" in var_lower:
            return "사실적 지식 - 정의, 용어, 기호, 공식, 값, 단위 등 기본 사실"
        elif "k2_definition" in var_lower:
            return (
                "개념적 지식 - 개념 간 관계, 분류, 원리, 이론, 비교/대조, 오개념 경계"
            )
        elif "k3_definition" in var_lower:
            return "절차적 지식 - 수행 방법, 기술, 알고리즘, 절차, 단계별 과정, 조건과 제약"
        elif "k4_definition" in var_lower:
            return "메타인지적 지식 - 전략적 사고, 문제 접근법, 계획, 반성, 대안 해법"

        # 게이팅 기준 변수들
        elif "answerable_criteria" in var_lower:
            return "교과(수학), 단원·수준 지정, 목표 동사 명확, 충분한 정보 제공"
        elif "needs_clarify_criteria" in var_lower:
            return "범위 과대/목표 불명/수준 불명/용어 혼동, 추가 정보 필요"
        elif "unanswerable_criteria" in var_lower:
            return "수학 외 영역, 평가윤리 위배, 교과 불일치 심각"

        # 기본값
        else:
            return f"[{var_name}]"

    def _restore_json_requirements(
        self, original_template: str, current_result: str
    ) -> str:
        """JSON 형식 요구사항 복원"""
        try:
            if "## 🚨 중요: 반드시 JSON 형식으로만 응답하세요! 🚨" in original_template:
                json_section = original_template.split(
                    "## 🚨 중요: 반드시 JSON 형식으로만 응답하세요! 🚨"
                )[1]
                if "## 🚨 다시 한번 강조" in json_section:
                    json_section = json_section.split("## 🚨 다시 한번 강조")[0]
                return (
                    current_result
                    + "\n\n"
                    + "## 🚨 중요: 반드시 JSON 형식으로만 응답하세요! 🚨"
                    + json_section
                    + "\n\n## 🚨 다시 한번 강조: JSON 형식으로만 응답하세요! 설명이나 추가 텍스트 금지! 🚨"
                )
        except Exception as e:
            self.logger.warning(f"JSON 요구사항 복원 실패: {e}")
        return current_result

    async def _call_llm_with_retry(
        self, messages: List[Dict[str, str]], config: LLMConfig
    ):
        """재시도 로직이 포함된 LLM 호출"""
        last_error = None

        for attempt in range(config.max_retries):
            try:
                self.logger.info(f"LLM 호출 시도 {attempt + 1}/{config.max_retries}")
                self.logger.debug(
                    f"🔧 LLM 설정: provider={config.provider}, model={config.model}, max_tokens={config.max_tokens}, timeout={config.timeout}s"
                )

                # 타임아웃 설정
                start_time = asyncio.get_event_loop().time()

                # 프로바이더별 LLM 호출
                if config.provider == LLMProvider.OPENAI:
                    # OpenAI API 파라미터 구성
                    api_params = {
                        "messages": messages,
                        "model": config.model,
                        "max_completion_tokens": config.max_tokens,
                        "stream": config.stream,
                    }

                    if config.temperature is not None:
                        api_params["temperature"] = config.temperature

                    # JSON 응답 형식 추가
                    if config.json_response:
                        api_params["response_format"] = {"type": "json_object"}

                    response = await asyncio.wait_for(
                        chat_completion(**api_params),
                        timeout=config.timeout,
                    )
                elif config.provider == LLMProvider.ANTHROPIC and anthropic:
                    # Anthropic Claude 호출
                    client = anthropic.AsyncAnthropic(
                        api_key=os.getenv("ANTHROPIC_API_KEY")
                    )

                    # system 메시지와 user 메시지 분리
                    system_message = None
                    user_messages = []

                    for msg in messages:
                        if msg["role"] == "system":
                            system_message = msg["content"]
                        else:
                            user_messages.append(msg)

                    # API 호출 파라미터 구성
                    api_params = {
                        "model": config.model,
                        "max_tokens": config.max_tokens,
                        "messages": user_messages,
                        "stream": config.stream,  # 스트리밍 설정 추가
                        **(
                            {}
                            if config.temperature is None
                            else {"temperature": config.temperature}
                        ),
                    }

                    # system 메시지가 있으면 별도 파라미터로 추가
                    if system_message:
                        api_params["system"] = system_message

                    if config.stream:
                        # 스트리밍 응답 처리
                        response = await asyncio.wait_for(
                            client.messages.create(**api_params), timeout=config.timeout
                        )

                        # Anthropic 스트리밍 응답을 표준 형식으로 변환
                        class AnthropicStreamResponse:
                            def __init__(self, anthropic_stream):
                                self.anthropic_stream = anthropic_stream
                                self._iterated = False

                            def __aiter__(self):
                                return self

                            async def __anext__(self):
                                try:
                                    chunk = await self.anthropic_stream.__anext__()

                                    # 모든 Anthropic 이벤트 타입 로깅
                                    chunk_type = getattr(chunk, "type", "unknown")
                                    logger.debug(
                                        f"🔍 Anthropic 청크 타입: {chunk_type}"
                                    )

                                    # Anthropic 스트리밍 응답을 OpenAI 형식으로 변환
                                    if (
                                        hasattr(chunk, "type")
                                        and chunk.type == "content_block_delta"
                                    ):
                                        # Anthropic content_block_delta를 OpenAI delta 형식으로 변환
                                        class MockDelta:
                                            def __init__(self, content):
                                                self.content = content

                                        class MockChoice:
                                            def __init__(self, delta):
                                                self.delta = delta

                                        class MockChunk:
                                            def __init__(self, choice):
                                                self.choices = [choice]

                                        # Anthropic에서는 delta.text가 아니라 delta.text를 사용
                                        text_content = (
                                            chunk.delta.text
                                            if hasattr(chunk.delta, "text")
                                            else ""
                                        )
                                        delta = MockDelta(text_content)
                                        choice = MockChoice(delta)
                                        return MockChunk(choice)
                                    elif (
                                        hasattr(chunk, "type")
                                        and chunk.type == "message_delta"
                                    ):
                                        # message_delta 이벤트 처리 (stop_reason 포함)
                                        stop_reason = getattr(
                                            chunk.delta, "stop_reason", None
                                        )
                                        if stop_reason:
                                            logger.info(
                                                f"🛑 Anthropic 종료 사유: {stop_reason}"
                                            )
                                        # message_delta는 건너뛰고 다음 청크 대기
                                        return await self.__anext__()
                                    elif (
                                        hasattr(chunk, "type")
                                        and chunk.type == "message_stop"
                                    ):
                                        # 메시지 종료 신호
                                        logger.info(
                                            "✅ Anthropic 스트리밍 정상 종료 (message_stop)"
                                        )
                                        raise StopAsyncIteration
                                    else:
                                        # 다른 타입의 청크는 건너뛰기 (content_block_start, content_block_stop 등)
                                        logger.debug(
                                            f"⏭️ Anthropic 이벤트 건너뛰기: {chunk_type}"
                                        )
                                        return await self.__anext__()
                                except StopAsyncIteration:
                                    raise
                                except Exception as e:
                                    self.logger.error(
                                        f"Anthropic 스트리밍 청크 처리 오류: {e}"
                                    )
                                    raise StopAsyncIteration

                        response = AnthropicStreamResponse(response)
                    else:
                        # 비스트리밍 응답
                        response = await asyncio.wait_for(
                            client.messages.create(**api_params), timeout=config.timeout
                        )
                elif config.provider == LLMProvider.GOOGLE and genai:
                    # Google Gemini 호출
                    self.logger.info(
                        f"🚀 Google Gemini 호출 시작: model={config.model}"
                    )
                    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
                    model = genai.GenerativeModel(config.model)
                    self.logger.info(f"✅ Google Gemini 모델 생성 완료: {config.model}")

                    # Gemini용 메시지 포맷 변환
                    prompt = ""
                    for msg in messages:
                        if msg["role"] == "system":
                            prompt += f"System: {msg['content']}\n\n"
                        elif msg["role"] == "user":
                            prompt += f"User: {msg['content']}\n\n"

                    if config.stream:
                        # Gemini 스트리밍 응답 처리 - 동기 스트리밍 API 사용
                        response_stream = model.generate_content(
                            prompt,
                            generation_config=genai.types.GenerationConfig(
                                max_output_tokens=config.max_tokens,
                                temperature=config.temperature or 0.7,
                            ),
                            stream=True,
                        )

                        # Gemini 스트리밍 응답을 표준 형식으로 변환 (실시간 스트리밍)
                        class GeminiStreamResponse:
                            def __init__(self, gemini_stream, logger):
                                self.gemini_stream = gemini_stream
                                self.logger = logger
                                self._iterated = False
                                self._stream_iterator = None

                            def __aiter__(self):
                                return self

                            async def __anext__(self):
                                try:
                                    # 첫 번째 호출 시 스트림 이터레이터 생성
                                    if self._stream_iterator is None:
                                        self._stream_iterator = iter(self.gemini_stream)

                                    # 실시간으로 다음 청크 가져오기 (동기 이터레이터를 비동기로 감싸기)
                                    chunk = next(self._stream_iterator)

                                    # Gemini 스트리밍 응답을 OpenAI 형식으로 변환
                                    if (
                                        hasattr(chunk, "candidates")
                                        and chunk.candidates
                                    ):
                                        candidate = chunk.candidates[0]
                                        if (
                                            hasattr(candidate, "content")
                                            and candidate.content
                                        ):
                                            if (
                                                hasattr(candidate.content, "parts")
                                                and candidate.content.parts
                                            ):
                                                text_content = candidate.content.parts[
                                                    0
                                                ].text
                                                # 빈 텍스트도 처리하여 연속성 유지
                                                text_content = text_content or ""

                                                class MockDelta:
                                                    def __init__(self, content):
                                                        self.content = content

                                                class MockChoice:
                                                    def __init__(self, delta):
                                                        self.delta = delta

                                                class MockChunk:
                                                    def __init__(self, choice):
                                                        self.choices = [choice]

                                                delta = MockDelta(text_content)
                                                choice = MockChoice(delta)
                                                return MockChunk(choice)

                                    # 빈 청크도 반환하여 연속성 유지
                                    class MockDelta:
                                        def __init__(self, content):
                                            self.content = content

                                    class MockChoice:
                                        def __init__(self, delta):
                                            self.delta = delta

                                    class MockChunk:
                                        def __init__(self, choice):
                                            self.choices = [choice]

                                    delta = MockDelta("")
                                    choice = MockChoice(delta)
                                    return MockChunk(choice)

                                except StopIteration:
                                    raise StopAsyncIteration
                                except Exception as e:
                                    self.logger.error(
                                        f"Gemini 스트리밍 청크 처리 오류: {e}"
                                    )
                                    raise StopAsyncIteration

                        response = GeminiStreamResponse(response_stream, self.logger)
                    else:
                        # 비스트리밍 응답
                        response = await asyncio.wait_for(
                            model.generate_content_async(
                                prompt,
                                generation_config=genai.types.GenerationConfig(
                                    max_output_tokens=config.max_tokens,
                                    temperature=config.temperature or 0.7,
                                ),
                            ),
                            timeout=config.timeout,
                        )
                elif config.provider == LLMProvider.MCP:
                    # MCP 서버 호출 (penGPT) - OpenAI 호환 API만 사용
                    mcp_openai_base_url = os.getenv("MCP_OPENAI_BASE_URL")

                    # OpenAI 호환 API URL이 없으면 기본 MCP 서버 URL의 /v1 엔드포인트 사용
                    if not mcp_openai_base_url:
                        base_url = os.getenv(
                            "MCP_SERVER_URL", "http://192.168.1.105:5555"
                        )
                        mcp_openai_base_url = f"{base_url.rstrip('/')}/v1"

                    # OpenAI 호환 API 사용
                    from openai import AsyncOpenAI

                    self.logger.info(
                        f"🔗 MCP OpenAI 호환 API 사용: {mcp_openai_base_url}"
                    )
                    client = AsyncOpenAI(
                        api_key=os.getenv(
                            "MCP_API_KEY", os.getenv("OPENAI_API_KEY", "dummy-key")
                        ),
                        base_url=mcp_openai_base_url,
                    )

                    # OpenAI 호환 API 호출 - messages 배열 그대로 전송
                    api_params = {
                        "model": config.model or os.getenv("MCP_MODEL", "penGPT"),
                        "messages": messages,  # OpenAI 표준 형식 그대로 사용
                        "max_completion_tokens": config.max_tokens,
                        "stream": config.stream,
                    }

                    if config.temperature is not None:
                        api_params["temperature"] = config.temperature

                    # JSON 응답 형식 추가
                    if config.json_response:
                        api_params["response_format"] = {"type": "json_object"}

                    response = await asyncio.wait_for(
                        client.chat.completions.create(**api_params),
                        timeout=config.timeout,
                    )

                else:
                    raise Exception(f"지원하지 않는 LLM 프로바이더: {config.provider}")
                end_time = asyncio.get_event_loop().time()
                self.logger.debug(f"⏱️ LLM 응답 시간: {end_time - start_time:.2f}초")

                # 스트리밍 응답인지 확인
                if config.stream:
                    # 스트리밍 응답인 경우 그대로 반환 (AnswerGenerator에서 처리)
                    self.logger.debug(f"📡 스트리밍 응답 반환: {type(response)}")
                    return response

                # 비스트리밍 응답 처리
                if config.provider == LLMProvider.OPENAI:
                    if hasattr(response, "choices") and response.choices:
                        content = response.choices[0].message.content
                        output_tokens = count_tokens(content or "", config.model)
                        self.logger.info(f"📤 출력 토큰 수: {output_tokens}")
                        self.logger.info(f"📄 LLM 응답 내용: {repr(content)}")
                    else:
                        self.logger.info(f"📄 LLM 응답 타입: {type(response)}")
                elif config.provider == LLMProvider.ANTHROPIC:
                    if hasattr(response, "content") and response.content:
                        content = response.content[0].text
                        output_tokens = count_tokens(content or "", config.model)
                        self.logger.info(f"📤 출력 토큰 수: {output_tokens}")
                        self.logger.info(f"📄 LLM 응답 내용: {repr(content)}")
                        # Anthropic 응답을 표준 형식으로 변환
                        response = type(
                            "Response",
                            (),
                            {
                                "choices": [
                                    type(
                                        "Choice",
                                        (),
                                        {
                                            "message": type(
                                                "Message", (), {"content": content}
                                            )()
                                        },
                                    )()
                                ]
                            },
                        )()
                    else:
                        self.logger.info(f"📄 LLM 응답 타입: {type(response)}")
                elif config.provider == LLMProvider.GOOGLE:
                    self.logger.info(
                        f"🎯 Google Gemini 응답 처리: model={config.model}"
                    )
                    if hasattr(response, "candidates") and response.candidates:
                        candidate = response.candidates[0]
                        if hasattr(candidate, "content") and candidate.content:
                            if (
                                hasattr(candidate.content, "parts")
                                and candidate.content.parts
                            ):
                                content = candidate.content.parts[0].text
                                output_tokens = count_tokens(
                                    content or "", config.model
                                )
                                self.logger.info(f"📤 출력 토큰 수: {output_tokens}")
                                self.logger.info(
                                    f"📄 Google Gemini 응답 내용: {repr(content)}"
                                )
                                # Google Gemini 응답을 표준 형식으로 변환
                                response = type(
                                    "Response",
                                    (),
                                    {
                                        "choices": [
                                            type(
                                                "Choice",
                                                (),
                                                {
                                                    "message": type(
                                                        "Message",
                                                        (),
                                                        {"content": content},
                                                    )()
                                                },
                                            )()
                                        ]
                                    },
                                )()
                            else:
                                self.logger.warning(
                                    f"📄 Google Gemini content.parts가 없음: {candidate.content}"
                                )
                        else:
                            self.logger.warning(
                                f"📄 Google Gemini content가 없음: {candidate}"
                            )
                    else:
                        self.logger.info(
                            f"📄 Google Gemini 응답 타입: {type(response)}"
                        )
                elif config.provider == LLMProvider.MCP:
                    if hasattr(response, "choices") and response.choices:
                        content = response.choices[0].message.content
                        output_tokens = count_tokens(content or "", config.model)
                        self.logger.info(f"📤 출력 토큰 수: {output_tokens}")
                        self.logger.info(f"📄 LLM 응답 내용: {repr(content)}")
                    else:
                        self.logger.info(f"📄 LLM 응답 타입: {type(response)}")

                return response

            except asyncio.TimeoutError:
                last_error = f"타임아웃 (시도 {attempt + 1})"
                self.logger.warning(f"LLM 호출 타임아웃: {last_error}")
            except Exception as e:
                last_error = str(e)
                self.logger.warning(f"LLM 호출 실패: {last_error}")

            # 마지막 시도가 아니면 대기
            if attempt < config.max_retries - 1:
                await asyncio.sleep(config.retry_delay)

        # 모든 재시도 실패
        raise Exception(f"LLM 호출 최종 실패: {last_error}")

    async def _process_streaming_response(
        self, stream, config: LLMConfig, session_id: int = None, streams_client=None
    ) -> str:
        """스트리밍 응답을 처리하여 최종 content 반환 (실시간 청크 전송 포함)"""
        try:
            full_content = ""
            chunk_count = 0

            self.logger.info(f"🚀 스트리밍 처리 시작: provider={config.provider.value}")

            async for chunk in stream:
                try:
                    content = ""

                    # OpenAI 형식 (OpenAI, Anthropic, MCP)
                    if (
                        hasattr(chunk, "choices")
                        and chunk.choices
                        and len(chunk.choices) > 0
                    ):
                        delta = chunk.choices[0].delta
                        if hasattr(delta, "content"):
                            content = delta.content or ""

                    # Google Gemini 형식
                    elif hasattr(chunk, "candidates") and chunk.candidates:
                        candidate = chunk.candidates[0]
                        if hasattr(candidate, "content") and candidate.content:
                            if (
                                hasattr(candidate.content, "parts")
                                and candidate.content.parts
                            ):
                                content = candidate.content.parts[0].text or ""

                    # 직접 content 속성이 있는 경우 (일부 프로바이더)
                    elif hasattr(chunk, "content"):
                        content = chunk.content or ""

                    # content가 리스트인 경우 문자열로 변환
                    if isinstance(content, list):
                        content = "".join(str(item) for item in content)

                    # content가 문자열이 아닌 경우 문자열로 변환
                    if not isinstance(content, str):
                        content = str(content) if content else ""

                    # 빈 청크도 카운트에 포함 (연속성 유지)
                    chunk_count += 1
                    full_content += content

                    # 실시간 청크 전송 (세션 ID가 있고 streams_client가 있는 경우)
                    # content가 있거나 빈 청크라도 전송 (연속성 유지)
                    if session_id and streams_client:
                        try:
                            # 통일된 streaming_chunk 타입으로 전송
                            stream_data = {
                                "type": "streaming_chunk",
                                "session_id": session_id,
                                "content": content,
                                "chunk_index": chunk_count - 1,  # 0부터 시작
                                "is_final": False,
                                "timestamp": datetime.now().isoformat(),
                            }

                            # request_id가 있으면 추가
                            request_id_param = getattr(
                                self, "_current_request_id", None
                            )
                            if request_id_param:
                                stream_data["request_id"] = request_id_param

                            await streams_client.send_to_backend_stream(stream_data)
                            # if content:
                            #     self.logger.info(f"📤 스트리밍 청크 전송: {chunk_count} - {content[:50]}...")
                            # else:
                            #     self.logger.info(f"📤 스트리밍 빈 청크 전송: {chunk_count}")
                        except Exception as e:
                            self.logger.warning(f"실시간 청크 전송 실패: {e}")
                    else:
                        self.logger.warning(
                            f"청크 전송 실패: session_id={session_id}, streams_client={streams_client}"
                        )

                except Exception as chunk_error:
                    self.logger.error(f"청크 처리 오류: {chunk_error}")
                    # 오류가 발생해도 청크 카운트는 증가시켜서 연속성 유지
                    chunk_count += 1

            self.logger.info(
                f"✅ 스트리밍 처리 완료: 총 {chunk_count}개 청크, {len(full_content)}자"
            )
            self.logger.info(
                f"🔍 스트리밍 완료 - full_content 끝부분(마지막 100자): ...{full_content[-100:] if len(full_content) > 100 else full_content}"
            )

            # 최종 청크 전송 (스트리밍 완료 신호)
            if session_id and streams_client:
                try:
                    # 통일된 streaming_complete 타입으로 완료 신호 전송
                    await streams_client.send_to_backend_stream(
                        {
                            "type": "streaming_complete",
                            "session_id": session_id,
                            "full_response": full_content,
                            "total_chunks": chunk_count,
                            "is_final": True,
                            "timestamp": datetime.now().isoformat(),
                        }
                    )
                    self.logger.info(
                        f"📤 스트리밍 완료 신호 전송: 세션 {session_id}, 총 {chunk_count}개 청크, full_response 길이 {len(full_content)}자"
                    )
                except Exception as e:
                    self.logger.warning(f"스트리밍 완료 신호 전송 실패: {e}")

            # LLM 응답에서 text 부분만 추출 (MCP와 일반 모델 구분)
            try:
                import json
                import ast

                # MCP 응답 형태: [{'type': 'text', 'text': '...'}]
                if (
                    full_content.strip().startswith("[")
                    and "type" in full_content
                    and "text" in full_content
                ):
                    # MCP 응답 파싱
                    try:
                        response_list = ast.literal_eval(full_content)
                        if isinstance(response_list, list) and len(response_list) > 0:
                            first_item = response_list[0]
                            if isinstance(first_item, dict) and "text" in first_item:
                                full_content = first_item["text"]
                                self.logger.info("MCP 응답에서 text 부분 추출 완료")
                    except (ValueError, SyntaxError) as e:
                        self.logger.warning(f"MCP 응답 파싱 실패: {e}")
                # 일반 JSON 형태: {'type': 'text', 'text': '...'}
                elif (
                    full_content.strip().startswith("{")
                    and "type" in full_content
                    and "text" in full_content
                ):
                    response_data = json.loads(full_content)
                    if isinstance(response_data, dict) and "text" in response_data:
                        full_content = response_data["text"]
                        self.logger.info("일반 JSON 응답에서 text 부분 추출 완료")
                else:
                    self.logger.info("LLM 응답이 JSON 형태가 아님, 그대로 사용")
            except Exception as e:
                self.logger.warning(f"LLM 응답 파싱 실패, 원본 사용: {e}")

            return full_content

        except Exception as e:
            self.logger.error(f"스트리밍 처리 오류: {e}")
            return f"스트리밍 처리 중 오류가 발생했습니다: {str(e)}"

    @staticmethod
    def _create_mcp_response(
        content: str, is_streaming: bool = False, gpt5_streaming: bool = False
    ):
        """MCP 응답을 OpenAI 형식으로 변환하는 헬퍼 메서드"""

        class MockChoice:
            def __init__(self, content):
                self.message = MockMessage(content)
                # 스트리밍을 위한 delta 속성 추가
                self.delta = MockDelta(content)

        class MockMessage:
            def __init__(self, content):
                self.content = content

        class MockDelta:
            def __init__(self, content):
                self.content = content

        class MockResponse:
            def __init__(self, content, is_streaming=False, gpt5_streaming=False):
                self.choices = [MockChoice(content)]
                # 기존 코드 호환성을 위한 속성들 추가
                self.text = content  # 일부 코드에서 사용
                self.content = content  # 일부 코드에서 사용
                # 문자열로도 접근 가능하도록
                self.__str__ = lambda: content
                self.__repr__ = lambda: f"MockResponse('{content[:50]}...')"
                self._iterated = False
                self._is_streaming = is_streaming
                self._gpt5_streaming = gpt5_streaming
                self._content = content
                self._chunk_index = 0

                # 스트리밍 정보 로깅
                if is_streaming or gpt5_streaming:
                    print(
                        f"🌊 MCP 스트리밍 응답 감지: streaming={is_streaming}, gpt5_streaming={gpt5_streaming}"
                    )
                    # 텍스트를 청크로 나누기 (한 번에 10-20자씩)
                    self._chunks = LLMTool._split_into_chunks(content, chunk_size=15)
                    print(f"📝 텍스트를 {len(self._chunks)}개 청크로 분할")

            def __aiter__(self):
                """스트리밍을 위한 async iterator"""
                return self

            async def __anext__(self):
                """스트리밍을 위한 async next"""
                if not self._is_streaming and not self._gpt5_streaming:
                    # 스트리밍이 아닌 경우 한 번만 반환
                    if not self._iterated:
                        self._iterated = True
                        return self
                    raise StopAsyncIteration

                # 스트리밍인 경우 청크 단위로 반환
                if self._chunk_index < len(self._chunks):
                    chunk = self._chunks[self._chunk_index]
                    self._chunk_index += 1

                    # 청크 내용으로 MockResponse 생성 (로깅 없이)
                    chunk_response = MockResponse(
                        chunk, is_streaming=False, gpt5_streaming=False
                    )
                    chunk_response._iterated = True  # 청크는 한 번만 반환
                    return chunk_response

                raise StopAsyncIteration

        return MockResponse(content, is_streaming, gpt5_streaming)

    @staticmethod
    def _split_into_chunks(text: str, chunk_size: int = 15) -> list:
        """텍스트를 청크 단위로 나누는 헬퍼 메서드"""
        chunks = []
        for i in range(0, len(text), chunk_size):
            chunk = text[i : i + chunk_size]
            chunks.append(chunk)
        return chunks

    @staticmethod
    async def _call_mcp_realtime_streaming(
        mcp_url: str, messages: List[Dict[str, str]], config: LLMConfig
    ):
        """MCP 실시간 스트리밍 엔드포인트 호출"""

        # API 스트리밍 요청 데이터 구성
        mcp_data = {
            "message": f"System: {messages[0]['content']}\n\nUser: {messages[-1]['content']}"
            if messages and messages[0]["role"] == "system"
            else messages[-1]["content"]
            if messages
            else "",
            "chat_hash": "maice-session",
        }

        logger.debug(f"🌊 API 스트리밍 요청: {mcp_url}")
        logger.debug(f"🌊 Message: {mcp_data['message'][:100]}...")

        class RealtimeStreamingResponse:
            def __init__(self, mcp_url: str, mcp_data: dict, config: LLMConfig):
                self.mcp_url = mcp_url
                self.mcp_data = mcp_data
                self.config = config
                self._session = None
                self._response = None
                self._is_streaming = True
                self._gpt5_streaming = True
                self._session_id = (
                    f"session_{id(self)}_{datetime.now().timestamp()}"  # 고유 세션 ID
                )
                self._buffer = ""  # 청크 버퍼링을 위한 버퍼
                self._buffer_size = 50  # 최소 50자 이상 모일 때 전송
                self._completed = False  # 스트리밍 완료 플래그 추가

            async def __aenter__(self):
                self._client = httpx.AsyncClient(timeout=config.timeout)
                return self

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if self._client:
                    await self._client.aclose()
                if self._session:
                    await self._session.close()

            def __aiter__(self):
                return self

            async def __anext__(self):
                # 스트리밍이 완료된 경우 즉시 종료
                if self._completed:
                    raise StopAsyncIteration

                if not self._session:
                    # 각 요청마다 독립적인 aiohttp 세션 생성
                    timeout = aiohttp.ClientTimeout(total=self.config.timeout)
                    self._session = aiohttp.ClientSession(
                        timeout=timeout,
                        connector=aiohttp.TCPConnector(
                            limit=100, limit_per_host=30
                        ),  # 연결 풀 설정
                    )
                    logger.info(f"🔗 새로운 aiohttp 세션 생성: {self._session_id}")

                if not self._response:
                    # aiohttp로 실시간 SSE 요청
                    self._response = await self._session.post(
                        self.mcp_url,
                        json=self.mcp_data,
                        headers={"Content-Type": "application/json"},
                    )
                    self._response.raise_for_status()

                # aiohttp로 실시간 라인 읽기
                try:
                    line_bytes = await self._response.content.readline()
                    if not line_bytes:
                        # 스트림 종료
                        logger.info(f"✅ 스트림 종료 ({self._session_id})")
                        self._completed = True
                        if self._session:
                            await self._session.close()
                        raise StopAsyncIteration

                    line = line_bytes.decode("utf-8").strip()
                    if line:  # 빈 라인 체크 추가
                        logger.info(f"🔍 aiohttp SSE 라인: {line[:50]}...")

                    if line and line.startswith("data: "):
                        data_str = line[6:]  # "data: " 제거

                        try:
                            data = json.loads(data_str)
                            logger.info(f"🔍 aiohttp SSE 데이터: {data}")

                            if data.get("type") == "delta":
                                # 델타 청크 생성 후 즉시 반환
                                text_content = data.get("text", "")

                                # JSON 메타데이터가 포함된 경우 필터링
                                if text_content and (
                                    text_content.startswith(
                                        '{"name":"message_output_created"'
                                    )
                                    or text_content.startswith(
                                        '{"type":"stream_complete"'
                                    )
                                    or text_content.startswith(
                                        '{"type":"run_item_stream_event"'
                                    )
                                    or "message_output_created" in text_content
                                    or "run_item_stream_event" in text_content
                                ):
                                    logger.debug(
                                        f"🔍 JSON 메타데이터 필터링: {text_content[:50]}..."
                                    )
                                    # JSON 메타데이터는 건너뛰기
                                    return await self.__anext__()

                                # 실제 텍스트만 처리 (버퍼링 적용) - 줄바꿈도 포함
                                if text_content is not None and text_content != "":
                                    # 버퍼에 텍스트 추가
                                    self._buffer += text_content

                                    # 버퍼가 충분히 쌓이거나 문장이 끝나는 경우 전송
                                    if len(
                                        self._buffer
                                    ) >= self._buffer_size or self._buffer.endswith(
                                        (".", "!", "?", "。", "!", "?", "\n")
                                    ):
                                        logger.info(
                                            f"📤 aiohttp 버퍼링된 청크 전송: '{self._buffer}' (길이: {len(self._buffer)})"
                                        )
                                        chunk_response = LLMTool._create_mcp_response(
                                            self._buffer,
                                            is_streaming=True,
                                            gpt5_streaming=True,
                                        )
                                        self._buffer = ""  # 버퍼 초기화
                                        return chunk_response
                                    else:
                                        # 아직 전송하지 않고 다음 청크 대기
                                        return await self.__anext__()
                                else:
                                    # 빈 텍스트는 건너뛰기
                                    return await self.__anext__()

                            elif data.get("type") == "completed":
                                # 스트리밍 완료 - 남은 버퍼 전송
                                if self._buffer:
                                    logger.info(
                                        f"📤 aiohttp 최종 버퍼 전송: '{self._buffer}' (길이: {len(self._buffer)})"
                                    )
                                    chunk_response = LLMTool._create_mcp_response(
                                        self._buffer,
                                        is_streaming=True,
                                        gpt5_streaming=True,
                                    )
                                    self._buffer = ""
                                    return chunk_response

                                logger.info(
                                    f"✅ aiohttp 스트리밍 완료 ({self._session_id})"
                                )
                                self._completed = True  # 완료 플래그 설정
                                if self._session:
                                    await self._session.close()
                                raise StopAsyncIteration

                        except json.JSONDecodeError:
                            pass

                    # delta가 아닌 라인은 다음 라인 요청
                    return await self.__anext__()

                except StopAsyncIteration:
                    # 정상적인 스트리밍 완료
                    self._completed = True
                    if self._session:
                        await self._session.close()
                    raise
                except Exception as e:
                    error_msg = str(e) if e else "알 수 없는 오류"
                    logger.error(f"aiohttp SSE 오류 ({self._session_id}): {error_msg}")
                    self._completed = True  # 에러가 발생해도 완료로 처리
                    if self._session:
                        await self._session.close()
                    raise StopAsyncIteration

        return RealtimeStreamingResponse(mcp_url, mcp_data, config)

    # 시뮬레이션된 스트리밍 코드 제거됨 - 이제 실제 MCP 실시간 스트리밍 사용


class SpecializedLLMTool(LLMTool):
    """특화된 LLM 툴들"""

    @staticmethod
    def _get_provider_from_env():
        """환경변수에서 LLM_PROVIDER 읽기"""
        env_provider = os.getenv("LLM_PROVIDER", "openai").lower()
        if env_provider == "anthropic":
            return LLMProvider.ANTHROPIC
        elif env_provider == "google":
            return LLMProvider.GOOGLE
        elif env_provider == "mcp":
            return LLMProvider.MCP
        else:
            return LLMProvider.OPENAI

    @classmethod
    def create_classifier_tool(cls) -> "SpecializedLLMTool":
        """질문 분류용 LLM 툴"""
        config = LLMConfig(
            provider=cls._get_provider_from_env(),
            max_tokens=5000,  # 3000 → 5000으로 증가 (JSON 응답 완성 보장)
            timeout=300,  # 120 → 300초로 증가 (응답 완성 보장)
            max_retries=5,  # 3 → 5로 증가
            stream=False,  # 스트리밍 비활성화 (JSON 응답을 위해)
        )

        template = PromptTemplate(
            system_prompt="당신은 수학 질문 분류 전문가입니다.",
            user_template="질문을 분류해주세요: {question}",
        )

        return cls("classifier_llm", config, template)

    @classmethod
    def create_answer_generator_tool(cls) -> "SpecializedLLMTool":
        """답변 생성용 LLM 툴"""
        config = LLMConfig(
            provider=cls._get_provider_from_env(),
            max_tokens=4000,  # 한글은 토큰이 많이 필요하므로 충분하게 설정
            timeout=60,  # Anthropic은 느리므로 타임아웃 증가
            max_retries=3,
            stream=True,
        )

        template = PromptTemplate(
            system_prompt="당신은 수학 교육 전문가입니다.",
            user_template="학생 질문에 답변해주세요: {question}",
        )

        return cls("answer_generator_llm", config, template)

    @classmethod
    def create_observer_tool(cls) -> "SpecializedLLMTool":
        """학습 관찰 및 요약용 LLM 툴"""
        config = LLMConfig(
            provider=cls._get_provider_from_env(),
            max_tokens=1000,  # 요약용으로 적당한 크기
            timeout=60,
            max_retries=2,
            stream=False,  # JSON 응답을 위해 스트리밍 비활성화
        )

        template = PromptTemplate(
            system_prompt="당신은 학습 과정 요약 전문가입니다.",
            user_template="학습 대화를 요약해주세요: {conversation}",
        )

        return cls("observer_llm", config, template)

    @classmethod
    def create_freetalker_tool(cls) -> "SpecializedLLMTool":
        """프리토커 에이전트용 LLM 툴"""
        config = LLMConfig(
            provider=cls._get_provider_from_env(),
            max_tokens=4000,  # 프리패스 모드용 충분한 토큰
            timeout=60,  # 적당한 타임아웃
            max_retries=3,
            stream=True,  # 스트리밍 활성화
        )

        template = PromptTemplate(
            system_prompt="필요할 때만 수학 수식을 LaTeX 형식($수식$)으로 작성해주세요.",
            user_template="{question}",
        )

        return cls("freetalker_llm", config, template)

    @classmethod
    def create_question_improvement_tool(cls) -> "SpecializedLLMTool":
        """질문 개선용 LLM 툴"""
        config = LLMConfig(
            provider=cls._get_provider_from_env(),
            max_tokens=3000,  # 800 → 2000으로 증가 (입력 토큰 2631개 + 응답 토큰 여유분)
            timeout=60,  # 30 → 60초로 증가 (gpt-5-mini는 응답이 느림)
            max_retries=2,
        )

        template = PromptTemplate(
            system_prompt="당신은 질문 개선 전문가입니다.",
            user_template="질문을 개선해주세요: {question}",
        )

        return cls("question_improvement_llm", config, template)
