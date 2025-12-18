"""
프롬프트 설정 파일 로더
"""

import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)

class PromptConfigLoader:
    """프롬프트 설정 파일 로더"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # 여러 가능한 경로를 시도
            import os
            current_dir = Path(os.getcwd())
            possible_paths = [
                Path("agent/agents"),  # 상대 경로
                Path("/app/agents"),  # Docker 컨테이너 내부 (올바른 경로)
                current_dir / "agents",  # 현재 작업 디렉토리 아래 agents
                current_dir / "agent" / "agents",  # 현재 작업 디렉토리 기준
            ]
            
            for path in possible_paths:
                if path.exists():
                    self.config_dir = path
                    break
            else:
                # 기본값
                self.config_dir = Path("agent/agents")
                logger.warning(f"존재하는 경로를 찾지 못했습니다. 기본값 사용: {self.config_dir}")
        else:
            self.config_dir = Path(config_dir)
        
        self.configs = {}
        self._load_all_configs()
    
    def _load_all_configs(self):
        """모든 설정 파일 로드"""
        try:
            if not self.config_dir.exists():
                logger.error(f"설정 디렉토리가 존재하지 않습니다: {self.config_dir}")
                return
            
            for agent_dir in self.config_dir.iterdir():
                if agent_dir.is_dir() and not agent_dir.name.startswith('_'):
                    prompts_dir = agent_dir / "prompts"
                    
                    if prompts_dir.exists():
                        config_file = prompts_dir / "config.yaml"
                        
                        if config_file.exists():
                            try:
                                with open(config_file, 'r', encoding='utf-8') as f:
                                    raw_config = yaml.safe_load(f)
                                    self.configs[agent_dir.name] = raw_config
                            except Exception as e:
                                logger.error(f"YAML 파일 파싱 오류 ({agent_dir.name}): {e}")
            
        except Exception as e:
            logger.error(f"설정 파일 로드 중 오류: {e}")
    
    def get_agent_config(self, agent_name: str) -> Dict[str, Any]:
        """에이전트별 설정 조회"""
        return self.configs.get(agent_name, {})
    
    def get_prompt_config(self, agent_name: str, prompt_path: str) -> Any:
        """특정 프롬프트 설정 조회 (점 표기법 지원)"""
        config = self.configs.get(agent_name, {})
        
        # 점 표기법으로 중첩된 설정 접근
        keys = prompt_path.split('.')
        for key in keys:
            if isinstance(config, dict) and key in config:
                config = config[key]
            else:
                logger.warning(f"설정을 찾을 수 없음: {agent_name}.{prompt_path}")
                return None
        
        return config
    
    def get_system_prompt(self, agent_name: str, prompt_type: str = "base") -> Optional[str]:
        """시스템 프롬프트 조회"""
        return self.get_prompt_config(agent_name, f"system_prompts.{prompt_type}")
    
    def get_user_prompt_template(self, agent_name: str, prompt_type: str) -> Optional[str]:
        """사용자 프롬프트 템플릿 조회"""
        return self.get_prompt_config(agent_name, f"user_prompts.{prompt_type}")
    
    def reload_config(self, agent_name: str = None):
        """설정 파일 재로드"""
        try:
            if agent_name:
                agent_dir = self.config_dir / agent_name
                if agent_dir.exists():
                    prompts_dir = agent_dir / "prompts"
                    config_file = prompts_dir / "config.yaml"
                    if config_file.exists():
                        with open(config_file, 'r', encoding='utf-8') as f:
                            raw_config = yaml.safe_load(f)
                            
                            # YAML 구조를 그대로 유지
                            self.configs[agent_name] = raw_config
                            
                            logger.info(f"설정 파일 재로드 완료: {agent_name}")
            else:
                self._load_all_configs()
        except Exception as e:
            logger.error(f"설정 파일 재로드 중 오류: {e}")
    
    def save_config(self, agent_name: str, config_data: Dict[str, Any]):
        """설정 파일 저장"""
        try:
            prompts_dir = self.config_dir / agent_name / "prompts"
            prompts_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = prompts_dir / "config.yaml"
            with open(config_file, 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
            
            # 메모리에도 업데이트
            self.configs[agent_name] = config_data
            logger.info(f"설정 파일 저장 완료: {agent_name}")
            
        except Exception as e:
            logger.error(f"설정 파일 저장 중 오류: {e}")
    
    def list_available_agents(self) -> List[str]:
        """사용 가능한 에이전트 목록 조회"""
        return list(self.configs.keys())
    
    def list_available_prompts(self, agent_name: str) -> List[str]:
        """에이전트별 사용 가능한 프롬프트 목록 조회"""
        config = self.configs.get(agent_name, {})
        prompts = []
        
        if "system_prompts" in config:
            prompts.extend([f"system.{k}" for k in config["system_prompts"].keys()])
        
        if "user_prompts" in config:
            prompts.extend([f"user.{k}" for k in config["user_prompts"].keys()])
        
        return prompts
