"""
통일된 YAML 구조를 위한 개선된 프롬프트 빌더
"""

import re
import yaml
from typing import Dict, Any, Optional, List
import os
import logging
from pathlib import Path


class PromptBuilder:
    """개선된 프롬프트 빌더 - 통일된 YAML 구조 사용"""
    
    def __init__(self, yaml_data: Dict[str, Any]):
        self.config = yaml_data
        self._logger = logging.getLogger(__name__)
        # 환경변수로 프롬프트 로깅 제어 (기본 비활성화)
        self._log_prompts = os.getenv("MAICE_LOG_LLM_PROMPTS", "false").lower() in ("1", "true", "yes")
        # 프로덕션에서는 강제 비활성화 (Jenkins 설정 불필요)
        environment = os.getenv("ENVIRONMENT", "development").lower()
        if environment in ("production", "prod"):
            self._log_prompts = False
        if self._log_prompts:
            self._logger.debug(f"🔍 PromptBuilder 초기화: {list(self.config.keys())}")
        
    def build_prompt(self, 
                    template_name: str, 
                    variables: Dict[str, Any] = None,
                    agent_name: str = None) -> Dict[str, str]:
        """
        프롬프트 템플릿을 빌드하고 변수를 주입
        
        Args:
            template_name: 사용할 템플릿 이름 (예: "classification")
            variables: 주입할 변수들
            agent_name: 에이전트 이름 (YAML에서 에이전트별 설정을 가져올 때 사용)
            
        Returns:
            {"system": "시스템 프롬프트", "user": "사용자 프롬프트"}
        """
        try:
            if self._log_prompts:
                self._logger.debug(f"🔍 build_prompt 호출: template_name={template_name}, agent_name={agent_name}")
            
            # 1. 에이전트 설정 가져오기
            agent_config = self.config.get(agent_name, {})
            if not agent_config:
                raise ValueError(f"에이전트 설정을 찾을 수 없습니다: {agent_name}")
            
            # 2. 템플릿 가져오기
            templates = agent_config.get("templates", {})
            template = templates.get(template_name, {})
            if not template:
                raise ValueError(f"템플릿을 찾을 수 없습니다: {template_name}")
            
            # 3. 설정 변수들 가져오기 (settings 섹션에서)
            settings = agent_config.get("settings", {})
            
            # 4. 가이드라인 변수들 가져오기 (guidelines 섹션에서)
            guidelines = agent_config.get("guidelines", {})
            
            # 5. 변수 병합 (설정 변수 + 가이드라인 변수 + 사용자 변수)
            merged_variables = {}
            merged_variables.update(self._flatten_dict(settings, "settings_"))
            merged_variables.update(self._flatten_dict(guidelines, "guidelines_"))
            merged_variables.update(variables or {})
            
            if self._log_prompts:
                self._logger.debug(f"🔍 병합된 변수 수: {len(merged_variables)}")
            
            # 6. 템플릿 치환
            system_prompt = self._format_template(template.get("system", ""), merged_variables)
            user_prompt = self._format_template(template.get("user", ""), merged_variables)
            
            # 디버그: 전체 프롬프트 출력 (옵션)
            if self._log_prompts:
                self._logger.debug(f"🔍 최종 system_prompt 길이: {len(system_prompt)}")
                self._logger.debug(f"🔍 system_prompt 끝부분: ...{system_prompt[-200:]}")
                self._logger.debug(f"🔍 최종 user_prompt: {user_prompt}")
            
            return {
                "system": system_prompt,
                "user": user_prompt
            }
            
        except Exception as e:
            self._logger.error(f"🔍 build_prompt 오류: {e}")
            raise Exception(f"프롬프트 빌드 실패: {e}")
    
    def _flatten_dict(self, data: Dict[str, Any], prefix: str = "") -> Dict[str, Any]:
        """중첩된 딕셔너리를 평면화하여 변수로 변환"""
        variables = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 중첩된 딕셔너리는 재귀적으로 처리
                nested_vars = self._flatten_dict(value, f"{prefix}{key}_")
                variables.update(nested_vars)
            elif isinstance(value, list):
                # 리스트는 그대로 유지
                variables[f"{prefix}{key}"] = value
            else:
                # 기본값은 문자열로 변환
                variables[f"{prefix}{key}"] = str(value) if value is not None else ""
        
        return variables
    
    def _format_template(self, template: str, variables: Dict[str, Any]) -> str:
        """템플릿 포맷팅 - 안전한 변수 치환"""
        if not template:
            return template
        
        try:
            # 1차 시도: 표준 format 사용
            return template.format(**variables)
        except KeyError as e:
            # 2차 시도: 누락된 변수는 기본값으로 치환
            result = template
            for key, value in variables.items():
                result = result.replace(f"{{{key}}}", str(value))
            
            # 3차 시도: 남은 변수들을 빈 문자열로 치환
            # JSON 형식의 중괄호는 변수로 인식하지 않도록 수정
            remaining_vars = re.findall(r'\{([^}]+)\}', result)
            for var in remaining_vars:
                # JSON 형식의 중괄호가 아닌 실제 변수만 치환
                if not (var.startswith('"') and var.endswith('"')) and not var.isdigit() and not var in ['knowledge_code', 'quality', 'missing_fields', 'unit_tags', 'policy_flags', 'reasoning', 'clarification_questions', 'clarification_reasoning', 'unanswerable_response', '위반 사항']:
                    result = result.replace(f"{{{var}}}", "")
            
            return result
    
    def get_setting(self, agent_name: str, key: str, default: Any = None) -> Any:
        """설정 값 조회"""
        agent_config = self.config.get(agent_name, {})
        settings = agent_config.get("settings", {})
        return self._get_nested_value(settings, key, default)
    
    def _get_nested_value(self, data: Dict[str, Any], key: str, default: Any = None) -> Any:
        """중첩된 키로 값 조회 (예: "common.tone")"""
        keys = key.split('.')
        current = data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
