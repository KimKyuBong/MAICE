"""
LaTeX 형식 정리 도구
텍스트의 LaTeX 수식을 정리하는 도구
"""

import logging
import re
from typing import Dict, Any
from ..base_agent import Tool

logger = logging.getLogger(__name__)

class LaTeXFormatterTool(Tool):
    """LaTeX 형식 정리 도구"""
    
    def __init__(self):
        super().__init__(
            name="latex_formatter", 
            description="텍스트의 LaTeX 수식을 정리합니다"
        )
        self.logger = logging.getLogger(__name__)
    
    async def execute(self, content: str) -> Dict[str, Any]:
        """LaTeX 형식 정리 실행"""
        try:
            self.logger.info(f"LaTeX 형식 정리 시작: {len(content)}자")
            
            # LaTeX 형식 정리 로직
            formatted_content = self._format_latex(content)
            
            result = {
                "original_content": content,
                "formatted_content": formatted_content,
                "latex_count": content.count("$"),
                "success": True
            }
            
            self.logger.info(f"LaTeX 형식 정리 완료: {result['latex_count']}개 수식")
            return result
            
        except Exception as e:
            self.logger.error(f"LaTeX 형식 정리 오류: {str(e)}", exc_info=True)
            return {
                "original_content": content,
                "formatted_content": content,
                "latex_count": 0,
                "success": False,
                "error": str(e)
            }
    
    def _format_latex(self, content: str) -> str:
        """LaTeX 수식 형식 정리"""
        # 기본적인 LaTeX 정리 로직
        # 실제로는 더 복잡한 정리가 필요할 수 있음
        
        # 인라인 수식 정리
        content = re.sub(r'\$([^$]+)\$', r'$\1$', content)
        
        # 블록 수식 정리
        content = re.sub(r'\$\$([^$]+)\$\$', r'$$\1$$', content)
        
        return content 