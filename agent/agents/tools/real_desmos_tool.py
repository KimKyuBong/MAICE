"""
실제 Desmos API v1.11을 사용하는 그래프 생성 도구
GPT가 자유롭게 호출해서 학습에 도움되는 인터랙티브 그래프를 만들 수 있음
"""

import logging
import json
import math
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from ..base_agent import Tool

logger = logging.getLogger(__name__)

class RealDesmosTool(Tool):
    """
    실제 Desmos API v1.11을 사용하는 그래프 생성 도구
    
    GPT가 호출할 수 있는 메인 기능들:
    - create_graph: 수학 질문 분석해서 자동으로 적절한 그래프 생성
    - set_expression: 수학 표현식 추가/수정
    - set_viewport: 그래프 보기 영역 설정
    - create_slider: 인터랙티브 슬라이더 생성
    - add_point: 특정 점 표시
    """
    
    def __init__(self):
        super().__init__(
            name="real_desmos_graph",
            description="실제 Desmos API v1.11을 사용해서 인터랙티브 그래프를 생성합니다. 수학 학습에 도움되는 시각화를 제공합니다."
        )
        self.logger = logging.getLogger(__name__)
        self.current_calculator_id = None
        self.expressions = []
        
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        도구 실행 - GPT가 호출하는 메인 함수
        
        사용 가능한 action들:
        - create_graph: 자동 그래프 생성 (question 필수)
        - set_expression: 표현식 설정 (latex 필수)
        - set_viewport: 뷰포트 설정 (xmin, ymin, xmax, ymax)
        - create_slider: 슬라이더 생성 (variable, min, max, step)
        - add_point: 점 추가 (x, y)
        """
        try:
            action = kwargs.get("action", "create_graph")
            
            if action == "create_graph":
                return await self._create_graph_from_question(kwargs.get("question", ""))
            elif action == "set_expression":
                return await self._set_expression(kwargs)
            elif action == "set_viewport":
                return await self._set_viewport(kwargs)
            elif action == "create_slider":
                return await self._create_slider(kwargs)
            elif action == "add_point":
                return await self._add_point(kwargs)
            else:
                return {"success": False, "error": f"알 수 없는 action: {action}"}
                
        except Exception as e:
            self.logger.error(f"Desmos 도구 실행 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "calculator_id": self.current_calculator_id
            }
    
    async def _create_graph_from_question(self, question: str) -> Dict[str, Any]:
        """질문을 분석해서 자동으로 적절한 그래프 생성"""
        try:
            self.logger.info(f"📊 Desmos 그래프 자동 생성: {question}")
            
            # 새 계산기 ID 생성
            self.current_calculator_id = f"desmos_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            self.expressions = []
            
            # 질문 분석 및 그래프 생성
            graph_data = await self._analyze_question_and_create_graph(question)
            
            if graph_data["success"]:
                # 완전한 JavaScript 코드 생성
                full_js_code = self._generate_complete_javascript()
                
                result = {
                    "success": True,
                    "calculator_id": self.current_calculator_id,
                    "question": question,
                    "concept_type": graph_data["concept_type"],
                    "expressions_count": len(self.expressions),
                    "expressions": self.expressions,
                    "javascript_code": full_js_code,
                    "usage_guide": graph_data["usage_guide"],
                    "learning_activities": graph_data["learning_activities"],
                    "message": f"✅ {graph_data['concept_type']} 그래프 생성 완료! 인터랙티브 요소 {len(self.expressions)}개 포함"
                }
                
                self.logger.info(f"✅ Desmos 그래프 생성 완료: {graph_data['concept_type']}")
                return result
            else:
                return graph_data
                
        except Exception as e:
            self.logger.error(f"그래프 자동 생성 오류: {e}")
            return {
                "success": False,
                "error": str(e),
                "calculator_id": self.current_calculator_id
            }
    
    async def _analyze_question_and_create_graph(self, question: str) -> Dict[str, Any]:
        """질문 분석 및 맞춤형 그래프 생성"""
        question_lower = question.lower()
        
        # 미분 관련
        if any(keyword in question_lower for keyword in ['미분', '도함수', 'derivative', "'"]):
            if any(keyword in question_lower for keyword in ['cos', '코사인']):
                return await self._create_cosine_derivative_graph()
            elif any(keyword in question_lower for keyword in ['sin', '사인']):
                return await self._create_sine_derivative_graph()
            elif any(keyword in question_lower for keyword in ['tan', '탄젠트']):
                return await self._create_tangent_derivative_graph()
            elif any(keyword in question_lower for keyword in ['log', 'ln', '로그']):
                return await self._create_log_derivative_graph()
        
        # 적분 관련
        elif any(keyword in question_lower for keyword in ['적분', 'integral', '넓이', '면적']):
            return await self._create_integral_graph(question)
        
        # 이차함수 관련
        elif any(keyword in question_lower for keyword in ['이차', '포물선', 'x²', 'x^2']):
            return await self._create_quadratic_graph(question)
        
        # 삼각함수 관련
        elif any(keyword in question_lower for keyword in ['삼각함수', 'sin', 'cos', 'tan', '사인', '코사인', '탄젠트']):
            return await self._create_trigonometry_graph()
        
        # 지수/로그함수 관련
        elif any(keyword in question_lower for keyword in ['지수', 'exp', 'log', 'ln', '로그']):
            return await self._create_exponential_log_graph()
        
        # 기본 함수 그래프
        else:
            return await self._create_basic_function_graph()
    
    async def _create_cosine_derivative_graph(self) -> Dict[str, Any]:
        """코사인 함수 미분 그래프"""
        # f(x) = cos(x)
        await self._add_expression({
            "id": "original",
            "latex": r"f(x)=\cos(x)",
            "color": "#c74440",
            "lineWidth": 3
        })
        
        # f'(x) = -sin(x)
        await self._add_expression({
            "id": "derivative", 
            "latex": r"f'(x)=-\sin(x)",
            "color": "#2d70b3",
            "lineWidth": 3
        })
        
        # 슬라이더 a
        await self._add_expression({
            "id": "slider_a",
            "latex": "a=1",
            "slider": {
                "hardMin": -2*math.pi,
                "hardMax": 2*math.pi,
                "step": 0.1
            }
        })
        
        # 접점
        await self._add_expression({
            "id": "point",
            "latex": r"(a,\cos(a))",
            "color": "#388c46",
            "showLabel": True,
            "label": "접점"
        })
        
        # 접선
        await self._add_expression({
            "id": "tangent",
            "latex": r"y-\cos(a)=-\sin(a)(x-a)",
            "color": "#fa7e19",
            "lineWidth": 2
        })
        
        # 뷰포트 설정
        await self._set_viewport({
            "xmin": -2*math.pi,
            "ymin": -2,
            "xmax": 2*math.pi,
            "ymax": 2
        })
        
        return {
            "success": True,
            "concept_type": "코사인 함수 미분",
            "usage_guide": "슬라이더를 움직여 다양한 점에서의 접선을 관찰하세요. 접선의 기울기가 -sin(a)와 일치함을 확인할 수 있습니다.",
            "learning_activities": [
                "슬라이더로 접점을 이동하며 접선의 기울기 변화 관찰",
                "cos(x)의 최댓값/최솟값에서 접선의 기울기는 0임을 확인",
                "도함수 그래프와 원함수의 접선 기울기 관계 이해"
            ]
        }
    
    async def _create_sine_derivative_graph(self) -> Dict[str, Any]:
        """사인 함수 미분 그래프"""
        # f(x) = sin(x)
        await self._add_expression({
            "id": "original",
            "latex": r"f(x)=\sin(x)",
            "color": "#c74440",
            "lineWidth": 3
        })
        
        # f'(x) = cos(x)
        await self._add_expression({
            "id": "derivative",
            "latex": r"f'(x)=\cos(x)",
            "color": "#2d70b3", 
            "lineWidth": 3
        })
        
        # 슬라이더
        await self._add_expression({
            "id": "slider_a",
            "latex": "a=1",
            "slider": {
                "hardMin": -2*math.pi,
                "hardMax": 2*math.pi,
                "step": 0.1
            }
        })
        
        # 접점
        await self._add_expression({
            "id": "point",
            "latex": r"(a,\sin(a))",
            "color": "#388c46",
            "showLabel": True,
            "label": "접점"
        })
        
        # 접선
        await self._add_expression({
            "id": "tangent",
            "latex": r"y-\sin(a)=\cos(a)(x-a)",
            "color": "#fa7e19",
            "lineWidth": 2
        })
        
        await self._set_viewport({
            "xmin": -2*math.pi,
            "ymin": -2,
            "xmax": 2*math.pi,
            "ymax": 2
        })
        
        return {
            "success": True,
            "concept_type": "사인 함수 미분",
            "usage_guide": "슬라이더로 접점을 이동하며 sin(x)의 접선을 관찰하세요. 도함수 cos(x)와의 관계를 확인할 수 있습니다.",
            "learning_activities": [
                "접선의 기울기가 cos(a)와 일치함을 확인",
                "sin(x)가 증가/감소하는 구간에서의 도함수 부호 관찰",
                "sin(x)의 변곡점과 도함수의 관계 이해"
            ]
        }
    
    async def _create_quadratic_graph(self, question: str) -> Dict[str, Any]:
        """이차함수 그래프"""
        # 기본 이차함수
        await self._add_expression({
            "id": "quadratic",
            "latex": r"f(x)=x^2-4x+3",
            "color": "#c74440",
            "lineWidth": 3
        })
        
        # 꼭짓점
        await self._add_expression({
            "id": "vertex",
            "latex": "(2,-1)",
            "color": "#388c46",
            "showLabel": True,
            "label": "꼭짓점"
        })
        
        # x절편
        await self._add_expression({
            "id": "x_intercepts",
            "latex": "(1,0), (3,0)",
            "color": "#2d70b3",
            "showLabel": True,
            "label": "x절편"
        })
        
        await self._set_viewport({
            "xmin": -1,
            "ymin": -2,
            "xmax": 5,
            "ymax": 4
        })
        
        return {
            "success": True,
            "concept_type": "이차함수 분석",
            "usage_guide": "이차함수의 꼭짓점, x절편, 개형을 확인하세요.",
            "learning_activities": [
                "꼭짓점의 좌표와 최솟값 확인",
                "x절편과 이차방정식의 근 관계 이해",
                "대칭축과 함수의 성질 관찰"
            ]
        }
    
    async def _create_trigonometry_graph(self) -> Dict[str, Any]:
        """기본 삼각함수들"""
        await self._add_expression({
            "id": "sin",
            "latex": r"y=\sin(x)",
            "color": "#c74440",
            "lineWidth": 2
        })
        
        await self._add_expression({
            "id": "cos", 
            "latex": r"y=\cos(x)",
            "color": "#2d70b3",
            "lineWidth": 2
        })
        
        await self._add_expression({
            "id": "tan",
            "latex": r"y=\tan(x)",
            "color": "#388c46"
        })
        
        await self._set_viewport({
            "xmin": -2*math.pi,
            "ymin": -3,
            "xmax": 2*math.pi,
            "ymax": 3
        })
        
        return {
            "success": True,
            "concept_type": "기본 삼각함수",
            "usage_guide": "sin(x), cos(x), tan(x)의 주기성과 특성을 비교해보세요.",
            "learning_activities": [
                "각 함수의 주기 비교 (sin, cos: 2π, tan: π)",
                "함수값의 범위 확인",
                "대칭성과 특별한 각에서의 함수값 관찰"
            ]
        }
    
    async def _create_basic_function_graph(self) -> Dict[str, Any]:
        """기본 함수 그래프"""
        await self._add_expression({
            "id": "linear",
            "latex": "y=x",
            "color": "#c74440"
        })
        
        await self._add_expression({
            "id": "quadratic",
            "latex": "y=x^2",
            "color": "#2d70b3"
        })
        
        await self._add_expression({
            "id": "cubic",
            "latex": "y=x^3",
            "color": "#388c46"
        })
        
        await self._set_viewport({
            "xmin": -3,
            "ymin": -3,
            "xmax": 3,
            "ymax": 3
        })
        
        return {
            "success": True,
            "concept_type": "기본 함수들",
            "usage_guide": "일차, 이차, 삼차 함수의 기본 모양을 비교해보세요.",
            "learning_activities": [
                "함수의 차수에 따른 그래프 모양 변화 관찰",
                "각 함수의 증가/감소 구간 확인",
                "함수의 대칭성 비교"
            ]
        }
    
    async def _set_expression(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """표현식 설정"""
        latex = kwargs.get("latex")
        if not latex:
            return {"success": False, "error": "latex 매개변수가 필요합니다"}
        
        expression = {
            "id": kwargs.get("id", f"expr_{len(self.expressions) + 1}"),
            "latex": latex
        }
        
        # 선택적 속성들 추가
        for attr in ["color", "hidden", "points", "lines", "lineWidth", "showLabel", "label"]:
            if attr in kwargs:
                expression[attr] = kwargs[attr]
        
        await self._add_expression(expression)
        
        return {
            "success": True,
            "expression_id": expression["id"],
            "message": f"표현식 '{latex}' 추가 완료"
        }
    
    async def _set_viewport(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """뷰포트 설정"""
        self.viewport = {}
        for coord in ["xmin", "ymin", "xmax", "ymax"]:
            if coord in kwargs:
                self.viewport[coord] = kwargs[coord]
        
        return {
            "success": True,
            "viewport": self.viewport,
            "message": "뷰포트 설정 완료"
        }
    
    async def _create_slider(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """슬라이더 생성"""
        variable = kwargs.get("variable", "a")
        min_val = kwargs.get("min", -10)
        max_val = kwargs.get("max", 10)
        step = kwargs.get("step", 0.1)
        default_val = kwargs.get("default", (min_val + max_val) / 2)
        
        slider_expr = {
            "id": f"slider_{variable}",
            "latex": f"{variable}={default_val}",
            "slider": {
                "hardMin": min_val,
                "hardMax": max_val,
                "step": step
            }
        }
        
        await self._add_expression(slider_expr)
        
        return {
            "success": True,
            "variable": variable,
            "slider_id": slider_expr["id"],
            "message": f"슬라이더 '{variable}' 생성 완료"
        }
    
    async def _add_point(self, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """점 추가"""
        x = kwargs.get("x", 0)
        y = kwargs.get("y", 0)
        color = kwargs.get("color", "#388c46")
        label = kwargs.get("label", f"({x},{y})")
        
        point_expr = {
            "id": f"point_{len(self.expressions) + 1}",
            "latex": f"({x},{y})",
            "color": color,
            "showLabel": True,
            "label": label
        }
        
        await self._add_expression(point_expr)
        
        return {
            "success": True,
            "point_id": point_expr["id"],
            "coordinates": (x, y),
            "message": f"점 ({x},{y}) 추가 완료"
        }
    
    async def _add_expression(self, expression: Dict[str, Any]):
        """표현식을 목록에 추가"""
        self.expressions.append(expression)
        self.logger.debug(f"표현식 추가: {expression['latex']}")
    
    def _generate_complete_javascript(self) -> str:
        """완전한 JavaScript 코드 생성"""
        if not self.current_calculator_id:
            return ""
        
        js_code = f"""
