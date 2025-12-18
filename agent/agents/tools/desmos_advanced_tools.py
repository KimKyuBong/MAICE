"""
Desmos 고급 수학 기능 MCP 도구들
통계 분포, 3D 그래프, 기하학, 복소수 등 전문 기능
"""

import logging
import json
import math
import cmath
from typing import Dict, Any, List, Optional, Union, Tuple
from datetime import datetime
import uuid

from .desmos_mcp_system import DesmosToolBase, DesmosCalculatorManager

logger = logging.getLogger(__name__)

# =============================================================================
# 10. 통계 및 분포 도구들
# =============================================================================

class CreateDistributionTool(DesmosToolBase):
    """통계 분포 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_distribution",
            description="다양한 통계 분포를 생성하고 시각화합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "distribution_type"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "distribution_type": {
                        "type": "string",
                        "enum": ["normal", "binomial", "poisson", "exponential", "uniform", "beta", "gamma", "chi_square", "t_distribution", "f_distribution"]
                    },
                    "parameters": {
                        "type": "object",
                        "description": "분포별 매개변수들",
                        "additionalProperties": {"type": "number"}
                    },
                    "range": {
                        "type": "object",
                        "properties": {
                            "x_min": {"type": "number"},
                            "x_max": {"type": "number"},
                            "samples": {"type": "integer", "default": 1000}
                        }
                    },
                    "visualization": {
                        "type": "object",
                        "properties": {
                            "show_pdf": {"type": "boolean", "default": True},
                            "show_cdf": {"type": "boolean", "default": False},
                            "show_area": {"type": "boolean", "default": False},
                            "area_bounds": {
                                "type": "object",
                                "properties": {
                                    "lower": {"type": "number"},
                                    "upper": {"type": "number"}
                                }
                            },
                            "color": {"type": "string", "default": "#2d70b3"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, distribution_type: str, 
                     parameters: Dict[str, float] = None, range_config: Dict[str, Any] = None,
                     visualization: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            # 기본 설정
            params = parameters or {}
            vis_config = visualization or {}
            range_cfg = range_config or {}
            
            # 분포별 LaTeX 표현식 생성
            distribution_latex = await self._generate_distribution_latex(distribution_type, params)
            if not distribution_latex:
                return {"success": False, "error": f"지원하지 않는 분포 타입: {distribution_type}"}
            
            expressions = []
            dist_id = f"dist_{distribution_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            
            # PDF 표시
            if vis_config.get("show_pdf", True):
                pdf_expr = {
                    "id": f"{dist_id}_pdf",
                    "latex": distribution_latex["pdf"],
                    "color": vis_config.get("color", "#2d70b3"),
                    "label": f"{distribution_type.upper()} PDF",
                    "showLabel": True
                }
                expressions.append(pdf_expr)
            
            # CDF 표시
            if vis_config.get("show_cdf", False):
                if "cdf" in distribution_latex:
                    cdf_expr = {
                        "id": f"{dist_id}_cdf",
                        "latex": distribution_latex["cdf"],
                        "color": "#388c46",
                        "label": f"{distribution_type.upper()} CDF",
                        "showLabel": True,
                        "lineStyle": "DASHED"
                    }
                    expressions.append(cdf_expr)
            
            # 영역 표시
            if vis_config.get("show_area", False) and "area_bounds" in vis_config:
                bounds = vis_config["area_bounds"]
                if "lower" in bounds and "upper" in bounds:
                    area_expr = {
                        "id": f"{dist_id}_area",
                        "latex": f"{bounds['lower']} \\le x \\le {bounds['upper']}",
                        "color": vis_config.get("color", "#2d70b3"),
                        "fillOpacity": 0.3
                    }
                    expressions.append(area_expr)
            
            # 매개변수 슬라이더 추가
            for param_name, param_value in params.items():
                slider_expr = {
                    "id": f"{dist_id}_{param_name}",
                    "latex": f"{param_name}={param_value}",
                    "slider": self._get_parameter_slider_config(distribution_type, param_name, param_value)
                }
                expressions.append(slider_expr)
            
            # 계산기에 추가
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"]["expressions"]["list"].extend(expressions)
            calculator["last_modified"] = datetime.now().isoformat()
            
            # 통계량 계산
            statistics = await self._calculate_distribution_statistics(distribution_type, params)
            
            return {
                "success": True,
                "distribution_id": dist_id,
                "distribution_type": distribution_type,
                "parameters": params,
                "expressions_added": len(expressions),
                "statistics": statistics,
                "calculator_id": calculator_id,
                "message": f"{distribution_type} 분포 생성 완료",
                "javascript_code": "\n".join([
                    f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expr)});"
                    for expr in expressions
                ])
            }
            
        except Exception as e:
            logger.error(f"분포 생성 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _generate_distribution_latex(self, dist_type: str, params: Dict[str, float]) -> Optional[Dict[str, str]]:
        """분포별 LaTeX 표현식 생성"""
        distributions = {
            "normal": {
                "pdf": f"f(x)=\\frac{{1}}{{\\sigma\\sqrt{{2\\pi}}}}e^{{-\\frac{{(x-\\mu)^2}}{{2\\sigma^2}}}}",
                "cdf": "F(x)=\\frac{1}{2}[1+\\text{erf}(\\frac{x-\\mu}{\\sigma\\sqrt{2}})]",
                "default_params": {"μ": 0, "σ": 1}
            },
            "exponential": {
                "pdf": "f(x)=\\lambda e^{-\\lambda x}",
                "cdf": "F(x)=1-e^{-\\lambda x}",
                "default_params": {"λ": 1}
            },
            "uniform": {
                "pdf": "f(x)=\\frac{1}{b-a}",
                "cdf": "F(x)=\\frac{x-a}{b-a}",
                "default_params": {"a": 0, "b": 1}
            },
            "poisson": {
                "pdf": "f(k)=\\frac{\\lambda^k e^{-\\lambda}}{k!}",
                "default_params": {"λ": 2}
            },
            "binomial": {
                "pdf": "f(k)=\\binom{n}{k}p^k(1-p)^{n-k}",
                "default_params": {"n": 10, "p": 0.5}
            }
        }
        
        if dist_type not in distributions:
            return None
        
        # 매개변수 기본값 적용
        dist_info = distributions[dist_type]
        merged_params = {**dist_info["default_params"], **params}
        
        # LaTeX에서 매개변수 치환
        latex_expressions = {}
        for key, latex in dist_info.items():
            if key != "default_params":
                for param, value in merged_params.items():
                    latex = latex.replace(f"\\{param}", str(value))
                latex_expressions[key] = latex
        
        return latex_expressions
    
    def _get_parameter_slider_config(self, dist_type: str, param_name: str, current_value: float) -> Dict[str, Any]:
        """분포 매개변수별 슬라이더 설정"""
        slider_configs = {
            "normal": {
                "μ": {"hardMin": -5, "hardMax": 5, "step": 0.1},
                "σ": {"hardMin": 0.1, "hardMax": 3, "step": 0.1}
            },
            "exponential": {
                "λ": {"hardMin": 0.1, "hardMax": 5, "step": 0.1}
            },
            "uniform": {
                "a": {"hardMin": -5, "hardMax": 5, "step": 0.1},
                "b": {"hardMin": -5, "hardMax": 5, "step": 0.1}
            },
            "poisson": {
                "λ": {"hardMin": 0.1, "hardMax": 10, "step": 0.1}
            },
            "binomial": {
                "n": {"hardMin": 1, "hardMax": 50, "step": 1},
                "p": {"hardMin": 0, "hardMax": 1, "step": 0.01}
            }
        }
        
        return slider_configs.get(dist_type, {}).get(param_name, {
            "hardMin": 0,
            "hardMax": 10,
            "step": 0.1
        })
    
    async def _calculate_distribution_statistics(self, dist_type: str, params: Dict[str, float]) -> Dict[str, float]:
        """분포의 통계량 계산"""
        try:
            if dist_type == "normal":
                μ = params.get("μ", 0)
                σ = params.get("σ", 1)
                return {
                    "mean": μ,
                    "variance": σ ** 2,
                    "std_dev": σ,
                    "skewness": 0,
                    "kurtosis": 0
                }
            elif dist_type == "exponential":
                λ = params.get("λ", 1)
                return {
                    "mean": 1 / λ,
                    "variance": 1 / (λ ** 2),
                    "std_dev": 1 / λ,
                    "skewness": 2,
                    "kurtosis": 6
                }
            elif dist_type == "uniform":
                a = params.get("a", 0)
                b = params.get("b", 1)
                return {
                    "mean": (a + b) / 2,
                    "variance": ((b - a) ** 2) / 12,
                    "std_dev": (b - a) / math.sqrt(12)
                }
            # 더 많은 분포 추가 가능
            else:
                return {}
        except Exception:
            return {}

# =============================================================================
# 11. 3D 및 극좌표 도구들
# =============================================================================

class Create3DGraphTool(DesmosToolBase):
    """3D 그래프 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_3d_graph",
            description="3D 그래프와 곡면을 생성합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "function_type"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "function_type": {
                        "type": "string",
                        "enum": ["parametric_surface", "implicit_surface", "vector_field", "parametric_curve"]
                    },
                    "equations": {
                        "type": "object",
                        "properties": {
                            "x": {"type": "string", "description": "x(u,v) 또는 x(t) 방정식"},
                            "y": {"type": "string", "description": "y(u,v) 또는 y(t) 방정식"},
                            "z": {"type": "string", "description": "z(u,v) 또는 z(t) 방정식"},
                            "implicit": {"type": "string", "description": "F(x,y,z)=0 형태의 암시함수"}
                        }
                    },
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "u_range": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}}},
                            "v_range": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}}},
                            "t_range": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}}}
                        }
                    },
                    "style": {
                        "type": "object",
                        "properties": {
                            "color": {"type": "string"},
                            "opacity": {"type": "number", "minimum": 0, "maximum": 1},
                            "wireframe": {"type": "boolean", "default": False},
                            "mesh_density": {"type": "integer", "default": 20}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, function_type: str, 
                     equations: Dict[str, str], parameters: Dict[str, Any] = None,
                     style: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            graph_id = f"3d_{function_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            expressions = []
            
            # 3D 그래프는 Desmos에서 제한적으로 지원되므로 parametric으로 근사
            if function_type == "parametric_surface":
                expressions.extend(await self._create_parametric_surface(graph_id, equations, parameters, style))
            elif function_type == "parametric_curve":
                expressions.extend(await self._create_parametric_curve(graph_id, equations, parameters, style))
            elif function_type == "vector_field":
                expressions.extend(await self._create_vector_field(graph_id, equations, parameters, style))
            else:
                return {"success": False, "error": f"지원하지 않는 3D 그래프 타입: {function_type}"}
            
            # 계산기에 추가
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"]["expressions"]["list"].extend(expressions)
            calculator["last_modified"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "graph_id": graph_id,
                "function_type": function_type,
                "expressions_added": len(expressions),
                "calculator_id": calculator_id,
                "message": f"3D {function_type} 그래프 생성 완료",
                "javascript_code": "\n".join([
                    f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expr)});"
                    for expr in expressions
                ])
            }
            
        except Exception as e:
            logger.error(f"3D 그래프 생성 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_parametric_surface(self, graph_id: str, equations: Dict[str, str], 
                                       parameters: Dict[str, Any], style: Dict[str, Any]) -> List[Dict[str, Any]]:
        """매개변수 곡면 생성 (2D 투영으로 근사)"""
        expressions = []
        
        # u, v 매개변수 슬라이더
        u_range = parameters.get("u_range", {"min": -2, "max": 2})
        v_range = parameters.get("v_range", {"min": -2, "max": 2})
        
        expressions.extend([
            {
                "id": f"{graph_id}_u",
                "latex": f"u=0",
                "slider": {"hardMin": u_range["min"], "hardMax": u_range["max"], "step": 0.1}
            },
            {
                "id": f"{graph_id}_v", 
                "latex": f"v=0",
                "slider": {"hardMin": v_range["min"], "hardMax": v_range["max"], "step": 0.1}
            }
        ])
        
        # x-y 평면 투영
        if "x" in equations and "y" in equations:
            expressions.append({
                "id": f"{graph_id}_xy",
                "latex": f"({equations['x']},{equations['y']})",
                "color": style.get("color", "#c74440") if style else "#c74440",
                "parametricDomain": {"min": str(u_range["min"]), "max": str(u_range["max"])},
                "label": "XY 투영"
            })
        
        # x-z 평면 투영 (z를 y로 표시)
        if "x" in equations and "z" in equations:
            expressions.append({
                "id": f"{graph_id}_xz",
                "latex": f"({equations['x']},{equations['z']})",
                "color": style.get("color", "#2d70b3") if style else "#2d70b3",
                "parametricDomain": {"min": str(u_range["min"]), "max": str(u_range["max"])},
                "label": "XZ 투영",
                "hidden": True
            })
        
        return expressions
    
    async def _create_parametric_curve(self, graph_id: str, equations: Dict[str, str],
                                     parameters: Dict[str, Any], style: Dict[str, Any]) -> List[Dict[str, Any]]:
        """매개변수 곡선 생성"""
        expressions = []
        
        t_range = parameters.get("t_range", {"min": -2, "max": 2})
        
        # t 매개변수 슬라이더
        expressions.append({
            "id": f"{graph_id}_t",
            "latex": "t=0",
            "slider": {"hardMin": t_range["min"], "hardMax": t_range["max"], "step": 0.1}
        })
        
        # 매개변수 곡선
        if "x" in equations and "y" in equations:
            expressions.append({
                "id": f"{graph_id}_curve",
                "latex": f"({equations['x']},{equations['y']})",
                "color": style.get("color", "#c74440") if style else "#c74440",
                "parametricDomain": {"min": str(t_range["min"]), "max": str(t_range["max"])},
                "label": "매개변수 곡선"
            })
        
        return expressions
    
    async def _create_vector_field(self, graph_id: str, equations: Dict[str, str],
                                 parameters: Dict[str, Any], style: Dict[str, Any]) -> List[Dict[str, Any]]:
        """벡터 필드 생성"""
        expressions = []
        
        # 벡터 필드 샘플 점들
        grid_size = style.get("mesh_density", 10) if style else 10
        step = 2.0 / grid_size
        
        for i in range(-grid_size // 2, grid_size // 2 + 1, 2):
            for j in range(-grid_size // 2, grid_size // 2 + 1, 2):
                x_start = i * step
                y_start = j * step
                
                # 벡터 성분 계산 (단순화)
                if "x" in equations and "y" in equations:
                    vector_expr = {
                        "id": f"{graph_id}_vector_{i}_{j}",
                        "latex": f"({x_start},{y_start})+0.5({equations['x']},{equations['y']})",
                        "color": style.get("color", "#388c46") if style else "#388c46",
                        "lineWidth": 2,
                        "lineStyle": "SOLID"
                    }
                    expressions.append(vector_expr)
        
        return expressions

# =============================================================================
# 12. 기하학 및 변환 도구들
# =============================================================================

class CreateGeometryTool(DesmosToolBase):
    """기하학적 객체 생성 도구"""
    
    def __init__(self):
        super().__init__(
            name="create_geometry",
            description="기하학적 도형과 변환을 생성합니다",
            schema={
                "type": "object",
                "required": ["calculator_id", "geometry_type"],
                "properties": {
                    "calculator_id": {"type": "string"},
                    "geometry_type": {
                        "type": "string",
                        "enum": ["circle", "ellipse", "polygon", "line", "transformation", "conic_section"]
                    },
                    "properties": {
                        "type": "object",
                        "description": "도형별 속성들"
                    },
                    "transformation": {
                        "type": "object",
                        "properties": {
                            "type": {"type": "string", "enum": ["rotation", "translation", "scaling", "reflection"]},
                            "parameters": {"type": "object"}
                        }
                    }
                }
            }
        )
        self.calculator_manager = DesmosCalculatorManager()
    
    async def execute(self, calculator_id: str, geometry_type: str,
                     properties: Dict[str, Any] = None, transformation: Dict[str, Any] = None) -> Dict[str, Any]:
        try:
            if calculator_id not in self.calculator_manager.calculators:
                return {"success": False, "error": f"계산기 '{calculator_id}'를 찾을 수 없습니다"}
            
            geom_id = f"geom_{geometry_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
            expressions = []
            
            # 기하학적 객체 생성
            if geometry_type == "circle":
                expressions.extend(await self._create_circle(geom_id, properties))
            elif geometry_type == "ellipse":
                expressions.extend(await self._create_ellipse(geom_id, properties))
            elif geometry_type == "polygon":
                expressions.extend(await self._create_polygon(geom_id, properties))
            elif geometry_type == "line":
                expressions.extend(await self._create_line(geom_id, properties))
            elif geometry_type == "conic_section":
                expressions.extend(await self._create_conic_section(geom_id, properties))
            else:
                return {"success": False, "error": f"지원하지 않는 기하학 타입: {geometry_type}"}
            
            # 변환 적용
            if transformation:
                expressions.extend(await self._apply_transformation(geom_id, expressions, transformation))
            
            # 계산기에 추가
            calculator = self.calculator_manager.calculators[calculator_id]
            calculator["state"]["expressions"]["list"].extend(expressions)
            calculator["last_modified"] = datetime.now().isoformat()
            
            return {
                "success": True,
                "geometry_id": geom_id,
                "geometry_type": geometry_type,
                "expressions_added": len(expressions),
                "calculator_id": calculator_id,
                "message": f"{geometry_type} 기하학 객체 생성 완료",
                "javascript_code": "\n".join([
                    f"calculator_{calculator_id.replace('-', '_')}.setExpression({json.dumps(expr)});"
                    for expr in expressions
                ])
            }
            
        except Exception as e:
            logger.error(f"기하학 객체 생성 오류: {e}")
            return {"success": False, "error": str(e)}
    
    async def _create_circle(self, geom_id: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """원 생성"""
        center_x = props.get("center_x", 0)
        center_y = props.get("center_y", 0)
        radius = props.get("radius", 1)
        color = props.get("color", "#c74440")
        
        return [{
            "id": f"{geom_id}_circle",
            "latex": f"(x-{center_x})^2+(y-{center_y})^2={radius}^2",
            "color": color,
            "label": f"원 (중심: ({center_x},{center_y}), 반지름: {radius})"
        }]
    
    async def _create_ellipse(self, geom_id: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """타원 생성"""
        center_x = props.get("center_x", 0)
        center_y = props.get("center_y", 0)
        a = props.get("semi_major", 2)  # 장반축
        b = props.get("semi_minor", 1)  # 단반축
        color = props.get("color", "#2d70b3")
        
        return [{
            "id": f"{geom_id}_ellipse",
            "latex": f"\\frac{{(x-{center_x})^2}}{{{a}^2}}+\\frac{{(y-{center_y})^2}}{{{b}^2}}=1",
            "color": color,
            "label": f"타원 (중심: ({center_x},{center_y}), a={a}, b={b})"
        }]
    
    async def _create_polygon(self, geom_id: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """다각형 생성"""
        vertices = props.get("vertices", [(0,0), (1,0), (1,1), (0,1)])  # 기본값: 정사각형
        color = props.get("color", "#388c46")
        
        expressions = []
        
        # 각 변을 선분으로 생성
        for i in range(len(vertices)):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % len(vertices)]
            
            # 매개변수 선분
            expressions.append({
                "id": f"{geom_id}_edge_{i}",
                "latex": f"({x1}+t({x2}-{x1}),{y1}+t({y2}-{y1}))",
                "color": color,
                "parametricDomain": {"min": "0", "max": "1"},
                "label": f"변 {i+1}"
            })
        
        return expressions
    
    async def _create_line(self, geom_id: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """직선 생성"""
        if "slope" in props and "y_intercept" in props:
            # y = mx + b 형태
            m = props["slope"]
            b = props["y_intercept"]
            latex = f"y={m}x+{b}"
        elif "point1" in props and "point2" in props:
            # 두 점을 지나는 직선
            x1, y1 = props["point1"]
            x2, y2 = props["point2"]
            if x2 != x1:
                m = (y2 - y1) / (x2 - x1)
                b = y1 - m * x1
                latex = f"y={m}(x-{x1})+{y1}"
            else:
                latex = f"x={x1}"
        else:
            # 기본값: y = x
            latex = "y=x"
        
        color = props.get("color", "#fa7e19")
        
        return [{
            "id": f"{geom_id}_line",
            "latex": latex,
            "color": color,
            "label": "직선"
        }]
    
    async def _create_conic_section(self, geom_id: str, props: Dict[str, Any]) -> List[Dict[str, Any]]:
        """이차곡선 생성"""
        # 일반형: Ax² + Bxy + Cy² + Dx + Ey + F = 0
        A = props.get("A", 1)
        B = props.get("B", 0)
        C = props.get("C", 1)
        D = props.get("D", 0)
        E = props.get("E", 0)
        F = props.get("F", -1)
        color = props.get("color", "#9317ab")
        
        latex = f"{A}x^2+{B}xy+{C}y^2+{D}x+{E}y+{F}=0"
        
        return [{
            "id": f"{geom_id}_conic",
            "latex": latex,
            "color": color,
            "label": "이차곡선"
        }]
    
    async def _apply_transformation(self, geom_id: str, expressions: List[Dict[str, Any]], 
                                  transformation: Dict[str, Any]) -> List[Dict[str, Any]]:
        """기하학적 변환 적용"""
        trans_type = transformation.get("type")
        params = transformation.get("parameters", {})
        
        transformed_expressions = []
        
        if trans_type == "rotation":
            angle = params.get("angle", 0)  # 라디안
            center_x = params.get("center_x", 0)
            center_y = params.get("center_y", 0)
            
            # 회전 변환 행렬 적용
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            
            transformed_expressions.append({
                "id": f"{geom_id}_rotation",
                "latex": f"\\theta={angle}",
                "slider": {"hardMin": 0, "hardMax": 2*math.pi, "step": 0.1},
                "label": "회전각"
            })
        
        elif trans_type == "translation":
            dx = params.get("dx", 0)
            dy = params.get("dy", 0)
            
            transformed_expressions.append({
                "id": f"{geom_id}_translation",
                "latex": f"T_x={dx}, T_y={dy}",
                "label": f"평행이동 ({dx}, {dy})"
            })
        
        return transformed_expressions