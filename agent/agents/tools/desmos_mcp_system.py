"""
Desmos MCP (Model Context Protocol) 시스템
Desmos API v1.11의 모든 메서드를 MCP 스타일로 구현

이 시스템은 GPT/Claude와 같은 LLM이 Desmos의 모든 기능을 
함수 호출 방식으로 활용할 수 있도록 설계되었습니다.
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from abc import ABC, abstractmethod
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

class DesmosToolBase(ABC):
    """Desmos MCP 도구 기본 클래스"""
    
    def __init__(self, name: str, description: str, schema: Dict[str, Any]):
        self.name = name
        self.description = description
        self.schema = schema
        self.tool_id = str(uuid.uuid4())
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """도구 실행"""
        pass
    
    def validate_parameters(self, params: Dict[str, Any]) -> bool:
        """파라미터 유효성 검사"""
        required = self.schema.get("required", [])
        return all(param in params for param in required)

class DesmosCalculatorManager:
    """Desmos 계산기 인스턴스 관리자"""
    
    def __init__(self):
        self.calculators: Dict[str, Dict[str, Any]] = {}
        self.default_options = {
            "keypad": True,
            "graphpaper": True,
            "expressions": True,
            "settingsMenu": True,
            "zoomButtons": True,
            "showResetButtonOnGraphpaper": False,
            "expressionsTopbar": True,
            "pointsOfInterest": True,
            "trace": True,
            "border": True,
            "lockViewport": False,
            "expressionsCollapsed": False,
            "capExpressionSize": False,
            "authorFeatures": False,
            "images": True,
            "folders": True,
            "notes": True,
            "sliders": True,
            "actions": "auto",
            "substitutions": True,
            "links": True,
            "qwertyKeyboard": True,
            "distributions": True,
            "restrictedFunctions": False,
            "forceEnableGeometryFunctions": False,
            "pasteGraphLink": False,
            "pasteTableData": True,
            "clearIntoDegreeMode": False,
            "language": "ko"
        }
    
    def create_calculator(self, calculator_id: str = None, 
                         calculator_type: str = "graphing",
                         options: Dict[str, Any] = None) -> str:
        """새 계산기 인스턴스 생성"""
        if calculator_id is None:
            calculator_id = f"calc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        merged_options = {**self.default_options}
        if options:
            merged_options.update(options)
        
        calculator_config = {
            "id": calculator_id,
            "type": calculator_type,
            "options": merged_options,
            "state": self._get_initial_state(calculator_type),
            "created_at": datetime.now().isoformat(),
            "last_modified": datetime.now().isoformat()
        }
        
        self.calculators[calculator_id] = calculator_config
        logger.info(f"📊 {calculator_type} 계산기 생성완료: {calculator_id}")
        
        return calculator_id
    
    def _get_initial_state(self, calculator_type: str) -> Dict[str, Any]:
        """계산기 타입별 초기 상태"""
        if calculator_type == "graphing":
            return {
                "version": 11,
                "randomSeed": str(uuid.uuid4()),
                "graph": {
                    "viewport": {"xmin": -10, "ymin": -10, "xmax": 10, "ymax": 10}
                },
                "expressions": {"list": []}
            }
        elif calculator_type == "scientific":
            return {
                "version": 11,
                "currentExpression": "",
                "history": []
            }
        elif calculator_type == "fourfunction":
            return {
                "version": 11,
                "currentExpression": "",
                "history": []
            }
        else:
            return {}

# =============================================================================
# 1. 계산기 생성 및 관리 도구들
# =============================================================================

class CreateGraphingCalculatorTool(DesmosToolBase):
    """Desmos 그래핑 계산기 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_graphing_calculator",
            description="새로운 Desmos 그래핑 계산기 인스턴스를 생성합니다",
            schema={
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
                            "keypad": {"type": "boolean", "default": True},
                            "graphpaper": {"type": "boolean", "default": True},
                            "expressions": {"type": "boolean", "default": True},
                            "settingsMenu": {"type": "boolean", "default": True},
                            "zoomButtons": {"type": "boolean", "default": True},
                            "pointsOfInterest": {"type": "boolean", "default": True},
                            "trace": {"type": "boolean", "default": True},
                            "border": {"type": "boolean", "default": True},
                            "lockViewport": {"type": "boolean", "default": False},
                            "expressionsCollapsed": {"type": "boolean", "default": False},
                            "images": {"type": "boolean", "default": True},
                            "folders": {"type": "boolean", "default": True},
                            "notes": {"type": "boolean", "default": True},
                            "sliders": {"type": "boolean", "default": True},
                            "actions": {"type": "string", "enum": ["auto", "true", "false"], "default": "auto"},
                            "distributions": {"type": "boolean", "default": True},
                            "language": {"type": "string", "default": "ko"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            calc_id = self.calculator_manager.create_calculator(
                calculator_id=calculator_id,
                calculator_type="graphing",
                options=options
            )
            
            return {
                "success": True,
                "calculator_id": calc_id,
                "type": "graphing",
                "message": f"그래핑 계산기 '{calc_id}' 생성 완료",
                "javascript_code": f"""
                // Desmos 그래핑 계산기 초기화 코드
                var element_{calc_id.replace('-', '_')} = document.getElementById('{calc_id}');
                var calculator_{calc_id.replace('-', '_')} = Desmos.GraphingCalculator(element_{calc_id.replace('-', '_')}, {json.dumps(options or {})});
                """
            }
        except Exception as e:
            logger.error(f"그래핑 계산기 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }

class CreateScientificCalculatorTool(DesmosToolBase):
    """Desmos 과학 계산기 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_scientific_calculator",
            description="새로운 Desmos 과학 계산기 인스턴스를 생성합니다",
            schema={
                "type": "object",
                "properties": {
                    "calculator_id": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "qwertyKeyboard": {"type": "boolean", "default": True},
                            "degreeMode": {"type": "boolean", "default": False},
                            "fontSize": {"type": "integer", "default": 16},
                            "invertedColors": {"type": "boolean", "default": False},
                            "language": {"type": "string", "default": "ko"},
                            "decimalToFraction": {"type": "boolean", "default": True},
                            "functionDefinition": {"type": "boolean", "default": True}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            calc_id = self.calculator_manager.create_calculator(
                calculator_id=calculator_id,
                calculator_type="scientific",
                options=options
            )
            
            return {
                "success": True,
                "calculator_id": calc_id,
                "type": "scientific",
                "message": f"과학 계산기 '{calc_id}' 생성 완료"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

class CreateFourFunctionCalculatorTool(DesmosToolBase):
    """Desmos 사칙연산 계산기 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_fourfunction_calculator",
            description="새로운 Desmos 사칙연산 계산기 인스턴스를 생성합니다",
            schema={
                "type": "object",
                "properties": {
                    "calculator_id": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "additionalFunctions": {
                                "type": "array",
                                "items": {"type": "string", "enum": ["sqrt", "exponent", "percent", "fraction"]},
                                "default": ["sqrt"]
                            },
                            "fontSize": {"type": "integer", "default": 16},
                            "invertedColors": {"type": "boolean", "default": False},
                            "language": {"type": "string", "default": "ko"},
                            "decimalToFraction": {"type": "boolean", "default": False}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str = None, options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            calc_id = self.calculator_manager.create_calculator(
                calculator_id=calculator_id,
                calculator_type="fourfunction",
                options=options
            )
            
            return {
                "success": True,
                "calculator_id": calc_id,
                "type": "fourfunction",
                "message": f"사칙연산 계산기 '{calc_id}' 생성 완료"
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 2. 표현식 관리 도구들
# =============================================================================

class SetExpressionTool(DesmosToolBase):
    """표현식 설정 도구"""
    
    def __init__(self):
        super().__init__(
            name="set_expression",
            description="계산기에 수학 표현식을 추가하거나 수정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "expression"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "expression": {
                        "type": "object",
                        "required": ["latex"],
                        "properties": {
                            "id": {"type": "string"},
                            "latex": {"type": "string", "description": "LaTeX 형식의 수학 표현식"},
                            "color": {"type": "string", "description": "색상 (hex 코드)"},
                            "hidden": {"type": "boolean", "default": False},
                            "points": {"type": "boolean", "default": True},
                            "lines": {"type": "boolean", "default": True},
                            "dragMode": {"type": "string", "enum": ["NONE", "X", "Y", "XY"]},
                            "label": {"type": "string"},
                            "showLabel": {"type": "boolean", "default": False},
                            "slider": {
                                "type": "object",
                                "properties": {
                                    "hardMin": {"type": "number"},
                                    "hardMax": {"type": "number"},
                                    "step": {"type": "number"},
                                    "animationPeriod": {"type": "number"},
                                    "loopMode": {"type": "string", "enum": ["LOOP_FORWARD_REVERSE", "LOOP_FORWARD", "PLAY_ONCE", "PLAY_INDEFINITELY"]}
                                }
                            },
                            "polarDomain": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "string"},
                                    "max": {"type": "string"}
                                }
                            },
                            "parametricDomain": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "string"},
                                    "max": {"type": "string"}
                                }
                            },
                            "domain": {
                                "type": "object",
                                "properties": {
                                    "min": {"type": "string"},
                                    "max": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, expression: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            
            # 표현식 ID 자동 생성
            if "id" not in expression:
                expression["id"] = f"expr_{len(calculator['state']['expressions']['list']) + 1}"
            
            # 기존 표현식 찾기 또는 새로 추가
            expressions_list = calculator["state"]["expressions"]["list"]
            expr_index = None
            
            for i, expr in enumerate(expressions_list):
                if expr.get("id") == expression["id"]:
                    expr_index = i
                    break
            
            if expr_index is not None:
                expressions_list[expr_index] = expression
                action = "수정"
            else:
                expressions_list.append(expression)
                action = "추가"
            
            calculator["last_modified"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "action": action,
                "expression_id": expression["id"],
                "calculator_id": calculator_id,
                "message": f"표현식 '{expression['latex']}' {action} 완료",
                "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expression)});"
            }
            
        except Exception as e:
            logger.error(f"표현식 설정 오류: {e}")
            return {"success": False, "error": str(e)}

class RemoveExpressionTool(DesmosToolBase):
    """표현식 제거 도구"""
    
    def __init__(self):
        super().__init__(
            name="remove_expression",
            description="계산기에서 표현식을 제거합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "expression_id"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "expression_id": {"type": "string"}
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, expression_id: str) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            expressions_list = calculator["state"]["expressions"]["list"]
            
            # 표현식 찾기 및 제거
            for i, expr in enumerate(expressions_list):
                if expr.get("id") == expression_id:
                    removed_expr = expressions_list.pop(i)
                    calculator["last_modified"] = datetime.now().isoformat()
                    
                    return {
                        "success": True,
                        "removed_expression": removed_expr,
                        "calculator_id": calculator_id,
                        "message": f"표현식 '{expression_id}' 제거 완료",
                        "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.removeExpression({{id: '{expression_id}'}});"
                    }
            
            return {"success": False, "error": f"표현식 '{expression_id}'를 찾을 수 없습니다"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 3. 뷰포트 및 그래프 설정 도구들  
# =============================================================================

class SetViewportTool(DesmosToolBase):
    """그래프 뷰포트 설정 도구"""
    
    def __init__(self):
        super().__init__(
            name="set_viewport",
            description="그래프의 보기 영역을 설정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "viewport": {
                        "type": "object",
                        "properties": {
                            "xmin": {"type": "number"},
                            "ymin": {"type": "number"},
                            "xmax": {"type": "number"},
                            "ymax": {"type": "number"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, viewport: Dict[str, float] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            
            if viewport:
                calculator["state"]["graph"]["viewport"].update(viewport)
                calculator["last_modified"] = datetime.now().isoformat()
                
                return {
                    "success": True,
                    "viewport": calculator["state"]["graph"]["viewport"],
                    "calculator_id": calculator_id,
                    "message": "뷰포트 설정 완료",
                    "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setMathBounds({json.dumps(viewport)});"
                }
            else:
                return {
                    "success": True,
                    "viewport": calculator["state"]["graph"]["viewport"],
                    "calculator_id": calculator_id
                }
                
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 4. 상태 관리 도구들
# =============================================================================

class GetStateTool(DesmosToolBase):
    """계산기 상태 조회 도구"""
    
    def __init__(self):
        super().__init__(
            name="get_state",
            description="계산기의 현재 상태를 조회합니다",
            schema={
                "type": "object",
                "required": ["calculator_id"],
                "properties": {
                    "calculator_id": {"type": "string"}
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            
            return {
                "success": True,
                "calculator_id": calculator_id,
                "state": calculator["state"],
                "metadata": {
                    "type": calculator["type"],
                    "created_at": calculator["created_at"],
                    "last_modified": calculator["last_modified"],
                    "options": calculator["options"]
                },
                "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.getState();"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class SetStateTool(DesmosToolBase):
    """계산기 상태 설정 도구"""
    
    def __init__(self):
        super().__init__(
            name="set_state",
            description="계산기의 상태를 설정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "state"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "state": {"type": "object"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "allowUndo": {"type": "boolean", "default": True},
                            "remapColors": {"type": "boolean", "default": True}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, state: Dict[str, Any], 
                     options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"] = state
            calculator["last_modified"] = datetime.now().isoformat()
            
            set_options = options or {"allowUndo": True, "remapColors": True}
            
            return {
                "success": True,
                "calculator_id": calculator_id,
                "message": "계산기 상태 설정 완료",
                "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setState({json.dumps(state)}, {json.dumps(set_options)});"
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 5. 시각화 및 스타일링 도구들
# =============================================================================

class SetExpressionStyleTool(DesmosToolBase):
    """표현식 스타일 설정 도구"""
    
    def __init__(self):
        super().__init__(
            name="set_expression_style",
            description="표현식의 시각적 스타일을 설정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "expression_id"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "expression_id": {"type": "string"},
                    "style": {
                        "type": "object",
                        "properties": {
                            "color": {"type": "string"},
                            "lineStyle": {"type": "string", "enum": ["SOLID", "DASHED", "DOTTED"]},
                            "lineOpacity": {"type": "number", "minimum": 0, "maximum": 1},
                            "lineWidth": {"type": "number", "minimum": 0},
                            "pointStyle": {"type": "string", "enum": ["POINT", "OPEN", "CROSS"]},
                            "pointSize": {"type": "number", "minimum": 0},
                            "pointOpacity": {"type": "number", "minimum": 0, "maximum": 1},
                            "fillOpacity": {"type": "number", "minimum": 0, "maximum": 1},
                            "hidden": {"type": "boolean"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, expression_id: str, 
                     style: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            expressions_list = calculator["state"]["expressions"]["list"]
            
            # 표현식 찾기 및 스타일 업데이트
            for expr in expressions_list:
                if expr.get("id") == expression_id:
                    expr.update(style)
                    calculator["last_modified"] = datetime.now().isoformat()
                    
                    return {
                        "success": True,
                        "expression_id": expression_id,
                        "calculator_id": calculator_id,
                        "updated_style": style,
                        "message": f"표현식 '{expression_id}' 스타일 업데이트 완료",
                        "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expr)});"
                    }
            
            return {"success": False, "error": f"표현식 '{expression_id}'를 찾을 수 없습니다"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# MCP 도구 레지스트리
class DesmosToolRegistry:
    """Desmos MCP 도구 레지스트리"""
    
    def __init__(self):
        self.tools: Dict[str, DesmosToolBase] = {}
        self._register_all_tools()
    
    def _register_all_tools(self):
        """모든 도구 등록"""
        tools = [
            # 계산기 생성 도구들
            CreateGraphingCalculatorTool(),
            CreateScientificCalculatorTool(), 
            CreateFourFunctionCalculatorTool(),
            
            # 표현식 관리 도구들
            SetExpressionTool(),
            RemoveExpressionTool(),
            
            # 뷰포트 및 그래프 설정 도구들
            SetViewportTool(),
            
            # 상태 관리 도구들
            GetStateTool(),
            SetStateTool(),
            
            # 시각화 및 스타일링 도구들
            SetExpressionStyleTool()
        ]
        
        for tool in tools:
            self.tools[tool.name] = tool
            logger.info(f"🔧 Desmos MCP 도구 등록: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[DesmosToolBase]:
        """도구 조회"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> Dict[str, DesmosToolBase]:
        """모든 도구 반환"""
        return self.tools.copy()
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """모든 도구의 스키마 반환 (LLM 함수 호출용)"""
        schemas = []
        for tool in self.tools.values():
            schema = {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.schema
            }
            schemas.append(schema)
        return schemas

# 전역 레지스트리 인스턴스
desmos_tool_registry = DesmosToolRegistry()

async def execute_desmos_tool(tool_name: str, **kwargs) -> Dict[str, Any]:
    """Desmos 도구 실행 함수"""
    tool = desmos_tool_registry.get_tool(tool_name)
    if not tool:
        return {
            "success": False,
            "error": f"도구 '{tool_name}'을 찾을 수 없습니다. 사용 가능한 도구: {list(desmos_tool_registry.tools.keys())}"
        }
    
    if not tool.validate_parameters(kwargs):
        return {
            "success": False,
            "error": f"필수 파라미터가 누락되었습니다. 필요한 파라미터: {tool.schema.get('required', [])}"
        }
    
    return await tool.execute(**kwargs)