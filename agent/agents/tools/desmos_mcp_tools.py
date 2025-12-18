#!/usr/bin/env python3
"""
GPT가 호출할 수 있는 실제 Desmos MCP 도구들
MCP (Model Context Protocol) 표준에 따라 구현

이제 GPT가:
1. 도구들을 동적으로 발견 (list_tools)
2. 필요에 따라 도구를 선택해서 호출 (call_tool)
3. 결과를 보고 다음 도구 결정
4. 실제 Desmos 그래프 완성
"""

import json
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from abc import ABC, abstractmethod

# === DEPRECATED IMPORTS - 파일이 존재하지 않거나 사용되지 않음 ===
# 향후 Desmos 고급 기능 개발 시 다시 활성화 예정
# 
# from .desmos_interactive_tools import (
#     CreateSliderTool as InteractiveSliderTool,
#     AnimateSliderTool,
#     ObserveEventTool,
#     UnobserveEventTool, 
#     TakeScreenshotTool,
#     EvaluateExpressionTool,
#     CreateTableTool
# )
# from .desmos_advanced_tools import (
#     CreateDistributionTool,
#     Create3DGraphTool,
#     CreateGeometryTool
# )
# from .desmos_mcp_system import (
#     SetExpressionStyleTool,
#     RemoveExpressionTool,
#     SetViewportTool as SystemViewportTool,
#     GetStateTool,
#     SetStateTool
# )

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("desmos-mcp-tools")

class DesmosCalculatorState:
    """Desmos 계산기 상태 관리"""
    
    def __init__(self):
        self.calculators: Dict[str, Dict[str, Any]] = {}
    
    def create_calculator(self, calculator_id: str = None, options: Dict[str, Any] = None) -> str:
        """새 계산기 생성"""
        if calculator_id is None:
            calculator_id = f"desmos_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        calculator_data = {
            "id": calculator_id,
            "options": options or {
                "keypad": False,
                "graphpaper": True,
                "expressions": True,
                "settingsMenu": False,
                "expressionsTopbar": False,
                "language": "ko"
            },
            "expressions": [],
            "viewport": {"xmin": -10, "ymin": -10, "xmax": 10, "ymax": 10},
            "created_at": datetime.now().isoformat()
        }
        
        self.calculators[calculator_id] = calculator_data
        logger.info(f"📊 Desmos 계산기 생성: {calculator_id}")
        return calculator_id
    
    def add_expression(self, calculator_id: str, expression: Dict[str, Any]) -> bool:
        """표현식 추가"""
        if calculator_id not in self.calculators:
            return False
        
        calculator = self.calculators[calculator_id]
        
        # ID 자동 생성
        if "id" not in expression:
            expression["id"] = f"expr_{len(calculator['expressions']) + 1}"
        
        # 기존 표현식 업데이트 또는 새로 추가
        updated = False
        for i, expr in enumerate(calculator["expressions"]):
            if expr.get("id") == expression["id"]:
                calculator["expressions"][i] = expression
                updated = True
                break
        
        if not updated:
            calculator["expressions"].append(expression)
        
        logger.info(f"📝 표현식 {'업데이트' if updated else '추가'}: {expression.get('latex', 'N/A')}")
        return True
    
    def set_viewport(self, calculator_id: str, viewport: Dict[str, float]) -> bool:
        """뷰포트 설정"""
        if calculator_id not in self.calculators:
            return False
        
        self.calculators[calculator_id]["viewport"].update(viewport)
        logger.info(f"🔍 뷰포트 설정: {viewport}")
        return True
    
    def get_calculator(self, calculator_id: str) -> Optional[Dict[str, Any]]:
        """계산기 조회"""
        return self.calculators.get(calculator_id)
    
    def generate_javascript(self, calculator_id: str) -> str:
        """완전한 JavaScript 코드 생성"""
        if calculator_id not in self.calculators:
            return ""
        
        calculator = self.calculators[calculator_id]
        
        js_code = f"""
// 실제 Desmos API v1.11 계산기 생성
(function() {{
    // DOM 엘리먼트 확인/생성
    let element = document.getElementById('{calculator_id}');
    if (!element) {{
        element = document.createElement('div');
        element.id = '{calculator_id}';
        element.style.width = '100%';
        element.style.height = '400px';
        element.style.border = '1px solid #ddd';
        element.style.margin = '10px 0';
        
        // 컨테이너에 추가 (우선순위: desmos-container > graphContainer > calculator-container > body)
        const container = document.getElementById('desmos-container') || 
                         document.getElementById('graphContainer') || 
                         document.getElementById('calculator-container') || 
                         document.body;
        
        // 기존 계산기가 있다면 제거
        if (container.id === 'desmos-container' || container.id === 'graphContainer') {{
            container.innerHTML = ''; // 기존 내용 제거
        }}
        container.appendChild(element);
    }}
    
    // Desmos 계산기 생성
    const calculator = Desmos.GraphingCalculator(element, {json.dumps(calculator['options'])});
    
    // 전역 접근을 위해 저장
    window.desmosCalculators = window.desmosCalculators || {{}};
    window.desmosCalculators['{calculator_id}'] = calculator;
"""
        
        # 모든 표현식 추가
        for expr in calculator["expressions"]:
            js_code += f"""
    calculator.setExpression({json.dumps(expr)});"""
        
        # 뷰포트 설정
        if calculator["viewport"]:
            js_code += f"""
    calculator.setMathBounds({json.dumps(calculator['viewport'])});"""
        
        js_code += f"""
    
    console.log('✅ Desmos 계산기 준비 완료:', '{calculator_id}');
    console.log('📊 표현식 개수:', {len(calculator['expressions'])});
    
    return calculator;
}})();
"""
        
        return js_code