// 실제 Desmos API v1.11 그래프 생성 코드
(function() {{
    // DOM 엘리먼트 생성 또는 기존 엘리먼트 사용
    let element = document.getElementById('{self.current_calculator_id}');
    if (!element) {{
        element = document.createElement('div');
        element.id = '{self.current_calculator_id}';
        element.style.width = '100%';
        element.style.height = '400px';
        
        // 그래프 컨테이너에 추가
        const container = document.getElementById('graphContainer') || document.body;
        container.innerHTML = '';
        container.appendChild(element);
    }}
    
    // Desmos 계산기 생성
    const calculator = Desmos.GraphingCalculator(element, {{
        keypad: false,
        graphpaper: true,
        expressions: true,
        settingsMenu: false,
        expressionsTopbar: false,
        language: 'ko'
    }});
    
    // 전역 변수로 저장
    window.desmosCalculators = window.desmosCalculators || {{}};
    window.desmosCalculators['{self.current_calculator_id}'] = calculator;
"""
        
        # 모든 표현식 추가
        for expr in self.expressions:
            js_code += f"""    
    calculator.setExpression({json.dumps(expr, ensure_ascii=False)});"""
        
        # 뷰포트 설정 (있는 경우)
        if hasattr(self, 'viewport') and self.viewport:
            js_code += f"""
    
    calculator.setMathBounds({json.dumps(self.viewport)});"""
        
        js_code += f"""
    
    console.log('✅ Desmos 그래프 생성 완료:', '{self.current_calculator_id}');
    console.log('📊 표현식 개수:', {len(self.expressions)});
    
    return calculator;
}})();
"""
        
        return js_code

# 에이전트에서 사용할 전역 인스턴스
real_desmos_agent_tool = RealDesmosTool()