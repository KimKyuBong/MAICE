"""
완전한 Desmos MCP 시스템 통합
모든 Desmos API v1.11 기능을 MCP 스타일로 제공하는 통합 시스템
"""

import logging
import json
import asyncio
import uuid
import os
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime

# 모든 Desmos 도구 모듈 import
from .desmos_mcp_system import (
    DesmosToolBase, 
    DesmosCalculatorManager,
    desmos_tool_registry,
    execute_desmos_tool
)
from .desmos_interactive_tools import (
    CreateSliderTool,
    AnimateSliderTool,
    ObserveEventTool,
    UnobserveEventTool,
    TakeScreenshotTool,
    EvaluateExpressionTool,
    CreateTableTool
)
from .desmos_advanced_tools import (
    CreateDistributionTool,
    Create3DGraphTool,
    CreateGeometryTool
)

logger = logging.getLogger(__name__)

class CompleteDesmosSystem:
    """완전한 Desmos MCP 시스템"""
    
    def __init__(self):
        self.calculator_manager = DesmosCalculatorManager()
        self.tool_registry = desmos_tool_registry
        self._register_additional_tools()
        
        # 시스템 통계
        self.stats = {
            "total_tools": 0,
            "calculators_created": 0,
            "expressions_created": 0,
            "screenshots_taken": 0,
            "animations_created": 0
        }
        
        self._update_stats()
        logger.info(f"🚀 완전한 Desmos MCP 시스템 초기화 완료 - {self.stats['total_tools']}개 도구 사용 가능")
    
    def _register_additional_tools(self):
        """추가 도구들 등록"""
        additional_tools = [
            # 인터랙티브 도구들
            CreateSliderTool(),
            AnimateSliderTool(),
            ObserveEventTool(),
            UnobserveEventTool(),
            TakeScreenshotTool(),
            EvaluateExpressionTool(),
            CreateTableTool(),
            
            # 고급 수학 도구들
            CreateDistributionTool(),
            Create3DGraphTool(),
            CreateGeometryTool()
        ]
        
        for tool in additional_tools:
            self.tool_registry.tools[tool.name] = tool
            logger.info(f"🔧 추가 도구 등록: {tool.name}")
    
    def _update_stats(self):
        """시스템 통계 업데이트"""
        self.stats["total_tools"] = len(self.tool_registry.tools)
        self.stats["calculators_created"] = len(self.calculator_manager.calculators)
    
    async def execute_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """도구 실행"""
        try:
            result = await execute_desmos_tool(tool_name, **kwargs)
            
            # 통계 업데이트
            if result.get("success", False):
                if "screenshot" in tool_name:
                    self.stats["screenshots_taken"] += 1
                elif "expression" in tool_name:
                    self.stats["expressions_created"] += 1
                elif "animate" in tool_name or "slider" in tool_name:
                    self.stats["animations_created"] += 1
            
            return result
            
        except Exception as e:
            logger.error(f"도구 실행 오류 ({tool_name}): {e}")
            return {"success": False, "error": str(e)}
    
    def get_available_tools(self) -> List[str]:
        """사용 가능한 모든 도구 목록"""
        return list(self.tool_registry.tools.keys())
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """특정 도구 정보 조회"""
        tool = self.tool_registry.get_tool(tool_name)
        if tool:
            return {
                "name": tool.name,
                "description": tool.description,
                "schema": tool.schema,
                "tool_id": tool.tool_id
            }
        return None
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 조회"""
        return {
            "status": "active",
            "stats": self.stats,
            "available_tools": len(self.tool_registry.tools),
            "active_calculators": len(self.calculator_manager.calculators),
            "tool_categories": {
                "calculator_management": [
                    "create_graphing_calculator",
                    "create_scientific_calculator", 
                    "create_fourfunction_calculator"
                ],
                "expression_management": [
                    "set_expression",
                    "remove_expression",
                    "set_expression_style"
                ],
                "viewport_and_settings": [
                    "set_viewport",
                    "get_state",
                    "set_state"
                ],
                "interactive_features": [
                    "create_slider",
                    "animate_slider",
                    "observe_event",
                    "unobserve_event",
                    "take_screenshot"
                ],
                "advanced_math": [
                    "create_distribution",
                    "create_3d_graph",
                    "create_geometry",
                    "evaluate_expression",
                    "create_table"
                ]
            }
        }
    
    def get_function_schemas_for_llm(self) -> List[Dict[str, Any]]:
        """LLM 함수 호출을 위한 스키마 반환"""
        return self.tool_registry.get_tool_schemas()

# 전역 시스템 인스턴스
complete_desmos_system = CompleteDesmosSystem()

# =============================================================================
# LLM과의 통합을 위한 편의 함수들
# =============================================================================

async def create_interactive_math_graph(
    concept_type: str = "function",
    difficulty_level: int = 3,
    question: str = "",
    auto_screenshot: bool = False
) -> Dict[str, Any]:
    """
    수학 개념에 맞는 완전한 인터랙티브 그래프를 자동 생성
    
    Args:
        concept_type: 수학 개념 (function, derivative, integral, vector, trigonometry, statistics, geometry)
        difficulty_level: 난이도 (1-5)
        question: 학생 질문 (분석하여 적절한 그래프 생성)
        auto_screenshot: 자동 스크린샷 생성 여부
    """
    try:
        results = {}
        
        # 1. 그래핑 계산기 생성
        calc_result = await complete_desmos_system.execute_tool(
            "create_graphing_calculator",
            options={
                "expressions": True,
                "sliders": True,
                "trace": True,
                "distributions": concept_type == "statistics",
                "language": "ko"
            }
        )
        
        if not calc_result["success"]:
            return calc_result
        
        calculator_id = calc_result["calculator_id"]
        results["calculator"] = calc_result
        
        # 2. 개념별 특화 그래프 생성
        if concept_type == "derivative":
            # 미분 그래프 + 슬라이더
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "f(x)=x^3-3x^2+2x",
                    "color": "#c74440",
                    "label": "원함수"
                }
            )
            
            await complete_desmos_system.execute_tool(
                "set_expression", 
                calculator_id=calculator_id,
                expression={
                    "latex": "f'(x)=3x^2-6x+2",
                    "color": "#2d70b3",
                    "label": "도함수",
                    "hidden": True
                }
            )
            
            slider_result = await complete_desmos_system.execute_tool(
                "create_slider",
                calculator_id=calculator_id,
                variable="a",
                min_value=-2,
                max_value=3,
                default_value=1,
                label="접점 x좌표"
            )
            results["slider"] = slider_result
            
            # 접선 표현식
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "y-f(a)=f'(a)(x-a)",
                    "color": "#fa7e19",
                    "label": "접선",
                    "lineStyle": "DASHED"
                }
            )
            
        elif concept_type == "integral":
            # 적분 시각화
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "f(x)=x^2",
                    "color": "#c74440"
                }
            )
            
            await complete_desmos_system.execute_tool(
                "create_slider",
                calculator_id=calculator_id,
                variable="a",
                min_value=-2,
                max_value=2,
                default_value=0,
                label="적분 시작"
            )
            
            await complete_desmos_system.execute_tool(
                "create_slider",
                calculator_id=calculator_id,
                variable="b", 
                min_value=0,
                max_value=3,
                default_value=2,
                label="적분 끝"
            )
            
            # 적분 영역
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "a\\le x\\le b\\{y\\le f(x)\\}",
                    "color": "#2d70b3",
                    "fillOpacity": 0.4
                }
            )
            
        elif concept_type == "statistics":
            # 통계 분포
            dist_result = await complete_desmos_system.execute_tool(
                "create_distribution",
                calculator_id=calculator_id,
                distribution_type="normal",
                parameters={"μ": 0, "σ": 1},
                visualization={
                    "show_pdf": True,
                    "show_cdf": False,
                    "color": "#2d70b3"
                }
            )
            results["distribution"] = dist_result
            
        elif concept_type == "geometry":
            # 기하학 도형
            geom_result = await complete_desmos_system.execute_tool(
                "create_geometry",
                calculator_id=calculator_id,
                geometry_type="circle",
                properties={
                    "center_x": 0,
                    "center_y": 0,
                    "radius": 2,
                    "color": "#c74440"
                }
            )
            results["geometry"] = geom_result
            
        elif concept_type == "vector":
            # 벡터 표시
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "(0,0)",
                    "color": "#000000",
                    "pointStyle": "POINT",
                    "pointSize": 8,
                    "label": "원점"
                }
            )
            
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "(3,2)",
                    "color": "#c74440",
                    "pointStyle": "POINT",
                    "pointSize": 6,
                    "label": "벡터 u"
                }
            )
            
        else:  # function
            # 일반 함수들
            functions = [
                {"latex": "f(x)=x^2", "color": "#c74440", "label": "이차함수"},
                {"latex": "g(x)=2x+1", "color": "#2d70b3", "label": "일차함수"}, 
                {"latex": "h(x)=\\sin(x)", "color": "#388c46", "label": "삼각함수"}
            ]
            
            for func in functions:
                await complete_desmos_system.execute_tool(
                    "set_expression",
                    calculator_id=calculator_id,
                    expression=func
                )
        
        # 3. 최적 뷰포트 설정
        viewport_configs = {
            "derivative": {"xmin": -3, "ymin": -5, "xmax": 5, "ymax": 10},
            "integral": {"xmin": -1, "ymin": -1, "xmax": 3, "ymax": 5},
            "vector": {"xmin": -1, "ymin": -1, "xmax": 5, "ymax": 5},
            "trigonometry": {"xmin": -6.28, "ymin": -3, "xmax": 6.28, "ymax": 3},
            "statistics": {"xmin": -4, "ymin": -0.1, "xmax": 4, "ymax": 0.5},
            "geometry": {"xmin": -5, "ymin": -5, "xmax": 5, "ymax": 5},
            "function": {"xmin": -5, "ymin": -5, "xmax": 5, "ymax": 10}
        }
        
        viewport = viewport_configs.get(concept_type, viewport_configs["function"])
        await complete_desmos_system.execute_tool(
            "set_viewport",
            calculator_id=calculator_id,
            viewport=viewport
        )
        
        # 4. 자동 스크린샷
        if auto_screenshot:
            screenshot_result = await complete_desmos_system.execute_tool(
                "take_screenshot",
                calculator_id=calculator_id,
                options={
                    "width": 800,
                    "height": 600,
                    "format": "png",
                    "include_expressions": True
                }
            )
            results["screenshot"] = screenshot_result
        
        # 5. 상태 조회
        state_result = await complete_desmos_system.execute_tool(
            "get_state",
            calculator_id=calculator_id
        )
        results["final_state"] = state_result
        
        return {
            "success": True,
            "concept_type": concept_type,
            "difficulty_level": difficulty_level,
            "calculator_id": calculator_id,
            "results": results,
            "message": f"{concept_type} 개념의 완전한 인터랙티브 그래프 생성 완료",
            "usage_guide": {
                "sliders": "슬라이더를 움직여 매개변수를 실시간으로 조작하세요",
                "expressions": "표현식 목록에서 함수를 켜고 끌 수 있습니다",
                "interaction": "그래프를 클릭하고 드래그하여 탐색하세요",
                "zoom": "마우스 휠로 확대/축소 가능합니다"
            }
        }
        
    except Exception as e:
        logger.error(f"인터랙티브 수학 그래프 생성 오류: {e}")
        return {"success": False, "error": str(e)}

async def create_data_visualization(
    data: Dict[str, List[float]],
    chart_type: str = "scatter",
    statistics: bool = True
) -> Dict[str, Any]:
    """
    데이터 시각화 및 통계 분석
    
    Args:
        data: {"x": [x값들], "y": [y값들]} 형태의 데이터
        chart_type: 차트 타입 (scatter, line, histogram)
        statistics: 통계 분석 포함 여부
    """
    try:
        # 계산기 생성
        calc_result = await complete_desmos_system.execute_tool(
            "create_graphing_calculator",
            options={
                "expressions": True,
                "distributions": True,
                "language": "ko"
            }
        )
        
        calculator_id = calc_result["calculator_id"]
        
        # 데이터 테이블 생성
        table_result = await complete_desmos_system.execute_tool(
            "create_table",
            calculator_id=calculator_id,
            data=data,
            style={
                "color": "#2d70b3",
                "point_style": "POINT",
                "lines": chart_type == "line"
            }
        )
        
        results = {
            "calculator": calc_result,
            "table": table_result
        }
        
        # 통계 분석
        if statistics and len(data["x"]) > 1:
            # 회귀분석
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": "y_1~mx_1+b",
                    "color": "#c74440",
                    "label": "회귀직선"
                }
            )
            
            # 평균선
            mean_x = sum(data["x"]) / len(data["x"])
            mean_y = sum(data["y"]) / len(data["y"])
            
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": f"x={mean_x}",
                    "color": "#fa7e19",
                    "lineStyle": "DASHED",
                    "label": "x 평균"
                }
            )
            
            await complete_desmos_system.execute_tool(
                "set_expression",
                calculator_id=calculator_id,
                expression={
                    "latex": f"y={mean_y}",
                    "color": "#388c46", 
                    "lineStyle": "DASHED",
                    "label": "y 평균"
                }
            )
        
        return {
            "success": True,
            "calculator_id": calculator_id,
            "chart_type": chart_type,
            "data_points": len(data["x"]),
            "results": results,
            "message": f"{chart_type} 차트 및 데이터 분석 완료"
        }
        
    except Exception as e:
        logger.error(f"데이터 시각화 생성 오류: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# 에이전트 통합을 위한 래퍼
# =============================================================================

class DesmosAgentTool:
    """Desmos 에이전트용 통합 도구"""
    
    def __init__(self):
        self.system = complete_desmos_system
        self.name = "desmos_complete_system"
        self.description = """
        완전한 Desmos API v1.11 기능을 제공하는 MCP 스타일 도구.
        
        주요 기능:
        - 모든 타입의 계산기 생성 (그래핑, 과학, 사칙연산)
        - 수학 표현식 관리 및 스타일링
        - 인터랙티브 슬라이더 및 애니메이션
        - 통계 분포 및 데이터 시각화
        - 3D 그래프 및 기하학 도형
        - 이벤트 관찰 및 스크린샷
        - 실시간 수식 계산
        
        GPT/Claude와 차별화된 실제 인터랙티브 그래프 생성 기능
        """
    
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """에이전트에서 호출하는 메인 실행 함수"""
        action = kwargs.get("action", "create_interactive_graph")
        
        if action == "create_interactive_graph":
            return await create_interactive_math_graph(
                concept_type=kwargs.get("concept_type", "function"),
                difficulty_level=kwargs.get("difficulty_level", 3),
                question=kwargs.get("question", ""),
                auto_screenshot=kwargs.get("auto_screenshot", False)
            )
        
        elif action == "create_data_visualization":
            return await create_data_visualization(
                data=kwargs.get("data", {"x": [1,2,3], "y": [1,4,9]}),
                chart_type=kwargs.get("chart_type", "scatter"),
                statistics=kwargs.get("statistics", True)
            )
        
        elif action == "execute_tool":
            tool_name = kwargs.get("tool_name")
            tool_params = kwargs.get("tool_params", {})
            return await self.system.execute_tool(tool_name, **tool_params)
        
        elif action == "get_system_status":
            return self.system.get_system_status()
        
        elif action == "get_available_tools":
            return {
                "success": True,
                "tools": self.system.get_available_tools(),
                "tool_schemas": self.system.get_function_schemas_for_llm()
            }
        
        else:
            return {"success": False, "error": f"지원하지 않는 액션: {action}"}
    
    def should_apply(self, question: str, context: Dict[str, Any] = None) -> bool:
        """이 도구가 적용되어야 하는지 판단"""
        math_keywords = [
            "그래프", "함수", "미분", "적분", "도함수", "곡선", "직선",
            "포물선", "삼각함수", "sin", "cos", "tan", "벡터", "좌표",
            "기울기", "접선", "넓이", "부피", "시각화", "그림", "차트",
            "분포", "통계", "데이터", "회귀", "상관관계", "슬라이더",
            "애니메이션", "인터랙티브", "3d", "기하", "원", "타원"
        ]
        
        question_lower = question.lower()
        return any(keyword in question_lower for keyword in math_keywords)

# 전역 에이전트 도구 인스턴스  
desmos_agent_tool = DesmosAgentTool()