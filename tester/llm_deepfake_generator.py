#!/usr/bin/env python3
"""
LLM 기반 딥페이크식 학생 질문 생성기
실제 학생들이 GPT에 질문한 형태를 LLM이 학습해서 비슷한 문체와 패턴으로 새로운 질문을 생성
"""

import json
import os
import random
import re
import asyncio
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging
from datetime import datetime

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. pip install python-dotenv를 실행하세요.")
    print("환경변수를 직접 설정하거나 .env 파일을 사용할 수 없습니다.")

# OpenAI 클라이언트
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai를 사용할 수 없습니다. 'pip install openai'를 실행하세요.")

# 로깅 설정
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('llm_deepfake_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class LLMDeepfakeGenerator:
    """LLM을 활용한 딥페이크식 학생 질문 생성기"""
    
    def __init__(self, openai_api_key: str = None, model: str = None, data_path: str = None):
        self.openai_client = None
        self.model = model or os.getenv('OPENAI_MODEL', 'gpt-4')
        self.data_path = data_path or os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
        self.real_questions = []
        self.student_profiles = []
        self.style_analysis = {}
        
        # OpenAI 클라이언트 초기화
        if OPENAI_AVAILABLE:
            api_key = openai_api_key or os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logging.info(f"✅ OpenAI 클라이언트 초기화 완료 (모델: {self.model})")
            else:
                logging.warning("❌ OpenAI API 키가 설정되지 않았습니다")
                logging.warning("환경변수 OPENAI_API_KEY를 설정하거나 .env 파일을 사용하세요")
        else:
            logging.warning("❌ OpenAI 패키지가 설치되지 않았습니다")
        
        # 실제 데이터 로드
        self.load_real_data()
        self.analyze_student_styles()
    
    def load_real_data(self):
        """실제 학생 질문 데이터 로드"""
        try:
            # .env에서 설정된 경로 우선 사용
            possible_paths = [
                self.data_path,
                'data/evaluation_statistics.json',
                'tester/data/evaluation_statistics.json',
                '../data/evaluation_statistics.json'
            ]
            
            data = None
            for path in possible_paths:
                if os.path.exists(path):
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    logging.info(f"✅ 데이터 파일 로드 성공: {path}")
                    break
            
            if not data:
                logging.warning("❌ 데이터 파일을 찾을 수 없습니다")
                logging.warning(f"시도한 경로들: {possible_paths}")
                return
            
            # 질문별_교사_평가에서 질문 추출
            if '질문별_교사_평가' in data:
                max_questions = int(os.getenv('MAX_QUESTIONS', 1000))
                question_count = 0
                
                for question_id, question_data in data['질문별_교사_평가'].items():
                    if question_count >= max_questions:
                        break
                        
                    if isinstance(question_data, dict) and '질문_원문' in question_data:
                        question_text = question_data['질문_원문']
                        if isinstance(question_text, str) and 5 <= len(question_text) <= 500:
                            self.real_questions.append(question_text)
                            question_count += 1
            
            logging.info(f"로드된 실제 질문 수: {len(self.real_questions)} (최대: {max_questions})")
            
        except Exception as e:
            logging.error(f"실제 데이터 로드 실패: {e}")
            logging.error("데이터 파일 경로와 형식을 확인하세요")
    
    def analyze_student_styles(self):
        """학생들의 문체 스타일 분석"""
        if not self.real_questions:
            return
        
        # 문체 패턴 분석
        for question in self.real_questions:
            style_info = self._extract_style_features(question)
            self.style_analysis[question] = style_info
        
        logging.info(f"스타일 분석 완료: {len(self.style_analysis)}개 질문")
    
    def _extract_style_features(self, question: str) -> Dict[str, any]:
        """질문에서 스타일 특징 추출"""
        features = {
            'formality': self._analyze_formality(question),
            'emotion': self._analyze_emotion(question),
            'urgency': self._analyze_urgency(question),
            'uncertainty': self._analyze_uncertainty(question),
            'length': len(question),
            'has_emoji': bool(re.search(r'[😀-🙏🌀-🗿]', question)),
            'has_ellipsis': bool(re.search(r'\.{2,}', question)),
            'has_exclamation': bool(re.search(r'[아|어|오|우|으|이]+\!+', question)),
            'sentence_endings': self._analyze_sentence_endings(question),
            'vocabulary_level': self._analyze_vocabulary_level(question)
        }
        return features
    
    def _analyze_formality(self, text: str) -> str:
        """존댓말/반말 분석"""
        formal_count = len(re.findall(r'[요|니다|습니다|니다]', text))
        informal_count = len(re.findall(r'[야|어|아|지]', text))
        
        if formal_count > informal_count:
            return 'formal'
        elif informal_count > formal_count:
            return 'informal'
        else:
            return 'mixed'
    
    def _analyze_emotion(self, text: str) -> str:
        """감정 상태 분석"""
        emotion_keywords = {
            'frustrated': ['짜증', '답답', '화나', '열받', '스트레스'],
            'anxious': ['불안', '걱정', '두려', '긴장', '떨려'],
            'confused': ['헷갈려', '모르겠어', '어려워', '복잡해'],
            'excited': ['재밌어', '신나', '흥미로워', '궁금해'],
            'desperate': ['급해', '빨리', '당장', '바로', '시험'],
            'neutral': []
        }
        
        for emotion, keywords in emotion_keywords.items():
            if any(keyword in text for keyword in keywords):
                return emotion
        
        return 'neutral'
    
    def _analyze_urgency(self, text: str) -> int:
        """긴급함 수준 분석 (0-5)"""
        urgency_words = ['급해', '빨리', '시험', '내일', '오늘', '당장', '바로', '마감']
        urgency_score = sum(1 for word in urgency_words if word in text)
        return min(urgency_score, 5)
    
    def _analyze_uncertainty(self, text: str) -> int:
        """불확실함 수준 분석 (0-5)"""
        uncertainty_words = ['같은데', '같은', '것 같은', '모르겠어', '잘 모르겠어', '아마', '혹시', '아직']
        uncertainty_score = sum(1 for word in uncertainty_words if word in text)
        return min(uncertainty_score, 5)
    
    def _analyze_sentence_endings(self, text: str) -> List[str]:
        """문장 끝 표현 분석"""
        endings = []
        if '?' in text:
            endings.append('question')
        if re.search(r'[요|니다|습니다]', text):
            endings.append('formal')
        if re.search(r'[야|어|아|지]', text):
            endings.append('informal')
        if re.search(r'\.{2,}', text):
            endings.append('ellipsis')
        if re.search(r'\!+', text):
            endings.append('exclamation')
        
        return endings
    
    def _analyze_vocabulary_level(self, text: str) -> str:
        """어휘 수준 분석"""
        advanced_terms = ['수학적귀납법', '점화식', '일반항', '공차', '공비', '시그마', 'Σ']
        intermediate_terms = ['수열', '등차수열', '등비수열', '합계', '항']
        basic_terms = ['더하기', '빼기', '곱하기', '나누기', '계산']
        
        advanced_count = sum(1 for term in advanced_terms if term in text)
        intermediate_count = sum(1 for term in intermediate_terms if term in text)
        basic_count = sum(1 for term in basic_terms if term in text)
        
        if advanced_count > 0:
            return 'advanced'
        elif intermediate_count > 0:
            return 'intermediate'
        elif basic_count > 0:
            return 'basic'
        else:
            return 'unknown'
    
    async def generate_llm_deepfake_question(self, 
                                           target_topic: str,
                                           style_profile: str = None,
                                           difficulty: str = 'intermediate',
                                           emotion: str = None) -> str:
        """LLM을 활용한 딥페이크 질문 생성"""
        if not self.openai_client:
            return "OpenAI 클라이언트가 초기화되지 않았습니다. API 키를 확인하세요."
        
        # 스타일 프로필 선택
        if style_profile and style_profile in self.style_analysis:
            selected_style = style_profile
        else:
            # 랜덤하게 스타일 선택
            available_styles = list(self.style_analysis.keys())
            if available_styles:
                selected_style = random.choice(available_styles)
            else:
                return "분석된 스타일이 없습니다."
        
        style_features = self.style_analysis[selected_style]
        
        # 프롬프트 생성
        prompt = self._create_llm_prompt(target_topic, style_features, difficulty, emotion)
        
        # 디버깅: 프롬프트 내용 로깅
        logging.info(f"생성된 프롬프트 길이: {len(prompt)}")
        logging.info(f"프롬프트 미리보기: {prompt[:200]}...")
        
        try:
            # GPT-5-mini 모델은 max_completion_tokens를 사용하고 temperature는 기본값만 지원
            if 'gpt-5' in self.model:
                logging.info(f"GPT-5 모델 사용: {self.model}")
                
                # GPT-5-mini 모델 파라미터 조정
                request_params = {
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "당신은 한국 고등학생들의 수학 질문 스타일을 정확하게 모방하는 AI입니다. 주어진 스타일 가이드에 따라 자연스럽고 현실적인 학생 질문을 생성해주세요."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "max_completion_tokens": 1000  # 더 큰 값으로 조정
                }
                
                logging.info(f"요청 파라미터: {request_params}")
                
                response = await self.openai_client.chat.completions.create(**request_params)
                
                # 디버깅: 전체 응답 구조 확인
                logging.info(f"응답 구조: {response}")
                logging.info(f"응답 choices: {response.choices}")
                
            else:
                # 기존 모델들은 max_tokens와 temperature 사용
                logging.info(f"기존 모델 사용: {self.model}")
                response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "당신은 한국 고등학생들의 수학 질문 스타일을 정확하게 모방하는 AI입니다. 주어진 스타일 가이드에 따라 자연스럽고 현실적인 학생 질문을 생성해주세요."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.8,
                    max_tokens=200
                )
            
            # 디버깅: API 응답 로깅
            if response.choices and len(response.choices) > 0:
                content = response.choices[0].message.content
                logging.info(f"API 응답 성공: '{content}' (길이: {len(content) if content else 0})")
                
                if content and content.strip():
                    generated_question = content.strip()
                    
                    # 생성된 질문의 품질 검증
                    if self._validate_generated_question(generated_question, style_features):
                        logging.info(f"LLM 생성 성공: {generated_question}")
                        return generated_question
                    else:
                        logging.warning(f"LLM 생성 실패, 폴백 사용: {generated_question}")
                        # 검증 실패 시 기본 템플릿 기반 생성
                        return self._fallback_generation(target_topic, style_features, difficulty)
                else:
                    logging.error("API 응답 내용이 비어있음")
                    return self._fallback_generation(target_topic, style_features, difficulty)
            else:
                logging.error("API 응답에 choices가 없음")
                return self._fallback_generation(target_topic, style_features, difficulty)
                
        except Exception as e:
            logging.error(f"LLM 질문 생성 실패: {e}")
            return self._fallback_generation(target_topic, style_features, difficulty)
    
    def _create_llm_prompt(self, target_topic: str, style_features: Dict, difficulty: str, emotion: str = None) -> str:
        """LLM 프롬프트 생성"""
        
        # 실제 학생 질문 예시들을 스타일에 맞게 선택
        style_examples = self._get_style_examples(style_features)
        
        # 스타일 가이드 생성
        style_guide = self._generate_style_guide(style_features)
        
        # 난이도 가이드
        difficulty_guide = {
            'naive': '기본 개념에 대한 간단한 질문',
            'basic': '기초적인 이해를 위한 질문',
            'intermediate': '일반적인 수준의 질문',
            'advanced': '심화 내용에 대한 질문',
            'olympiad': '올림피아드 수준의 도전적 질문'
        }
        
        # 감정 가이드
        emotion_guide = {
            'frustrated': '답답하고 짜증나는 톤',
            'anxious': '불안하고 긴장된 톤',
            'confused': '헷갈리고 어려워하는 톤',
            'excited': '흥미롭고 궁금해하는 톤',
            'desperate': '급하고 절박한 톤',
            'neutral': '평온하고 차분한 톤'
        }
        
        prompt = f"""
당신은 한국 고등학생들의 수학 질문 스타일을 정확하게 모방하는 AI입니다.

**주제**: {target_topic}
**난이도**: {difficulty_guide.get(difficulty, '일반적인 수준')}
**감정**: {emotion_guide.get(emotion or style_features.get('emotion', 'neutral'), '자연스러운 톤')}

**학습할 학생 질문 예시들** (이 스타일을 정확히 따라야 함):
{style_examples}

**스타일 가이드**:
{style_guide}

**요구사항**:
1. 위 학생 질문 예시들의 스타일을 정확히 따라야 합니다
2. 자연스럽고 현실적인 학생 질문이어야 합니다
3. 주제와 난이도에 맞는 내용이어야 합니다
4. 한국어로 작성해야 합니다
5. 질문은 한 문장으로 끝내야 합니다

위 예시들과 같은 톤과 표현으로 '{target_topic}'에 대한 학생 질문을 생성해주세요:
"""
        return prompt
    
    def _get_style_examples(self, style_features: Dict) -> str:
        """스타일에 맞는 실제 학생 질문 예시들 가져오기"""
        examples = []
        
        logging.info(f"스타일 특징: {style_features}")
        logging.info(f"분석된 질문 수: {len(self.style_analysis)}")
        
        # 20개의 무작위 학생 질문 선택
        available_questions = list(self.style_analysis.keys())
        random_questions = random.sample(available_questions, min(20, len(available_questions)))
        
        for q in random_questions:
            examples.append(f"- {q}")
            logging.info(f"무작위 선택된 질문: {q[:50]}...")
        
        result = "\n".join(examples)
        logging.info(f"최종 선택된 예시들 ({len(examples)}개): {result[:200]}...")
        
        return result
    
    def _generate_style_guide(self, style_features: Dict) -> str:
        """스타일 가이드 생성"""
        guide_parts = []
        
        # 존댓말/반말 가이드
        formality = style_features.get('formality', 'mixed')
        if formality == 'formal':
            guide_parts.append("- 존댓말을 사용하세요 (요, 니다, 습니다)")
        elif formality == 'informal':
            guide_parts.append("- 반말을 사용하세요 (야, 어, 아, 지)")
        else:
            guide_parts.append("- 존댓말과 반말을 혼용하세요")
        
        # 감정 가이드
        emotion = style_features.get('emotion', 'neutral')
        if emotion == 'frustrated':
            guide_parts.append("- 답답하고 짜증나는 톤으로 작성하세요")
        elif emotion == 'anxious':
            guide_parts.append("- 불안하고 긴장된 톤으로 작성하세요")
        elif emotion == 'confused':
            guide_parts.append("- 헷갈리고 어려워하는 톤으로 작성하세요")
        elif emotion == 'excited':
            guide_parts.append("- 흥미롭고 궁금해하는 톤으로 작성하세요")
        elif emotion == 'desperate':
            guide_parts.append("- 급하고 절박한 톤으로 작성하세요")
        
        # 긴급함 가이드
        urgency = style_features.get('urgency', 0)
        if urgency >= 3:
            guide_parts.append("- 긴급함을 표현하는 단어를 사용하세요 (급해, 빨리, 시험 등)")
        
        # 불확실함 가이드
        uncertainty = style_features.get('uncertainty', 0)
        if uncertainty >= 2:
            guide_parts.append("- 불확실함을 표현하는 단어를 사용하세요 (같은데, 것 같은, 모르겠어 등)")
        
        # 어휘 수준 가이드
        vocab_level = style_features.get('vocabulary_level', 'unknown')
        if vocab_level == 'basic':
            guide_parts.append("- 기본적인 수학 용어를 사용하세요")
        elif vocab_level == 'intermediate':
            guide_parts.append("- 중급 수학 용어를 사용하세요")
        elif vocab_level == 'advanced':
            guide_parts.append("- 고급 수학 용어를 사용하세요")
        
        # 특수 표현 가이드
        if style_features.get('has_emoji', False):
            guide_parts.append("- 적절한 이모지를 사용하세요")
        if style_features.get('has_ellipsis', False):
            guide_parts.append("- 말줄임표(...)를 사용하세요")
        if style_features.get('has_exclamation', False):
            guide_parts.append("- 감탄사를 사용하세요")
        
        return "\n".join(guide_parts)
    
    def _validate_generated_question(self, question: str, target_style: Dict) -> bool:
        """생성된 질문의 품질 검증"""
        if not question or len(question) < 5:
            return False
        
        # 기본적인 한국어 검증
        if not re.search(r'[가-힣]', question):
            return False
        
        # 스타일 일치도 검증
        generated_features = self._extract_style_features(question)
        
        # 주요 스타일 특징들이 일치하는지 확인
        key_features = ['formality', 'emotion', 'urgency', 'uncertainty']
        match_score = 0
        
        for feature in key_features:
            if feature in target_style and feature in generated_features:
                if target_style[feature] == generated_features[feature]:
                    match_score += 1
        
        # 50% 이상 일치하면 통과
        return match_score >= len(key_features) * 0.5
    
    def _fallback_generation(self, target_topic: str, style_features: Dict, difficulty: str) -> str:
        """LLM 생성 실패 시 기본 템플릿 기반 생성"""
        # 기본 템플릿
        templates = {
            '수열': [
                "등차수열의 일반항을 구하는 방법이 뭔가요?",
                "등비수열의 공비를 어떻게 구하나요?",
                "수열의 합을 계산하는 공식이 궁금해요"
            ],
            '점화식': [
                "점화식을 푸는 방법을 알려주세요",
                "재귀적으로 정의된 수열을 어떻게 풀어요?",
                "점화식의 일반항을 구하는 과정이 헷갈려요"
            ],
            '귀납법': [
                "수학적 귀납법을 사용하는 방법이 뭔가요?",
                "귀납법으로 증명할 때 n=k+1 단계가 어려워요",
                "귀납가정을 어떻게 설정해야 하나요?"
            ],
            '수열의합': [
                "등차수열의 합을 구하는 공식을 설명해주세요",
                "시그마를 사용해서 수열의 합을 계산하는 방법이 궁금해요",
                "수열의 합을 구할 때 주의할 점이 뭔가요?"
            ]
        }
        
        base_templates = templates.get(target_topic, ["이 주제에 대해 궁금한 점이 있어요"])
        base_question = random.choice(base_templates)
        
        # 스타일에 맞게 조정
        adjusted_question = self._adjust_question_to_style(base_question, style_features)
        
        return adjusted_question
    
    def _adjust_question_to_style(self, question: str, style_features: Dict) -> str:
        """질문을 스타일에 맞게 조정"""
        adjusted = question
        
        # 존댓말/반말 조정
        formality = style_features.get('formality', 'mixed')
        if formality == 'informal':
            # 존댓말을 반말로 변경
            adjusted = adjusted.replace('요', '어')
            adjusted = adjusted.replace('니다', '어')
            adjusted = adjusted.replace('습니다', '어')
        elif formality == 'formal':
            # 반말을 존댓말로 변경
            adjusted = adjusted.replace('어', '요')
            adjusted = adjusted.replace('아', '요')
        
        # 감정 표현 추가
        emotion = style_features.get('emotion', 'neutral')
        if emotion == 'frustrated':
            adjusted = adjusted.replace('요', '요...')
            adjusted = adjusted.replace('어', '어...')
        elif emotion == 'anxious':
            adjusted = adjusted.replace('요', '요?')
            adjusted = adjusted.replace('어', '어?')
        elif emotion == 'desperate':
            if '시험' not in adjusted:
                adjusted = adjusted.replace('요', '요! 시험 때문에 급해요!')
                adjusted = adjusted.replace('어', '어! 시험 때문에 급해!')
        
        # 불확실함 표현 추가
        uncertainty = style_features.get('uncertainty', 0)
        if uncertainty >= 2:
            if '같은데' not in adjusted:
                adjusted = adjusted.replace('요', '요... 맞는 것 같은데 확신이 안 서요')
                adjusted = adjusted.replace('어', '어... 맞는 것 같은데 확신이 안 서')
        
        return adjusted
    
    async def generate_multiple_llm_questions(self, 
                                           target_topic: str,
                                           count: int = 5,
                                           style_variety: bool = True) -> List[str]:
        """LLM을 활용해 여러 개의 딥페이크 질문 생성"""
        questions = []
        
        for i in range(count):
            if style_variety:
                # 다양한 스타일로 생성
                available_styles = list(self.style_analysis.keys())
                style = random.choice(available_styles)
            else:
                style = None
            
            question = await self.generate_llm_deepfake_question(target_topic, style)
            questions.append(question)
        
        return questions
    
    def get_style_statistics(self) -> Dict[str, int]:
        """스타일별 통계"""
        stats = defaultdict(int)
        for features in self.style_analysis.values():
            stats[features.get('formality', 'unknown')] += 1
            stats[features.get('emotion', 'unknown')] += 1
        
        return dict(stats)
    
    def find_similar_style_questions(self, target_style: Dict, count: int = 5) -> List[str]:
        """특정 스타일과 유사한 질문들 찾기"""
        similarities = []
        
        for question, features in self.style_analysis.items():
            similarity_score = self._calculate_style_similarity(target_style, features)
            similarities.append((question, similarity_score))
        
        # 유사도 순으로 정렬
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        # 상위 count개 반환
        return [q for q, s in similarities[:count]]
    
    def _calculate_style_similarity(self, style1: Dict, style2: Dict) -> float:
        """두 스타일 간의 유사도 계산"""
        if not style1 or not style2:
            return 0.0
        
        score = 0.0
        total_features = 0
        
        # 주요 특징들 비교
        key_features = ['formality', 'emotion', 'urgency', 'uncertainty']
        
        for feature in key_features:
            if feature in style1 and feature in style2:
                if style1[feature] == style2[feature]:
                    score += 1.0
                total_features += 1
        
        # 수치형 특징들 비교 (정규화된 유사도)
        numeric_features = ['length']
        for feature in numeric_features:
            if feature in style1 and feature in style2:
                val1, val2 = style1[feature], style2[feature]
                if isinstance(val1, (int, float)) and isinstance(val2, (int, float)):
                    # 길이의 경우 정규화된 유사도 계산
                    max_len = max(val1, val2)
                    if max_len > 0:
                        similarity = 1.0 - abs(val1 - val2) / max_len
                        score += similarity
                    total_features += 1
        
        return score / total_features if total_features > 0 else 0.0

