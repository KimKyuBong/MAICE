"""
데이터 로딩 유틸리티
"""

import json
import os
from typing import List, Dict, Any

def load_questions_from_dataset(path: str, max_items: int = 2000) -> List[str]:
    """데이터셋에서 실제 학생 질문들을 로드"""
    questions: List[str] = []
    if not path or not os.path.exists(path):
        return questions
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= max_items:
                    break
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        continue
                    # 다양한 키에서 질문 텍스트 추출
                    for key in ("question", "query", "utterance", "student_question", "content", "text"):
                        val = obj.get(key)
                        if isinstance(val, str) and 5 <= len(val) <= 500:
                            questions.append(val.strip())
                            break
                except Exception:
                    continue
    except Exception:
        pass
    return questions

def load_answers_from_dataset(path: str, max_items: int = 2000) -> List[str]:
    """데이터셋에서 실제 학생 답변들을 로드"""
    answers: List[str] = []
    if not path or not os.path.exists(path):
        return answers
    try:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f):
                if idx >= max_items:
                    break
                try:
                    obj = json.loads(line)
                    if not isinstance(obj, dict):
                        continue
                    # 다양한 키에서 답변 텍스트 추출
                    for key in ("answer", "response", "reply", "student_answer", "content", "text"):
                        val = obj.get(key)
                        if isinstance(val, str) and 5 <= len(val) <= 500:
                            answers.append(val.strip())
                            break
                except Exception:
                    continue
    except Exception:
        pass
    return answers

def categorize_questions_by_topic(questions: List[str], topics: List[str]) -> Dict[str, List[str]]:
    """질문들을 주제별로 분류"""
    categorized = {topic: [] for topic in topics}
    
    for question in questions:
        for topic in topics:
            if topic.lower() in question.lower():
                categorized[topic].append(question)
                break
        else:
            # 매칭되는 주제가 없으면 첫 번째 주제에 추가
            if topics:
                categorized[topics[0]].append(question)
    
    return categorized
