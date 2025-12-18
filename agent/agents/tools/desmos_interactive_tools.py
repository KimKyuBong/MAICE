"""
Desmos 인터랙티브 기능 MCP 도구들
슬라이더, 애니메이션, 이벤트, 스크린샷 등 고급 기능
"""

import logging
import json
import asyncio
from typing import Dict, Any, List, Optional, Union, Callable
from datetime import datetime
import uuid
import base64

from .desmos_mcp_system import DesmosToolBase, DesmosCalculatorManager

logger = logging.getLogger(__name__)

# =============================================================================
# 6. 슬라이더 및 애니메이션 도구들
# =============================================================================

class CreateSliderTool(DesmosToolBase):
    """슬라이더 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_slider",
            description="매개변수 조작을 위한 슬라이더를 생성합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "variable", "min_value", "max_value"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "variable": {"type": "string", "description": "슬라이더 변수명 (예: 'a', 'b', 'c')"},
                    "min_value": {"type": "number", "description": "최솟값"},
                    "max_value": {"type": "number", "description": "최댓값"},
                    "default_value": {"type": "number", "description": "기본값"},
                    "step": {"type": "number", "description": "증감 단위", "default": 0.1},
                    "animation": {
                        "type": "object",
                        "properties": {
                            "period": {"type": "number", "description": "애니메이션 주기 (초)", "default": 4.0},
                            "loop_mode": {
                                "type": "string", 
                                "enum": ["LOOP_FORWARD_REVERSE", "LOOP_FORWARD", "PLAY_ONCE", "PLAY_INDEFINITELY"],
                                "default": "LOOP_FORWARD_REVERSE"
                            },
                            "auto_play": {"type": "boolean", "default": False}
                        }
                    },
                    "label": {"type": "string", "description": "슬라이더 라벨"},
                    "color": {"type": "string", "description": "슬라이더 색상"}
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, variable: str, min_value: float, max_value: float,
                     default_value: float = None, step: float = 0.1, animation: Dict[str, Any] = None,
                     label: str = None, color: str = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            if default_value is None:
                default_value = (min_value + max_value) / 2
            
            # 슬라이더 표현식 생성
            slider_expr = {
                "id": f"slider_{variable}",
                "latex": f"{variable}={default_value}",
                "slider": {
                    "hardMin": min_value,
                    "hardMax": max_value,
                    "step": step
                }
            }
            
            # 애니메이션 설정
            if animation:
                slider_expr["slider"].update({
                    "animationPeriod": animation.get("period", 4.0),
                    "loopMode": animation.get("loop_mode", "LOOP_FORWARD_REVERSE")
                })
                
                if animation.get("auto_play", False):
                    slider_expr["slider"]["isPlaying"] = True
            
            # 스타일 설정
            if label:
                slider_expr["label"] = label
                slider_expr["showLabel"] = True
            
            if color:
                slider_expr["color"] = color
            
            # 계산기에 추가
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"]["expressions"]["list"].append(slider_expr)
            calculator["last_modified"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "slider_id": slider_expr["id"],
                "variable": variable,
                "calculator_id": calculator_id,
                "range": {"min": min_value, "max": max_value, "default": default_value},
                "message": f"슬라이더 '{variable}' 생성 완료",
                "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(slider_expr)});"
            }
            
        except Exception as e:
            logger.error(f"슬라이더 생성 오류: {e}")
            return {"success": False, "error": str(e)}

class AnimateSliderTool(DesmosToolBase):
    """슬라이더 애니메이션 제어 도구"""
    
    def __init__(self):
        super().__init__(
            name="animate_slider",
            description="슬라이더 애니메이션을 시작, 중지, 또는 설정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "variable", "action"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "variable": {"type": "string"},
                    "action": {"type": "string", "enum": ["play", "pause", "reset", "configure"]},
                    "config": {
                        "type": "object",
                        "properties": {
                            "period": {"type": "number"},
                            "loop_mode": {"type": "string", "enum": ["LOOP_FORWARD_REVERSE", "LOOP_FORWARD", "PLAY_ONCE", "PLAY_INDEFINITELY"]}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, variable: str, action: str, 
                     config: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            calculator = self.calculator_manager.calculators[calculator_id]
            expressions_list = calculator["state"]["expressions"]["list"]
            
            # 슬라이더 찾기
            slider_id = f"slider_{variable}"
            for expr in expressions_list:
                if expr.get("id") == slider_id and "slider" in expr:
                    if action == "play":
                        expr["slider"]["isPlaying"] = True
                    elif action == "pause":
                        expr["slider"]["isPlaying"] = False
                    elif action == "reset":
                        expr["slider"]["isPlaying"] = False
                        # 기본값으로 재설정
                        hardMin = expr["slider"].get("hardMin", 0)
                        hardMax = expr["slider"].get("hardMax", 1)
                        default_value = (hardMin + hardMax) / 2
                        expr["latex"] = f"{variable}={default_value}"
                    elif action == "configure" and config:
                        if "period" in config:
                            expr["slider"]["animationPeriod"] = config["period"]
                        if "loop_mode" in config:
                            expr["slider"]["loopMode"] = config["loop_mode"]
                    
                    calculator["last_modified"] = datetime.now().isoformat()
                    
                    return {
                        "success": True,
                        "variable": variable,
                        "action": action,
                        "calculator_id": calculator_id,
                        "message": f"슬라이더 '{variable}' {action} 완료",
                        "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expr)});"
                    }
            
            return {"success": False, "error": f"슬라이더 변수 '{variable}'를 찾을 수 없습니다"}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 7. 이벤트 및 상호작용 도구들
# =============================================================================

class ObserveEventTool(DesmosToolBase):
    """이벤트 관찰 설정 도구"""
    
    def __init__(self):
        super().__init__(
            name="observe_event",
            description="계산기 이벤트를 관찰하고 콜백을 설정합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "event_type"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "event_type": {
                        "type": "string",
                        "enum": ["change", "click", "mousemove", "zoom", "resize"]
                    },
                    "callback_id": {"type": "string", "description": "콜백 함수 식별자"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "throttle": {"type": "number", "description": "이벤트 스로틀링 (ms)"},
                            "expression_filter": {"type": "string", "description": "특정 표현식만 필터링"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
        self.event_observers: Dict[str, Dict[str, Any]] = {}
    
    async def execute(self, calculator_id: str, event_type: str, callback_id: str = None,
                     options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            if callback_id is None:
                callback_id = f"callback_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            observer_key = f"{calculator_id}_{event_type}_{callback_id}"
            
            # 이벤트 관찰자 등록
            self.event_observers[observer_key] = {
                "calculator_id": calculator_id,
                "event_type": event_type,
                "callback_id": callback_id,
                "options": options or {},
                "created_at": datetime.now().isoformat()
            }
            
            # JavaScript 코드 생성
            js_options = ""
            if options:
                if "throttle" in options:
                    js_options += f", throttle: {options['throttle']}"
                if "expression_filter" in options:
                    js_options += f", expressionFilter: '{options['expression_filter']}'"
            
            javascript_code = f"""
            calculator_{calculator_id.replace('-', '_')}.observeEvent('{event_type}', function(event) {{
                // 콜백 ID: {callback_id}
                console.log('Desmos {event_type} event:', event);
                // 여기에 사용자 정의 로직 추가
            }}{js_options});
            """
            
            return {
                "success": True,
                "observer_key": observer_key,
                "callback_id": callback_id,
                "event_type": event_type,
                "calculator_id": calculator_id,
                "message": f"'{event_type}' 이벤트 관찰 설정 완료",
                "javascript_code": javascript_code.strip()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class UnobserveEventTool(DesmosToolBase):
    """이벤트 관찰 해제 도구"""
    
    def __init__(self):
        super().__init__(
            name="unobserve_event",
            description="계산기 이벤트 관찰을 해제합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "event_type"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "event_type": {"type": "string"},
                    "callback_id": {"type": "string", "description": "특정 콜백만 해제할 경우"}
                }
            }
        )
        self.event_observers: Dict[str, Dict[str, Any]] = {}
    
    async def execute(self, calculator_id: str, event_type: str, callback_id: str = None) -> Dict[str, Any]:
        try:
            removed_observers = []
            
            # 해제할 관찰자들 찾기
            for key, observer in list(self.event_observers.items()):
                if (observer["calculator_id"] == calculator_id and 
                    observer["event_type"] == event_type and
                    (callback_id is None or observer["callback_id"] == callback_id)):
                    removed_observers.append(self.event_observers.pop(key))
            
            if removed_observers:
                javascript_code = f"calculator_{calculator_id.replace('-', '_')}.unobserveEvent('{event_type}');"
                return {
                    "success": True,
                    "removed_count": len(removed_observers),
                    "event_type": event_type,
                    "calculator_id": calculator_id,
                    "message": f"'{event_type}' 이벤트 관찰 해제 완료",
                    "javascript_code": javascript_code
                }
            else:
                return {
                    "success": False,
                    "error": f"해제할 '{event_type}' 이벤트 관찰자를 찾을 수 없습니다"
                }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

# =============================================================================
# 8. 스크린샷 및 내보내기 도구들
# =============================================================================

class TakeScreenshotTool(DesmosToolBase):
    """그래프 스크린샷 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="take_screenshot",
            description="현재 그래프의 스크린샷을 생성합니다",
            schema={
                "type": "object",
                "required": ["calculator_id"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "options": {
                        "type": "object",
                        "properties": {
                            "width": {"type": "integer", "default": 800, "minimum": 100, "maximum": 2000},
                            "height": {"type": "integer", "default": 600, "minimum": 100, "maximum": 2000},
                            "format": {"type": "string", "enum": ["png", "jpeg", "svg"], "default": "png"},
                            "quality": {"type": "number", "minimum": 0.1, "maximum": 1.0, "default": 1.0},
                            "background_color": {"type": "string", "default": "#ffffff"},
                            "include_expressions": {"type": "boolean", "default": False},
                            "expressions_width": {"type": "integer", "default": 300}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, options: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            screenshot_options = {
                "width": 800,
                "height": 600,
                "format": "png",
                "quality": 1.0,
                "background_color": "#ffffff",
                "include_expressions": False,
                "expressions_width": 300
            }
            
            if options:
                screenshot_options.update(options)
            
            # 스크린샷 ID 생성
            screenshot_id = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # JavaScript 옵션 구성
            js_options = {
                "width": screenshot_options["width"],
                "height": screenshot_options["height"],
                "targetPixelRatio": 1,
                "format": screenshot_options["format"]
            }
            
            if screenshot_options["format"] == "jpeg":
                js_options["quality"] = screenshot_options["quality"]
            
            if screenshot_options["include_expressions"]:
                js_options["showExpressions"] = True
                js_options["expressionsWidth"] = screenshot_options["expressions_width"]
            
            # 비동기 스크린샷을 위한 JavaScript 코드
            javascript_code = f"""
            calculator_{calculator_id.replace('-', '_')}.asyncScreenshot({json.dumps(js_options)}).then(function(dataURL) {{
                console.log('스크린샷 생성 완료:', dataURL);
                // dataURL을 서버로 전송하거나 다운로드 링크 생성
                var link = document.createElement('a');
                link.download = '{screenshot_id}.{screenshot_options["format"]}';
                link.href = dataURL;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }}).catch(function(error) {{
                console.error('스크린샷 생성 오류:', error);
            }});
            """
            
            return {
                "success": True,
                "screenshot_id": screenshot_id,
                "calculator_id": calculator_id,
                "options": screenshot_options,
                "message": f"스크린샷 '{screenshot_id}' 생성 요청 완료",
                "javascript_code": javascript_code.strip(),
                "download_filename": f"{screenshot_id}.{screenshot_options['format']}"
            }
            
        except Exception as e:
            logger.error(f"스크린샷 생성 오류: {e}")
            return {"success": False, "error": str(e)}

# =============================================================================
# 9. 고급 수학 기능 도구들
# =============================================================================

class EvaluateExpressionTool(DesmosToolBase):
    """수학 표현식 계산 도구"""
    
    def __init__(self):
        super().__init__(
            name="evaluate_expression",
            description="수학 표현식을 계산하고 결과를 반환합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "expression"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "expression": {"type": "string", "description": "계산할 LaTeX 표현식"},
                    "variables": {
                        "type": "object",
                        "description": "변수 값들",
                        "additionalProperties": {"type": "number"}
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, expression: str, 
                     variables: Dict[str, float] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            # 변수값 설정
            js_variables = ""
            if variables:
                for var, value in variables.items():
                    js_variables += f"calculator_{calculator_id.replace('-', '_')}.setExpression({{latex: '{var}={value}'}});\n"
            
            javascript_code = f"""
            {js_variables}
            // 표현식 계산
            var result = calculator_{calculator_id.replace('-', '_')}.HelperExpression({{latex: '{expression}'}});
            console.log('계산 결과:', result.numericValue);
            """
            
            return {
                "success": True,
                "expression": expression,
                "variables": variables or {},
                "calculator_id": calculator_id,
                "message": f"표현식 '{expression}' 계산 요청 완료",
                "javascript_code": javascript_code.strip()
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class CreateTableTool(DesmosToolBase):
    """데이터 테이블 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_table",
            description="데이터 테이블을 생성하고 시각화합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "data"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "data": {
                        "type": "object",
                        "properties": {
                            "x_values": {"type": "array", "items": {"type": "number"}},
                            "y_values": {"type": "array", "items": {"type": "number"}},
                            "column_names": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["x_values", "y_values"]
                    },
                    "style": {
                        "type": "object",
                        "properties": {
                            "color": {"type": "string"},
                            "point_style": {"type": "string", "enum": ["POINT", "OPEN", "CROSS"]},
                            "point_size": {"type": "number"},
                            "lines": {"type": "boolean", "default": False}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, data: Dict[str, Any], 
                     style: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            x_values = data["x_values"]
            y_values = data["y_values"]
            
            if len(x_values) != len(y_values):
                return {"success": False, "error": "x값과 y값의 개수가 일치하지 않습니다"}
            
            # 테이블 표현식 생성
            table_id = f"table_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            table_expr = {
                "id": table_id,
                "type": "table",
                "columns": [
                    {
                        "latex": "x_1",
                        "values": [str(x) for x in x_values],
                        "hidden": False
                    },
                    {
                        "latex": "y_1",
                        "values": [str(y) for y in y_values],
                        "hidden": False,
                        "color": style.get("color", "#2d70b3") if style else "#2d70b3"
                    }
                ]
            }
            
            # 스타일 적용
            if style:
                if "point_style" in style:
                    table_expr["columns"][1]["pointStyle"] = style["point_style"]
                if "point_size" in style:
                    table_expr["columns"][1]["pointSize"] = style["point_size"]
                if "lines" in style:
                    table_expr["columns"][1]["lines"] = style["lines"]
            
            # 계산기에 추가
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"]["expressions"]["list"].append(table_expr)
            calculator["last_modified"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "table_id": table_id,
                "calculator_id": calculator_id,
                "data_points": len(x_values),
                "message": f"테이블 '{table_id}' 생성 완료 ({len(x_values)}개 데이터 포인트)",
                "javascript_code": f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(table_expr)});"
            }
            
        except Exception as e:
            logger.error(f"테이블 생성 오류: {e}")
            return {"success": False, "error": str(e)}