# 전역 계산기 상태 관리자
calculator_state = DesmosCalculatorState()

class GPTCallableTool(ABC):
    """GPT가 호출할 수 있는 도구의 기본 클래스"""
    
    @abstractmethod
    def get_tool_definition(self) -> Dict[str, Any]:
        """GPT가 확인할 수 있는 도구 정의"""
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """GPT가 호출할 수 있는 실행 함수"""
        pass

class CreateDesmosCalculatorTool(GPTCallableTool):
    """계산기 생성 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "create_desmos_calculator",
                "description": "새로운 Desmos 그래핑 계산기를 생성합니다. 수학 그래프를 그리기 위한 첫 번째 단계입니다.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "calculator_id": {
                            "type": "string",
                            "description": "계산기 고유 ID (생략시 자동 생성)"
                        },
                        "options": {
                            "type": "object",
                            "description": "계산기 옵션 설정",
                            "properties": {
                                "keypad": {"type": "boolean", "description": "키패드 표시 여부"},
                                "expressions": {"type": "boolean", "description": "표현식 리스트 표시 여부"},
                                "language": {"type": "string", "description": "언어 설정 (ko, en 등)"}
                            }
                        }
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str = None, options: dict = None) -> Dict[str, Any]:
        try:
            calc_id = calculator_state.create_calculator(calculator_id, options)
            return {
                "success": True,
                "calculator_id": calc_id,
                "message": f"✅ Desmos 계산기 '{calc_id}' 생성 완료",
                "next_steps": [
                    "add_expression을 사용해서 수학 표현식 추가",
                    "create_slider로 인터랙티브 요소 추가",
                    "set_viewport로 보기 영역 조정"
                ]
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

class AddExpressionTool(GPTCallableTool):
    """표현식 추가 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function", 
            "function": {
                "name": "add_expression",
                "description": "계산기에 수학 표현식을 추가합니다. 함수, 방정식, 부등식 등을 그래프로 표시할 수 있습니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id", "latex"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "latex": {"type": "string", "description": "LaTeX 형식의 수학 표현식 (예: y=x^2, f(x)=\\sin(x))"},
                        "color": {"type": "string", "description": "그래프 색상 (hex 코드, 예: #c74440)"},
                        "label": {"type": "string", "description": "라벨 텍스트"},
                        "hidden": {"type": "boolean", "description": "표현식 숨김 여부", "default": False},
                        "line_style": {"type": "string", "enum": ["SOLID", "DASHED", "DOTTED"], "description": "선 스타일"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, latex: str, color: str = None, 
                label: str = None, hidden: bool = False, line_style: str = "SOLID") -> Dict[str, Any]:
        try:
            if calculator_id not in calculator_state.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            expression = {
                "latex": latex,
                "hidden": hidden,
                "lineStyle": line_style
            }
            
            if color:
                expression["color"] = color
            if label:
                expression["label"] = label
                expression["showLabel"] = True
            
            success = calculator_state.add_expression(calculator_id, expression)
            
            if success:
                return {
                    "success": True,
                    "expression_id": expression.get("id"),
                    "latex": latex,
                    "message": f"✅ 표현식 '{latex}' 추가 완료"
                }
            else:
                return {"success": False, "error": "표현식 추가 실패"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}

class CreateSliderTool(GPTCallableTool):
    """슬라이더 생성 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "create_slider",
                "description": "인터랙티브 슬라이더를 생성합니다. 매개변수를 실시간으로 조정하여 그래프의 변화를 관찰할 수 있습니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id", "variable"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "variable": {"type": "string", "description": "슬라이더 변수명 (예: a, b, c)"},
                        "min_value": {"type": "number", "description": "최솟값", "default": -10},
                        "max_value": {"type": "number", "description": "최댓값", "default": 10},
                        "step": {"type": "number", "description": "단계 크기", "default": 0.1},
                        "default_value": {"type": "number", "description": "기본값"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, variable: str, min_value: float = -10, 
                max_value: float = 10, step: float = 0.1, default_value: float = None) -> Dict[str, Any]:
        try:
            if calculator_id not in calculator_state.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            if default_value is None:
                default_value = (min_value + max_value) / 2
            
            slider_expression = {
                "id": f"slider_{variable}",
                "latex": f"{variable}={default_value}",
                "slider": {
                    "hardMin": min_value,
                    "hardMax": max_value,
                    "step": step
                }
            }
            
            success = calculator_state.add_expression(calculator_id, slider_expression)
            
            return {
                "success": success,
                "variable": variable,
                "range": f"[{min_value}, {max_value}]",
                "default": default_value,
                "message": f"✅ 슬라이더 '{variable}' 생성 완료"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class AddPointTool(GPTCallableTool):
    """점 추가 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "add_point",
                "description": "특정 좌표에 점을 추가합니다. 중요한 점이나 교점을 강조할 때 사용합니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id", "x", "y"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "x": {"type": "number", "description": "x 좌표"},
                        "y": {"type": "number", "description": "y 좌표"},
                        "color": {"type": "string", "description": "점 색상", "default": "#388c46"},
                        "size": {"type": "number", "description": "점 크기", "default": 9},
                        "label": {"type": "string", "description": "점 라벨"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, x: float, y: float, 
                color: str = "#388c46", size: float = 9, label: str = None) -> Dict[str, Any]:
        try:
            if calculator_id not in calculator_state.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            point_expression = {
                "latex": f"({x},{y})",
                "color": color,
                "pointSize": size,
                "showLabel": bool(label)
            }
            
            if label:
                point_expression["label"] = label
            else:
                point_expression["label"] = f"({x},{y})"
            
            success = calculator_state.add_expression(calculator_id, point_expression)
            
            return {
                "success": success,
                "coordinates": [x, y],
                "message": f"✅ 점 ({x},{y}) 추가 완료"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class SetViewportTool(GPTCallableTool):
    """뷰포트 설정 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "set_viewport",
                "description": "그래프의 보기 영역(뷰포트)을 설정합니다. 그래프의 특정 부분을 확대하거나 전체를 보고 싶을 때 사용합니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "xmin": {"type": "number", "description": "x축 최솟값"},
                        "ymin": {"type": "number", "description": "y축 최솟값"},
                        "xmax": {"type": "number", "description": "x축 최댓값"},
                        "ymax": {"type": "number", "description": "y축 최댓값"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, xmin: float = None, ymin: float = None,
                xmax: float = None, ymax: float = None) -> Dict[str, Any]:
        try:
            if calculator_id not in calculator_state.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            viewport = {}
            if xmin is not None:
                viewport["xmin"] = xmin
            if ymin is not None:
                viewport["ymin"] = ymin
            if xmax is not None:
                viewport["xmax"] = xmax
            if ymax is not None:
                viewport["ymax"] = ymax
            
            success = calculator_state.set_viewport(calculator_id, viewport)
            current_viewport = calculator_state.calculators[calculator_id]["viewport"]
            
            return {
                "success": success,
                "viewport": current_viewport,
                "message": "✅ 뷰포트 설정 완료"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class GenerateJavaScriptTool(GPTCallableTool):
    """JavaScript 코드 생성 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "generate_javascript",
                "description": "완성된 계산기의 전체 JavaScript 코드를 생성합니다. 웹페이지에 실제로 그래프를 표시할 때 사용합니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "코드를 생성할 계산기 ID"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str) -> Dict[str, Any]:
        try:
            calculator = calculator_state.get_calculator(calculator_id)
            
            if not calculator:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            js_code = calculator_state.generate_javascript(calculator_id)
            
            return {
                "success": True,
                "calculator_id": calculator_id,
                "expressions_count": len(calculator["expressions"]),
                "javascript_code": js_code,
                "message": "✅ JavaScript 코드 생성 완료",
                "usage": "이 코드를 웹페이지에서 실행하면 실제 Desmos 그래프가 표시됩니다"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class AddTangentLineTool(GPTCallableTool):
    """접선 추가 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "add_tangent_line",
                "description": "특정 점에서의 접선을 추가합니다. 미분 개념을 시각적으로 설명할 때 유용합니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id", "function_latex", "point_variable"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "function_latex": {"type": "string", "description": "원함수 LaTeX (예: \\sin(x), x^2)"},
                        "point_variable": {"type": "string", "description": "접점 변수 (예: a)"},
                        "color": {"type": "string", "description": "접선 색상", "default": "#fa7e19"},
                        "show_point": {"type": "boolean", "description": "접점 표시 여부", "default": True}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, function_latex: str, point_variable: str, 
                color: str = "#fa7e19", show_point: bool = True) -> Dict[str, Any]:
        try:
            # 접점 표시
            if show_point:
                point_expr = {
                    "latex": f"({point_variable}, {function_latex.replace('x', point_variable)})",
                    "color": color,
                    "pointSize": 8
                }
                calculator_state.add_expression(calculator_id, point_expr)
            
            # 접선 표현식 생성 (미분 사용)
            # 간단한 경우들에 대한 미분 처리
            if "x^2" in function_latex:
                derivative = function_latex.replace("x^2", "2*x")
                tangent_latex = f"y - ({function_latex.replace('x', point_variable)}) = ({derivative.replace('x', point_variable)}) * (x - {point_variable})"
            elif "sin(x)" in function_latex:
                tangent_latex = f"y - sin({point_variable}) = cos({point_variable}) * (x - {point_variable})"
            elif "cos(x)" in function_latex:
                tangent_latex = f"y - cos({point_variable}) = -sin({point_variable}) * (x - {point_variable})"
            else:
                # 일반적인 경우는 기울기를 수치적으로 계산
                tangent_latex = f"y = {function_latex.replace('x', point_variable)} + m * (x - {point_variable})"
            
            tangent_expr = {
                "latex": tangent_latex,
                "color": color,
                "lineStyle": "DASHED",
                "lineWidth": 2
            }
            
            result = calculator_state.add_expression(calculator_id, tangent_expr)
            
            return {
                "success": True,
                "message": f"접선이 추가되었습니다 (색상: {color})",
                "tangent_expression": tangent_latex,
                "point_shown": show_point
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class AddLineTool(GPTCallableTool):
    """직선 추가 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "add_line",
                "description": "직선을 추가합니다. 두 점을 연결하거나 기울기와 y절편으로 직선을 그릴 수 있습니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "slope": {"type": "number", "description": "기울기 (m)"},
                        "y_intercept": {"type": "number", "description": "y절편 (b)"},
                        "x1": {"type": "number", "description": "첫 번째 점의 x좌표"},
                        "y1": {"type": "number", "description": "첫 번째 점의 y좌표"},
                        "x2": {"type": "number", "description": "두 번째 점의 x좌표"},
                        "y2": {"type": "number", "description": "두 번째 점의 y좌표"},
                        "color": {"type": "string", "description": "직선 색상", "default": "#2d70b3"},
                        "line_style": {"type": "string", "enum": ["SOLID", "DASHED", "DOTTED"], "description": "선 스타일", "default": "SOLID"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, slope: float = None, y_intercept: float = None,
                x1: float = None, y1: float = None, x2: float = None, y2: float = None,
                color: str = "#2d70b3", line_style: str = "SOLID") -> Dict[str, Any]:
        try:
            if slope is not None and y_intercept is not None:
                # y = mx + b 형태
                latex = f"y = {slope}*x + {y_intercept}"
            elif all(coord is not None for coord in [x1, y1, x2, y2]):
                # 두 점을 지나는 직선
                if x2 != x1:
                    slope_calc = (y2 - y1) / (x2 - x1)
                    y_int_calc = y1 - slope_calc * x1
                    latex = f"y = {slope_calc}*x + {y_int_calc}"
                else:
                    # 수직선
                    latex = f"x = {x1}"
            else:
                return {"success": False, "error": "기울기와 y절편 또는 두 점의 좌표가 필요합니다"}
            
            line_expr = {
                "latex": latex,
                "color": color,
                "lineStyle": line_style,
                "lineWidth": 2.5
            }
            
            result = calculator_state.add_expression(calculator_id, line_expr)
            
            return {
                "success": True,
                "message": f"직선이 추가되었습니다: {latex}",
                "line_equation": latex,
                "color": color
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class AddCircleTool(GPTCallableTool):
    """원 추가 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "add_circle",
                "description": "원을 추가합니다. 중심과 반지름을 지정하여 원을 그릴 수 있습니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id", "center_x", "center_y", "radius"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "대상 계산기 ID"},
                        "center_x": {"type": "number", "description": "원의 중심 x좌표"},
                        "center_y": {"type": "number", "description": "원의 중심 y좌표"},
                        "radius": {"type": "number", "description": "원의 반지름"},
                        "color": {"type": "string", "description": "원 색상", "default": "#6042a6"},
                        "fill": {"type": "boolean", "description": "원 내부 채우기", "default": False},
                        "fill_opacity": {"type": "number", "description": "채우기 투명도 (0-1)", "default": 0.4}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str, center_x: float, center_y: float, radius: float,
                color: str = "#6042a6", fill: bool = False, fill_opacity: float = 0.4) -> Dict[str, Any]:
        try:
            # 원의 방정식: (x-h)^2 + (y-k)^2 = r^2
            latex = f"(x - {center_x})^2 + (y - {center_y})^2 = {radius**2}"
            
            circle_expr = {
                "latex": latex,
                "color": color,
                "lineWidth": 2.5
            }
            
            if fill:
                circle_expr["fillOpacity"] = fill_opacity
            
            result = calculator_state.add_expression(calculator_id, circle_expr)
            
            return {
                "success": True,
                "message": f"원이 추가되었습니다: 중심({center_x}, {center_y}), 반지름 {radius}",
                "circle_equation": latex,
                "center": [center_x, center_y],
                "radius": radius,
                "color": color
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class GetCalculatorInfoTool(GPTCallableTool):
    """계산기 정보 조회 도구"""
    
    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "get_calculator_info",
                "description": "계산기의 현재 상태와 정보를 조회합니다. 표현식 목록, 설정 등을 확인할 수 있습니다.",
                "parameters": {
                    "type": "object",
                    "required": ["calculator_id"],
                    "properties": {
                        "calculator_id": {"type": "string", "description": "조회할 계산기 ID"}
                    }
                }
            }
        }
    
    def execute(self, calculator_id: str) -> Dict[str, Any]:
        try:
            calculator = calculator_state.calculators.get(calculator_id)
            
            if not calculator:
                return {"success": False, "error": f"계산기를 찾을 수 없습니다: {calculator_id}"}
            
            return {
                "success": True,
                "calculator_id": calculator_id,
                "options": calculator["options"],
                "expressions_count": len(calculator["expressions"]),
                "expressions": calculator["expressions"],
                "viewport": calculator["viewport"],
                "created_at": calculator["created_at"]
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class DesmosToolManager:
    """GPT가 사용할 수 있는 모든 Desmos 도구들을 관리"""
    
    def __init__(self):
        self.tools = {
            # === 기본 계산기 도구들 ===
            "create_desmos_calculator": CreateDesmosCalculatorTool(),
            "add_expression": AddExpressionTool(),
            "get_calculator_info": GetCalculatorInfoTool(),
            
            # === 기하학적 요소 도구들 ===
            "add_point": AddPointTool(),
            "add_line": AddLineTool(),
            "add_circle": AddCircleTool(),
            "add_tangent_line": AddTangentLineTool(),
            
            # === 뷰포트 및 설정 도구들 ===
            "set_viewport": SetViewportTool(),
            
            # === 인터랙티브 기능 도구들 ===
            "create_slider": CreateSliderTool(),
            
            # === 최종 생성 도구 ===
            "generate_javascript": GenerateJavaScriptTool()
        }
    
    def list_tools(self) -> List[Dict[str, Any]]:
        """GPT가 확인할 수 있는 모든 도구 목록"""
        return [tool.get_tool_definition() for tool in self.tools.values()]
    
    def call_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """GPT가 도구를 호출하는 함수"""
        if tool_name not in self.tools:
            return {"success": False, "error": f"알 수 없는 도구: {tool_name}"}
        
        logger.info(f"🔧 GPT가 도구 호출: {tool_name}")
        logger.info(f"   매개변수: {kwargs}")
        
        try:
            result = self.tools[tool_name].execute(**kwargs)
            logger.info(f"   결과: {'성공' if result.get('success') else '실패'}")
            return result
        except Exception as e:
            logger.error(f"   오류: {e}")
            return {"success": False, "error": str(e)}
    
    def get_calculator_state(self) -> DesmosCalculatorState:
        """계산기 상태 반환"""
        return calculator_state

# 전역 도구 매니저 인스턴스
desmos_tool_manager = DesmosToolManager()

def get_gpt_function_definitions() -> List[Dict[str, Any]]:
    """GPT Function Calling에 사용할 함수 정의들"""
    return desmos_tool_manager.list_tools()

def execute_gpt_function_call(tool_name: str, **kwargs) -> Dict[str, Any]:
    """GPT Function Call 실행"""
    return desmos_tool_manager.call_tool(tool_name, **kwargs)

# 개별 함수들 (GPT가 직접 호출할 수 있도록)
def create_desmos_calculator(calculator_id: str = None, options: dict = None) -> str:
    """GPT가 호출할 수 있는 계산기 생성 함수"""
    result = desmos_tool_manager.call_tool("create_desmos_calculator", 
                                          calculator_id=calculator_id, options=options)
    return json.dumps(result, ensure_ascii=False)

def add_expression(calculator_id: str, latex: str, color: str = None, 
                  label: str = None, hidden: bool = False, line_style: str = "SOLID") -> str:
    """GPT가 호출할 수 있는 표현식 추가 함수"""
    result = desmos_tool_manager.call_tool("add_expression", 
                                          calculator_id=calculator_id, latex=latex, 
                                          color=color, label=label, hidden=hidden, 
                                          line_style=line_style)
    return json.dumps(result, ensure_ascii=False)

def create_slider(calculator_id: str, variable: str, min_value: float = -10,
                 max_value: float = 10, step: float = 0.1, default_value: float = None) -> str:
    """GPT가 호출할 수 있는 슬라이더 생성 함수"""
    result = desmos_tool_manager.call_tool("create_slider",
                                          calculator_id=calculator_id, variable=variable,
                                          min_value=min_value, max_value=max_value,
                                          step=step, default_value=default_value)
    return json.dumps(result, ensure_ascii=False)

def add_point(calculator_id: str, x: float, y: float, color: str = "#388c46",
             size: float = 9, label: str = None) -> str:
    """GPT가 호출할 수 있는 점 추가 함수"""
    result = desmos_tool_manager.call_tool("add_point",
                                          calculator_id=calculator_id, x=x, y=y,
                                          color=color, size=size, label=label)
    return json.dumps(result, ensure_ascii=False)

def set_viewport(calculator_id: str, xmin: float = None, ymin: float = None,
                xmax: float = None, ymax: float = None) -> str:
    """GPT가 호출할 수 있는 뷰포트 설정 함수"""
    result = desmos_tool_manager.call_tool("set_viewport",
                                          calculator_id=calculator_id, xmin=xmin,
                                          ymin=ymin, xmax=xmax, ymax=ymax)
    return json.dumps(result, ensure_ascii=False)

def generate_javascript(calculator_id: str) -> str:
    """GPT가 호출할 수 있는 JavaScript 생성 함수"""
    result = desmos_tool_manager.call_tool("generate_javascript",
                                          calculator_id=calculator_id)
    return json.dumps(result, ensure_ascii=False)

if __name__ == "__main__":
    print("""
🎯 GPT 호출 가능한 Desmos MCP 도구들 (완전 확장판)
===============================================

✅ 구현된 도구들 (총 10개):

📊 기본 계산기 도구들:
- create_desmos_calculator: 계산기 생성
- add_expression: 수학 표현식 추가
- get_calculator_info: 계산기 상태 조회

📐 기하학적 요소 도구들:
- add_point: 특정 점 표시
- add_line: 직선 추가 (기울기/두점)
- add_circle: 원 추가 (중심/반지름)
- add_tangent_line: 접선 추가 (미분 시각화)

🎛️ 인터랙티브 기능 도구들:
- create_slider: 인터랙티브 슬라이더

🖥️ 시스템 도구들:
- set_viewport: 보기 영역 조정
- generate_javascript: 최종 코드 생성

🤖 GPT 사용 방법:
1. list_tools()로 10개 도구 목록 확인
2. 질문에 따라 적절한 도구들 선택
3. 점, 직선, 원, 접선이 포함된 복잡한 그래프 생성
4. 슬라이더로 인터랙티브 요소 활용

🚀 GPT가 점, 직선, 원, 접선, 슬라이더를 자유롭게 조합할 수 있습니다!
   기본 기능부터 고급 기하학까지 모두 가능!
""")
    
    # 도구 목록 출력
    tools = desmos_tool_manager.list_tools()
    print(f"\n📋 사용 가능한 도구: {len(tools)}개")
    for tool in tools:
        print(f"   - {tool['function']['name']}: {tool['function']['description'][:50]}...")