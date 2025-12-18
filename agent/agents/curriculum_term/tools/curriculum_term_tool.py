"""
교과과정 용어 분석 및 검증 도구
질문을 분석하여 교과과정에 맞는 용어를 제안하고, 응답의 용어를 검증합니다.
"""

import json
import logging
import os
import re
from typing import Any, Dict, List

from ...base_agent import Tool

logger = logging.getLogger(__name__)


class CurriculumTermTool(Tool):
    """교육과정과 교과서에서 관련 내용을 검색하고 분석하는 도구"""
    
    def __init__(self):
        super().__init__(
            name="curriculum_term",
            description="교육과정과 교과서에서 관련 내용을 검색하고 분석하는 도구"
        )
        self.curriculum_corpus = None
        # 의미 확장을 위한 사전
        self._concept_relations = self._build_concept_relations()
        self._synonyms = self._build_synonyms()
        self._load_data()

    def _load_data(self):
        """데이터 로드"""
        try:
            rag_dir = os.path.join(os.path.dirname(__file__), "rag")
            db_path = os.path.join(rag_dir, "unified_corpus.db")
            
            if os.path.exists(db_path):
                self.curriculum_corpus = db_path
                logger.info("데이터베이스 로드 완료")
            else:
                logger.warning("데이터베이스를 찾을 수 없습니다.")
                
        except Exception as e:
            logger.error(f"데이터 로드 실패: {e}")
            self.curriculum_corpus = None

    async def search(self, query: str, k: int = 5) -> Dict[str, Any]:
        """교과과정과 교과서 통합 검색"""
        if not self.curriculum_corpus:
            return {"error": "데이터를 로드할 수 없습니다."}
        
        try:
            # 교과과정/교과서 검색 (의미 확장 + 점수화)
            curriculum_results = await self._search_curriculum(query, k)
            textbook_results = await self._search_textbook(query, k)
            
            return {
                "query": query,
                "curriculum_results": curriculum_results,
                "textbook_results": textbook_results,
                "total": len(curriculum_results) + len(textbook_results)
            }
            
        except Exception as e:
            logger.error(f"검색 중 오류: {e}")
            return {"error": f"검색 중 오류가 발생했습니다: {e}"}
    
    async def _search_curriculum(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """교과과정 검색 (의미 확장 + 점수화)"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.curriculum_corpus)
            cursor = conn.cursor()
            
            query_words = self._extract_words(query)
            expanded_concepts = self._expand_query_concepts(query_words)
            direct_words = set(query_words)
            expanded_only = expanded_concepts - direct_words
            # 앵커 개념(핵심 개념)이 쿼리에 포함되어 있다면 결과에도 존재하도록 요구
            anchor_candidates = {'미분', '적분', '함수', '수열', '확률', '통계', '기하', '미적분'}
            required_core = anchor_candidates.intersection(expanded_concepts)
            
            search_query = """
                SELECT id, chunk_type, title, content, keywords, 
                       grade_level, subject, topic, achievement_code
                FROM unified_chunks 
                WHERE source_type = 'curriculum' 
                AND (content LIKE ? OR title LIKE ?)
                LIMIT ?
            """
            
            all_results = []
            # 확장된 개념으로 검색 풀 확보
            per_term_limit = max(k, 5)
            for term in expanded_concepts:
                cursor.execute(search_query, [f'%{term}%', f'%{term}%', per_term_limit])
                results = cursor.fetchall()
                
                for result in results:
                    result_dict = {
                        "id": result[0],
                        "chunk_type": result[1],
                        "title": result[2],
                        "content": result[3],
                        "keywords": json.loads(result[4]) if result[4] else [],
                        "grade_level": result[5],
                        "subject": result[6],
                        "topic": result[7],
                        "achievement_code": result[8]
                    }
                    # 매칭 문장 추출
                    match_terms = set(list(direct_words) + list(required_core))
                    if not match_terms:
                        match_terms = direct_words
                    result_dict["matched_sentences"] = self._extract_matched_sentences(
                        result_dict["content"], match_terms
                    )
                    # 과목 필터: 수학이 아닌 경우 제외 (명시된 경우)
                    subj = result_dict.get("subject")
                    if subj and "수학" not in subj:
                        continue
                    # 핵심 용어 하드 필터: 쿼리에 핵심 용어가 있으면 본문에도 반드시 포함
                    full_text = f"{result_dict.get('title','')} {result_dict.get('content','')}"
                    if required_core and not any(core in full_text for core in required_core):
                        continue
                    # 점수 계산
                    score = self._calculate_relevance_score(
                        item=result_dict,
                        direct_words=direct_words,
                        expanded_only=expanded_only,
                        chunk_type_weight_map={
                            "achievement_standard": 0.6,
                            "teaching_method": 0.2,
                        },
                        required_core_terms=required_core,
                        query_words=direct_words,
                    )
                    if score < 1.0:
                        continue
                    result_dict["score"] = score
                    all_results.append(result_dict)
            
            conn.close()
            
            # 중복은 최고 점수만 유지
            id_to_best: Dict[Any, Dict[str, Any]] = {}
            for r in all_results:
                rid = r["id"]
                if rid not in id_to_best or r.get("score", 0.0) > id_to_best[rid].get("score", 0.0):
                    id_to_best[rid] = r
            ranked = sorted(id_to_best.values(), key=lambda x: x.get("score", 0.0), reverse=True)
            return ranked[:k]
            
        except Exception as e:
            logger.error(f"교과과정 검색 중 오류: {e}")
            return []
    
    async def _search_textbook(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """교과서 검색 (의미 확장 + 점수화)"""
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.curriculum_corpus)
            cursor = conn.cursor()
            
            query_words = self._extract_words(query)
            expanded_concepts = self._expand_query_concepts(query_words)
            direct_words = set(query_words)
            expanded_only = expanded_concepts - direct_words
            anchor_candidates = {'미분', '적분', '함수', '수열', '확률', '통계', '기하', '미적분'}
            required_core = anchor_candidates.intersection(expanded_concepts)
            
            search_query = """
                SELECT id, chunk_type, title, content, keywords,
                       unit_number, subunit_number, grade_level, subject, topic
                FROM unified_chunks 
                WHERE source_type = 'textbook'
                AND (
                    (content LIKE ? OR title LIKE ?)
                    OR (keywords LIKE ? OR related_concepts LIKE ?)
                )
                LIMIT ?
            """
            
            all_results = []
            per_term_limit = max(k, 5)
            for term in expanded_concepts:
                cursor.execute(search_query, [f'%{term}%', f'%{term}%', f'%{term}%', f'%{term}%', per_term_limit])
                results = cursor.fetchall()
                
                for result in results:
                    result_dict = {
                        "id": result[0],
                        "chunk_type": result[1],
                        "title": result[2],
                        "content": result[3],
                        "keywords": json.loads(result[4]) if result[4] else [],
                        "unit_number": result[5],
                        "subunit_number": result[6],
                        "grade_level": result[7],
                        "subject": result[8],
                        "topic": result[9]
                    }
                    match_terms = set(list(direct_words) + list(required_core))
                    if not match_terms:
                        match_terms = direct_words
                    result_dict["matched_sentences"] = self._extract_matched_sentences(
                        result_dict["content"], match_terms
                    )
                    # 과목 필터: 수학이 아닌 경우 제외 (명시된 경우)
                    subj = result_dict.get("subject")
                    if subj and "수학" not in subj:
                        continue
                    # 핵심 용어 하드 필터 완화 (교과서는 키워드 기반 문맥 허용)
                    full_text = f"{result_dict.get('title','')} {result_dict.get('content','')}"
                    if required_core and not any(core in full_text for core in required_core):
                        keywords_str = json.dumps(result_dict.get('keywords', []), ensure_ascii=False)
                        if not any(core in keywords_str for core in required_core):
                            continue
                    score = self._calculate_relevance_score(
                        item=result_dict,
                        direct_words=direct_words,
                        expanded_only=expanded_only,
                        chunk_type_weight_map={
                            "unit_title": 0.6,
                            "concept_explanation": 0.3,
                            "example_solution": 0.2,
                        },
                        required_core_terms=required_core,
                        query_words=direct_words,
                    )
                    if score < 1.0:
                        continue
                    result_dict["score"] = score
                    all_results.append(result_dict)
            
            conn.close()
            
            id_to_best: Dict[Any, Dict[str, Any]] = {}
            for r in all_results:
                rid = r["id"]
                if rid not in id_to_best or r.get("score", 0.0) > id_to_best[rid].get("score", 0.0):
                    id_to_best[rid] = r
            ranked = sorted(id_to_best.values(), key=lambda x: x.get("score", 0.0), reverse=True)
            return ranked[:k]
            
        except Exception as e:
            logger.error(f"교과서 검색 중 오류: {e}")
            return []
    
    def _extract_words(self, text: str) -> List[str]:
        """텍스트에서 의미있는 단어 추출"""
        words = re.findall(r'[가-힣]{2,}', text)
        
        noise_words = {
            '한다', '있다', '된다', '않다', '이다', '니다', '습니다', '합니다',
            '에서', '으로', '까지', '부터', '에게', '뿐만', '아니라', '또한', '그리고',
            '기본', '내용', '관련', '개념', '원리', '법칙'
        }
        
        meaningful_words = []
        for word in words:
            # 조사 제거를 통한 정규화 (예: 미분과 -> 미분, 적분의 -> 적분)
            base = re.sub(r'(과|와|의|을|를|에|에서|으로)$', '', word)
            candidate = base if len(base) >= 2 else word
            if candidate not in noise_words and candidate not in meaningful_words:
                meaningful_words.append(candidate)
        
        return meaningful_words[:10]

    def _extract_matched_sentences(self, text: str, terms: set, window: int = 1, max_sentences: int = 6) -> List[str]:
        """쿼리/핵심 용어가 포함된 문장과 주변 문장을 추출"""
        if not text:
            return []
        # 문장 분할 (간단한 한국어 문장 경계)
        sentences = re.split(r'(?<=[\.!?。！？])\s+|\n+', text)
        sentences = [s.strip() for s in sentences if s and s.strip()]
        matched_indices = []
        for idx, sent in enumerate(sentences):
            if any(term and term in sent for term in terms):
                matched_indices.append(idx)
        # 주변 문장 포함
        selected = []
        seen = set()
        for idx in matched_indices:
            start = max(0, idx - window)
            end = min(len(sentences), idx + window + 1)
            for j in range(start, end):
                if j not in seen:
                    seen.add(j)
                    selected.append(sentences[j])
                if len(selected) >= max_sentences:
                    break
            if len(selected) >= max_sentences:
                break
        return selected

    def _build_concept_relations(self) -> Dict[str, set]:
        """핵심 개념 간 연관 관계 사전"""
        return {
            '미분': {'미분법', '미분계수', '도함수', '접선', '변화율', '연속', '극한', '적분', '미적분'},
            '적분': {'정적분', '부정적분', '면적', '누적', '적분법', '미적분'},
            '함수': {'정의역', '치역', '공역', '그래프', '합성함수', '역함수'},
            '수열': {'등차수열', '등비수열', '일반항', '부분합', '공차', '공비'},
            '확률': {'통계', '확률분포', '기댓값', '분산'},
        }

    def _build_synonyms(self) -> Dict[str, set]:
        """동의어/유사어 사전"""
        return {
            '미분': {'도함수', '변화율'},
            '도함수': {'미분'},
            '적분': {'누적', '면적'},
            '함수': {'대응'},
            '수열': {'열'},
        }

    def _expand_query_concepts(self, query_words: List[str]) -> set:
        """쿼리 개념 확장: 연관 개념 + 동의어 포함"""
        expanded = set(query_words)
        for w in query_words:
            if w in self._concept_relations:
                expanded.update(self._concept_relations[w])
            if w in self._synonyms:
                expanded.update(self._synonyms[w])
        return expanded

    def _calculate_relevance_score(
        self,
        item: Dict[str, Any],
        direct_words: set,
        expanded_only: set,
        chunk_type_weight_map: Dict[str, float],
        required_core_terms: set,
        query_words: set,
    ) -> float:
        """관련성 점수 계산"""
        text = f"{item.get('title', '')} {item.get('content', '')}"
        # 한국어는 lower 영향 거의 없음
        direct_hits = sum(1 for w in direct_words if w and w in text)
        related_hits = sum(1 for w in expanded_only if w and w in text)
        score = direct_hits * 2.0 + related_hits * 1.0
        # chunk 타입 가중치
        weight = chunk_type_weight_map.get(item.get('chunk_type'), 0.0)
        score += weight
        # 내용 길이로 약한 보정 (짧은 노이즈 방지)
        content_len = len(item.get('content') or '')
        if content_len >= 200:
            score += 0.2
        elif content_len >= 80:
            score += 0.1
        # 쿼리에 앵커 개념이 포함되었는데 본문에 하나도 없으면 강한 패널티
        if required_core_terms:
            if not any(core in text for core in required_core_terms):
                score -= 2.0
        # '기본 정리' 문맥 보정: 미분/적분과 함께 등장 시 가산점
        if ('기본' in query_words or '정리' in query_words) and any(core in required_core_terms for core in {'미분', '적분'}):
            if ('미분' in text and '적분' in text and '정리' in text) or ('기본' in text and '정리' in text and any(core in text for core in {'미분', '적분'})):
                score += 0.5
        return score

    async def execute(self, action: str, **kwargs) -> Dict[str, Any]:
        """도구 실행"""
        try:
            if action == "search":
                query = kwargs.get("query", "")
                k = kwargs.get("k", 5)
                return await self.search(query, k)
            else:
                return {"error": f"알 수 없는 액션: {action}"}
                
        except Exception as e:
            logger.error(f"도구 실행 실패: {e}")
            return {"error": str(e)}

    async def analyze_question(self, question: str) -> Dict[str, Any]:
        """질문을 분석하여 교과과정에 맞는 용어를 제안"""
        try:
            # 질문에서 핵심 개념 추출
            core_concepts = self._extract_core_concepts(question)
            
            # 각 개념에 대해 교과과정 검색
            suggested_terms = []
            concept_level = "고등학교 1학년"  # 기본값
            avoid_terms = []
            achievement_standards = []
            teaching_notes = []
            textbook_examples = []
            
            for concept in core_concepts:
                search_result = await self.search(concept, k=5)
                
                if "error" not in search_result:
                    # 교과과정 결과에서 적절한 용어와 성취기준 추출
                    curriculum_data = self._extract_curriculum_data(search_result.get("curriculum_results", []))
                    suggested_terms.extend(curriculum_data.get("terms", []))
                    achievement_standards.extend(curriculum_data.get("achievement_standards", []))
                    teaching_notes.extend(curriculum_data.get("teaching_notes", []))
                    
                    # 교과서 결과에서 개념 수준과 예시 추출
                    textbook_data = self._extract_textbook_data(search_result.get("textbook_results", []))
                    if textbook_data.get("level"):
                        concept_level = textbook_data["level"]
                    textbook_examples.extend(textbook_data.get("examples", []))
                
                # 고급/전문 용어 식별 (실제 교과과정 데이터 기반)
                advanced_terms = await self._identify_advanced_terms_dynamically(concept)
                if advanced_terms:
                    avoid_terms.extend(advanced_terms)
            
            # 중복 제거 및 정렬
            suggested_terms = list(set(suggested_terms))[:15]
            avoid_terms = list(set(avoid_terms))[:8]
            achievement_standards = list(set(achievement_standards))[:5]
            teaching_notes = list(set(teaching_notes))[:5]
            textbook_examples = list(set(textbook_examples))[:5]
            
            return {
                "success": True,
                "suggested_terms": suggested_terms,
                "concept_level": concept_level,
                "avoid_terms": avoid_terms,
                "achievement_standards": achievement_standards,
                "teaching_notes": teaching_notes,
                "textbook_examples": textbook_examples,
                "analysis": f"질문에서 {len(core_concepts)}개 핵심 개념을 식별했습니다.",
                "recommendations": self._generate_recommendations_with_context(
                    suggested_terms, concept_level, achievement_standards, teaching_notes, textbook_examples
                )
            }
            
        except Exception as e:
            logger.error(f"질문 분석 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def verify_terms(self, content: str) -> Dict[str, Any]:
        """응답 내용의 용어를 검증하고 교과과정에 맞게 수정 제안"""
        try:
            # 내용에서 수학 용어 추출
            math_terms = self._extract_math_terms(content)
            
            violations = []
            suggestions = []
            corrected_text = content
            
            for term in math_terms:
                # 용어가 교과과정에 적합한지 검증
                verification_result = await self._verify_single_term(term)
                
                if not verification_result["is_appropriate"]:
                    violations.append({
                        "term": term,
                        "issue": verification_result["issue"],
                        "suggestion": verification_result["suggestion"]
                    })
                    
                    # 수정 제안
                    if verification_result["suggestion"]:
                        corrected_text = corrected_text.replace(term, verification_result["suggestion"])
                        suggestions.append({
                            "original": term,
                            "replacement": verification_result["suggestion"],
                            "reason": verification_result["issue"]
                        })
            
            return {
                "success": True,
                "violations": violations,
                "suggestions": suggestions,
                "corrected_text": corrected_text,
                "total_terms_checked": len(math_terms)
            }
            
        except Exception as e:
            logger.error(f"용어 검증 오류: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _extract_core_concepts(self, question: str) -> List[str]:
        """질문에서 핵심 수학 개념 추출"""
        # 수학 관련 키워드 패턴
        math_patterns = [
            r'미분|적분|함수|수열|확률|통계|기하|삼각함수|지수함수|로그함수',
            r'방정식|부등식|집합|명제|벡터|행렬',
            r'극한|연속|도함수|정적분|부정적분',
            r'등차수열|등비수열|수학적 귀납법',
            r'사인법칙|코사인법칙|삼각형|원|포물선|타원|쌍곡선'
        ]
        
        concepts = []
        for pattern in math_patterns:
            matches = re.findall(pattern, question)
            concepts.extend(matches)
        
        return list(set(concepts))
    
    def _extract_curriculum_data(self, curriculum_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """교과과정 결과에서 적절한 용어와 성취기준, 유의사항, 예시 추출"""
        terms = []
        achievement_standards = []
        teaching_notes = []
        textbook_examples = []
        
        for result in curriculum_results:
            # 결과가 튜플인 경우 (직접 SQL 결과)
            if isinstance(result, tuple):
                if len(result) >= 4:
                    title = result[2] or ""
                    content = result[3] or ""
                    
                    # 성취기준에서 핵심 용어 추출
                    if "성취기준" in title or "성취기준" in content:
                        # 콜론 뒤의 핵심 내용에서 용어 추출
                        if ":" in content:
                            core_content = content.split(":")[-1]
                            # 쉼표나 마침표로 구분된 용어들
                            content_terms = re.findall(r'[가-힣]+', core_content)
                            terms.extend(content_terms[:3])  # 상위 3개만
                        
                        # 성취기준을 간결하게 정리
                        clean_content = self._clean_achievement_standard(content)
                        if clean_content:
                            achievement_standards.append(clean_content)
                    
                    # 키워드에서 용어 추출
                    if len(result) > 4 and result[4]:
                        try:
                            keywords = json.loads(result[4]) if isinstance(result[4], str) else result[4]
                            if isinstance(keywords, list):
                                terms.extend(keywords[:5])
                        except:
                            pass
                    
                    # 유의사항 추출 (teaching_method에서)
                    if "유의사항" in content or "주의" in content or "경고" in content:
                        clean_note = self._clean_teaching_note(content)
                        if clean_note:
                            teaching_notes.append(clean_note)
                    
                    # 예시 추출
                    if "예시" in content or "예제" in content or "문제" in content:
                        clean_example = self._clean_example(content)
                        if clean_example:
                            textbook_examples.append(clean_example)
            
            # 결과가 딕셔너리인 경우 (처리된 결과)
            elif isinstance(result, dict):
                title = result.get("title", "")
                content = result.get("content", "")
                keywords = result.get("keywords", [])
                
                # 성취기준에서 핵심 용어 추출
                if "성취기준" in title or "성취기준" in content:
                    if ":" in content:
                        core_content = content.split(":")[-1]
                        content_terms = re.findall(r'[가-힣]+', core_content)
                        terms.extend(content_terms[:3])
                    
                    # 성취기준을 간결하게 정리
                    clean_content = self._clean_achievement_standard(content)
                    if clean_content:
                        achievement_standards.append(clean_content)
                
                # 키워드에서 용어 추출
                if keywords:
                    if isinstance(keywords, list):
                        terms.extend(keywords[:5])
                    elif isinstance(keywords, str):
                        try:
                            parsed_keywords = json.loads(keywords)
                            if isinstance(parsed_keywords, list):
                                terms.extend(parsed_keywords[:5])
                        except:
                            pass
                
                # 유의사항 추출
                if "유의사항" in content or "주의" in content or "경고" in content:
                    clean_note = self._clean_teaching_note(content)
                    if clean_note:
                        teaching_notes.append(clean_note)
                
                # 예시 추출
                if "예시" in content or "예제" in content or "문제" in content:
                    clean_example = self._clean_example(content)
                    if clean_example:
                        textbook_examples.append(clean_example)
        
        # 중복 제거 및 필터링
        filtered_terms = []
        for term in terms:
            if len(term) >= 2 and term not in filtered_terms:
                filtered_terms.append(term)
            
            return {
            "terms": filtered_terms[:10],
            "achievement_standards": achievement_standards[:3],
            "teaching_notes": teaching_notes[:3],
            "textbook_examples": textbook_examples[:3]
        }
    
    def _clean_achievement_standard(self, content: str) -> str:
        """성취기준 내용을 간결하게 정리"""
        if not content:
            return ""
        
        # 불필요한 공백과 줄바꿈 제거
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 성취기준 코드 패턴 찾기 (예: [2수01-01], [3수01-01] 등)
        achievement_code = ""
        code_pattern = r'\[([가-힣]+\d+-\d+)\]'
        code_match = re.search(code_pattern, content)
        if code_match:
            achievement_code = code_match.group(1)
            # 코드 이후의 내용만 추출
            code_end = content.find(']') + 1
            content = content[code_end:].strip()
        
        # 성취기준 번호가 있으면 앞에 붙이기
        if achievement_code:
            prefix = f"성취기준 [{achievement_code}]: "
        else:
            # 코드가 없으면 일반적인 성취기준 형식 사용
            prefix = "성취기준: "
        
        # 너무 긴 내용은 핵심 부분만 추출
        if len(content) > 100:
            # 핵심 키워드가 포함된 문장 찾기
            sentences = re.split(r'[.!?。！？]', content)
            for sentence in sentences:
                if any(keyword in sentence for keyword in ['함수', '수열', '미분', '적분', '확률', '통계', '기하', '방정식', '도형', '측정']):
                    if len(sentence.strip()) > 20:
                        return prefix + sentence.strip()[:80] + "..."
            
            # 첫 번째 문장 사용
            return prefix + content[:80] + "..."
        
        return prefix + content
    
    def _clean_teaching_note(self, content: str) -> str:
        """유의사항 내용을 간결하게 정리"""
        if not content:
            return ""
        
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 핵심 내용만 추출
        if len(content) > 100:
            # 유의사항 키워드 주변 내용
            for keyword in ['유의사항', '주의', '경고']:
                if keyword in content:
                    start = content.find(keyword)
                    end = min(start + 100, len(content))
                    return content[start:end] + "..."
            
            return content[:100] + "..."
        
        return content
    
    def _clean_example(self, content: str) -> str:
        """예시 내용을 간결하게 정리"""
        if not content:
            return ""
        
        content = re.sub(r'\s+', ' ', content.strip())
        
        # 예시 키워드 주변 내용만 추출
        for keyword in ['예시', '예제', '문제']:
            if keyword in content:
                start = content.find(keyword)
                end = min(start + 80, len(content))
                return content[start:end] + "..."
        
        # 너무 긴 내용은 자르기
        if len(content) > 80:
            return content[:80] + "..."
        
        return content
    
    def _extract_textbook_data(self, textbook_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """교과서 결과에서 개념 수준과 예시 추출"""
        level = "고등학교 1학년"
        examples = []
        
        for result in textbook_results:
            if isinstance(result, tuple) and len(result) > 1:
                chunk_type = result[1]
                content = result[3] if len(result) > 3 else ""
                
                # chunk_type에 따른 수준 판단
                if chunk_type == "concept_explanation":
                    level = "고등학교 2-3학년"  # 개념 설명은 고급 수준
                elif chunk_type == "unit_title":
                    # 단원 제목에서 학년 정보 추출
                    if content:
                        if "미적분" in content or "기하" in content:
                            level = "고등학교 3학년"
                        elif "함수" in content or "수열" in content or "확률" in content:
                            level = "고등학교 2학년"
                        elif "방정식" in content or "도형" in content:
                            level = "고등학교 1학년"
                
                # 교과서 예시 추출 (간결하게)
                if content and len(content) > 20:  # 너무 짧은 내용은 제외
                    clean_example = self._clean_textbook_example(content, chunk_type)
                    if clean_example:
                        examples.append(clean_example)
            
            elif isinstance(result, dict):
                chunk_type = result.get("chunk_type", "")
                content = result.get("content", "")
                
                # chunk_type에 따른 수준 판단
                if chunk_type == "concept_explanation":
                    level = "고등학교 2-3학년"
                elif chunk_type == "unit_title":
                    if content:
                        if "미적분" in content or "기하" in content:
                            level = "고등학교 3학년"
                        elif "함수" in content or "수열" in content or "확률" in content:
                            level = "고등학교 2학년"
                        elif "방정식" in content or "도형" in content:
                            level = "고등학교 1학년"
                
                # 교과서 예시 추출 (간결하게)
                if content and len(content) > 20:
                    clean_example = self._clean_textbook_example(content, chunk_type)
                    if clean_example:
                        examples.append(clean_example)
            
            return {
            "level": level,
            "examples": examples[:3]  # 최대 3개 예시
        }
    
    def _clean_textbook_example(self, content: str, chunk_type: str) -> str:
        """교과서 예시 내용을 간결하게 정리"""
        if not content:
            return ""
        
        content = re.sub(r'\s+', ' ', content.strip())
        
        # chunk_type에 따른 처리
        if chunk_type == "example_solution":
            # 문제 풀이 예시는 핵심만 추출
            if len(content) > 100:
                # 문제와 답안 부분 찾기
                for keyword in ['문제', '풀이', '답안', '해답']:
                    if keyword in content:
                        start = content.find(keyword)
                        end = min(start + 100, len(content))
                        return content[start:end] + "..."
                return content[:100] + "..."
        
        elif chunk_type == "concept_explanation":
            # 개념 설명은 핵심 문장만 추출
            if len(content) > 120:
                sentences = re.split(r'[.!?。！？]', content)
                for sentence in sentences:
                    if any(keyword in sentence for keyword in ['함수', '수열', '미분', '적분', '확률', '통계', '기하', '방정식']):
                        if len(sentence.strip()) > 30:
                            return sentence.strip()[:120] + "..."
                return content[:120] + "..."
        
        # 일반적인 경우
        if len(content) > 80:
            return content[:80] + "..."
        
        return content
    
    async def _identify_advanced_terms_dynamically(self, concept: str) -> List[str]:
        """고급/전문 용어 식별 (실제 교과과정 데이터 기반)"""
        advanced_terms = []
        
        try:
            import sqlite3
            
            conn = sqlite3.connect(self.curriculum_corpus)
            cursor = conn.cursor()
            
            # 1. 교과과정에서 해당 개념의 수준 확인
            level_query = """
                SELECT chunk_type, content, keywords
                FROM unified_chunks
                WHERE source_type = 'curriculum'
                AND (content LIKE ? OR title LIKE ? OR keywords LIKE ?)
                LIMIT 10
            """
            cursor.execute(level_query, [f'%{concept}%', f'%{concept}%', f'%{concept}%'])
            curriculum_results = cursor.fetchall()
            
            # 2. 교과서에서 해당 개념의 수준 확인
            textbook_query = """
                SELECT chunk_type, content, keywords, unit_number
                FROM unified_chunks
                WHERE source_type = 'textbook'
                AND (content LIKE ? OR title LIKE ? OR keywords LIKE ?)
                LIMIT 10
            """
            cursor.execute(textbook_query, [f'%{concept}%', f'%{concept}%', f'%{concept}%'])
            textbook_results = cursor.fetchall()
            
            # 3. 고급 개념 판단 기준
            advanced_indicators = {
                'chunk_type': ['concept_explanation', 'advanced_concept'],
                'content_keywords': ['고급', '심화', '전문', '대학', '연구', '이론'],
                'unit_patterns': ['3학년', '고급', '심화', '선택']
            }
            
            # 교과과정 결과 분석
            for result in curriculum_results:
                chunk_type = result[0] if len(result) > 0 else ""
                content = result[1] if len(result) > 1 else ""
                keywords = result[2] if len(result) > 2 else ""
                
                # 고급 지표 확인
                if any(indicator in content for indicator in advanced_indicators['content_keywords']):
                    advanced_terms.append(concept)
                    break
                
                # 키워드에서 고급 지표 확인
                if keywords:
                    try:
                        parsed_keywords = json.loads(keywords) if isinstance(keywords, str) else keywords
                        if isinstance(parsed_keywords, list):
                            for keyword in parsed_keywords:
                                if any(indicator in str(keyword) for indicator in advanced_indicators['content_keywords']):
                                    advanced_terms.append(concept)
                                    break
                    except:
                        pass
            
            # 교과서 결과 분석
            for result in textbook_results:
                chunk_type = result[0] if len(result) > 0 else ""
                content = result[1] if len(result) > 1 else ""
                unit_number = result[3] if len(result) > 3 else ""
                
                # chunk_type이 concept_explanation이면 고급 개념 가능성
                if chunk_type in advanced_indicators['chunk_type']:
                    # 단원 번호가 높으면 고급 개념
                    if unit_number and str(unit_number).isdigit():
                        if int(unit_number) > 5:  # 단원 번호가 5보다 크면 고급
                            advanced_terms.append(concept)
                            break
                
                # 내용에서 고급 지표 확인
                if any(indicator in content for indicator in advanced_indicators['content_keywords']):
                    advanced_terms.append(concept)
                    break
            
            # 4. 개념 관계에서 고급 개념 확인
            if concept in self._concept_relations:
                related_concepts = self._concept_relations[concept]
                # 관련 개념 중 고급 개념이 있으면 본 개념도 고급
                for related in related_concepts:
                    if any(advanced in related for advanced in ['미분', '적분', '미적분', '기하', '확률', '통계']):
                        advanced_terms.append(concept)
                        break
            
            conn.close()
            
        except Exception as e:
            logger.error(f"고급 용어 식별 중 오류: {e}")
        
        return list(set(advanced_terms))
    
    def _generate_recommendations_with_context(self, suggested_terms: List[str], concept_level: str, achievement_standards: List[str], teaching_notes: List[str], textbook_examples: List[str]) -> List[str]:
        """용어 사용 권장사항 생성 (컨텍스트 포함)"""
        recommendations = []
        
        if suggested_terms:
            recommendations.append(f"제안된 용어: {', '.join(suggested_terms[:5])}")
        else:
            recommendations.append("제안된 용어가 없습니다. 기본 용어를 사용하세요.")
        
        recommendations.append(f"적정 수준: {concept_level}")
        recommendations.append("용어 사용 시 주의사항:")
        recommendations.append("- 학생이 이해할 수 있는 수준으로 설명")
        recommendations.append("- 교과서에서 사용하는 표준 용어 우선 사용")
        recommendations.append("- 복잡한 개념은 단계별로 분해하여 설명")
        
        # 성취기준 추가
        if achievement_standards:
            recommendations.append("")
            recommendations.append("📚 성취기준:")
            for i, std in enumerate(achievement_standards[:3], 1):
                # 너무 긴 내용은 잘라서 표시
                content = std[:200] + "..." if len(std) > 200 else std
                recommendations.append(f"{i}. {content}")
        
        # 유의사항 추가
        if teaching_notes:
            recommendations.append("")
            recommendations.append("⚠️ 유의사항:")
            for i, note in enumerate(teaching_notes[:3], 1):
                content = note[:150] + "..." if len(note) > 150 else note
                recommendations.append(f"{i}. {content}")
        
        # 교과서 예시 추가
        if textbook_examples:
            recommendations.append("")
            recommendations.append("📖 교과서 예시:")
            for i, example in enumerate(textbook_examples[:3], 1):
                content = example[:180] + "..." if len(example) > 180 else example
                recommendations.append(f"{i}. {content}")
        
        return recommendations
    
    def _extract_math_terms(self, content: str) -> List[str]:
        """내용에서 수학 용어 추출"""
        # 수학 용어 패턴 (더 포괄적으로)
        math_terms = re.findall(r'[가-힣]+(?:함수|수열|확률|통계|기하|미분|적분|방정식|부등식|집합|명제|벡터|행렬|극한|연속|도함수|정적분|부정적분|등차수열|등비수열|귀납법|사인법칙|코사인법칙|삼각형|원|포물선|타원|쌍곡선)', content)
        
        # 기본 수학 용어도 포함
        basic_terms = re.findall(r'\b(?:함수|수열|확률|통계|기하|미분|적분|방정식|부등식|집합|명제|벡터|행렬|극한|연속|도함수|정적분|부정적분|등차수열|등비수열|귀납법|사인법칙|코사인법칙|삼각형|원|포물선|타원|쌍곡선)\b', content)
        
        # 고급 용어도 포함
        advanced_terms = re.findall(r'\b(?:도함수|정적분|부정적분|합성함수|역함수|일대일함수|점화식|무한급수|조건부확률|베이즈 정리|확률분포|표본분산|신뢰구간|가설검정)\b', content)
        
        all_terms = math_terms + basic_terms + advanced_terms
        return list(set(all_terms))
    
    async def _verify_single_term(self, term: str) -> Dict[str, Any]:
        """단일 용어 검증"""
        try:
            # 용어 검색으로 교과과정 적합성 확인
            search_result = await self.search(term, k=2)
            
            if "error" in search_result:
                return {
                    "is_appropriate": False,
                    "issue": "용어 검증을 수행할 수 없습니다.",
                    "suggestion": term
                }
            
            # 교과과정 결과가 있으면 적절한 용어
            curriculum_count = len(search_result.get("curriculum_results", []))
            textbook_count = len(search_result.get("textbook_results", []))
            
            # 고급 용어 목록 확인
            advanced_terms = []
            for concept, terms in {
                "미분": ["도함수", "미분계수", "연쇄법칙", "편미분", "전미분"],
                "적분": ["정적분", "부정적분", "치환적분", "부분적분", "이중적분", "삼중적분"],
                "함수": ["합성함수", "역함수", "일대일함수", "전사함수", "단사함수"],
                "수열": ["점화식", "수학적 귀납법", "무한급수", "급수의 수렴", "급수의 발산"],
                "확률": ["조건부확률", "베이즈 정리", "확률분포", "기댓값", "분산", "표준편차"],
                "통계": ["표본분산", "신뢰구간", "가설검정", "회귀분석", "상관분석"]
            }.items():
                if term in terms:
                    advanced_terms.append(concept)
            
            # 고급 용어이면서 교과과정에 없는 경우 부적절
            if advanced_terms and curriculum_count == 0:
                alternative = self._suggest_alternative_term(term)
                return {
                    "is_appropriate": False,
                    "issue": f"고급 용어입니다. {', '.join(advanced_terms)} 수준에서 다루어집니다.",
                    "suggestion": alternative
                }
            
            if curriculum_count > 0 or textbook_count > 0:
                return {
                    "is_appropriate": True,
                    "issue": None,
                    "suggestion": term
                }
            else:
                # 대안 용어 제안
                alternative = self._suggest_alternative_term(term)
                return {
                    "is_appropriate": False,
                    "issue": "교과과정에서 찾을 수 없는 용어입니다.",
                    "suggestion": alternative
                }
                
        except Exception as e:
            logger.error(f"단일 용어 검증 오류: {e}")
            return {
                "is_appropriate": False,
                "issue": f"검증 중 오류 발생: {e}",
                "suggestion": term
            }
    
    def _suggest_alternative_term(self, term: str) -> str:
        """대안 용어 제안"""
        alternatives = {
            "도함수": "미분계수",
            "정적분": "적분",
            "부정적분": "적분",
            "합성함수": "함수",
            "역함수": "함수",
            "일대일함수": "함수",
            "점화식": "수열",
            "무한급수": "수열의 합",
            "조건부확률": "확률",
            "베이즈 정리": "확률",
            "확률분포": "확률",
            "표본분산": "분산",
            "신뢰구간": "통계",
            "가설검정": "통계",
            "편미분": "미분",
            "전미분": "미분",
            "치환적분": "적분",
            "부분적분": "적분",
            "이중적분": "적분",
            "삼중적분": "적분",
            "전사함수": "함수",
            "단사함수": "함수",
            "급수의 수렴": "수열",
            "급수의 발산": "수열",
            "기댓값": "평균",
            "분산": "분산",
            "표준편차": "표준편차",
            "회귀분석": "통계",
            "상관분석": "통계",
            "역삼각함수": "삼각함수",
            "쌍곡선함수": "삼각함수",
            "복소삼각함수": "삼각함수"
        }
        
        return alternatives.get(term, term)
