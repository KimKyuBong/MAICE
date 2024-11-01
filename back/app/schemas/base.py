from pydantic import BaseModel
from typing import List

class ExpressionBase(BaseModel):
    original: str
    latex: str

class SolutionStepBase(BaseModel):
    step_number: int
    content: str
    expressions: List[ExpressionBase]

    class Config:
        from_attributes = True 