async def main():
    """메인 실행 함수"""
    print("🤖 LLM 기반 딥페이크식 학생 질문 생성기 시작\n")
    
    # 환경변수 확인
    print("🔧 환경변수 확인:")
    api_key = os.getenv('OPENAI_API_KEY')
    model = os.getenv('OPENAI_MODEL', 'gpt-4')
    data_path = os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    
    print(f"  OpenAI API 키: {'✅ 설정됨' if api_key else '❌ 설정되지 않음'}")
    print(f"  LLM 모델: {model}")
    print(f"  데이터 경로: {data_path}")
    print(f"  로그 레벨: {log_level}")
    print()
    
    if not api_key:
        print("❌ OPENAI_API_KEY 환경변수가 설정되지 않았습니다.")
        print("다음 방법 중 하나로 설정하세요:")
        print("1. .env 파일에 OPENAI_API_KEY=your-api-key 추가")
        print("2. export OPENAI_API_KEY='your-api-key' 실행")
        print("3. 코드에서 직접 전달")
        return
    
    # 생성기 초기화
    generator = LLMDeepfakeGenerator(api_key, model, data_path)
    
    if not generator.real_questions:
        print("❌ 실제 질문 데이터를 로드할 수 없습니다.")
        return
    
    print(f"✅ {len(generator.real_questions)}개의 실제 질문 로드 완료\n")
    
    # 스타일 통계 출력
    style_stats = generator.get_style_statistics()
    print("📊 스타일별 통계:")
    for style, count in style_stats.items():
        print(f"  {style}: {count}개")
    
    print("\n" + "="*60 + "\n")
    
    # LLM을 활용한 딥페이크 질문 생성
    topics = ['수열', '점화식', '귀납법', '수열의합']
    
    for topic in topics:
        print(f"🎯 주제: {topic}")
        print("-" * 40)
        
        # 다양한 난이도로 질문 생성
        difficulties = ['naive', 'basic', 'intermediate', 'advanced']
        
        for difficulty in difficulties:
            question = await generator.generate_llm_deepfake_question(topic, difficulty=difficulty)
            print(f"{difficulty:12}: {question}")
        
        print()
    
    print("="*60 + "\n")
    
    # 스타일별 질문 생성 예시
    print("🎭 스타일별 질문 생성 예시:")
    print("-" * 40)
    
    # 실제 스타일 중에서 선택
    available_styles = list(generator.style_analysis.keys())[:5]  # 처음 5개만
    
    for style in available_styles:
        question = await generator.generate_llm_deepfake_question('수열', style)
        print(f"스타일: {question[:50]}...")
    
    print("\n" + "="*60 + "\n")
    
    # 여러 질문 한번에 생성
    print("🔄 여러 질문 한번에 생성:")
    print("-" * 40)
    
    multiple_questions = await generator.generate_multiple_llm_questions('점화식', count=3, style_variety=True)
    
    for i, question in enumerate(multiple_questions, 1):
        print(f"{i}. {question}")
    
    print("\n✅ LLM 딥페이크 질문 생성 완료!")

if __name__ == "__main__":
    asyncio.run(main())
