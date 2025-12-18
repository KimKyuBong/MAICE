#!/usr/bin/env python3
"""
딥페이크식 학생 질문 생성기
실제 학생들이 GPT에 질문한 형태를 분석해서 비슷한 문체와 패턴으로 새로운 질문을 생성
"""

import json
import os
import random
import re
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import logging

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. pip install python-dotenv를 실행하세요.")
    print("환경변수를 직접 설정하거나 .env 파일을 사용할 수 없습니다.")

# 로깅 설정
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level.upper()),
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('deepfake_generator.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class DeepfakeQuestionGenerator:
    """실제 학생 질문 패턴을 분석하고 딥페이크식 질문을 생성하는 클래스"""
    
    def __init__(self, data_path: str = None):
        self.data_path = data_path or os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
        self.real_questions = []
        self.question_patterns = defaultdict(list)
        self.style_patterns = defaultdict(list)
        self.topic_keywords = defaultdict(list)
        self.load_real_data()
        self.analyze_patterns()
    
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
                    with open(path, "r", encoding="utf-8") as f:
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
                            self.real_questions.append(question_text.strip())
                            question_count += 1
            
            logging.info(f"로드된 실제 질문 수: {len(self.real_questions)} (최대: {max_questions})")
            
        except Exception as e:
            logging.error(f"실제 데이터 로드 실패: {e}")
            logging.error("데이터 파일 경로와 형식을 확인하세요")
    
    def analyze_patterns(self):
        """질문 패턴 분석"""
        if not self.real_questions:
            logging.warning("분석할 질문이 없습니다")
            return
        
        for question in self.real_questions:
            # 문체 패턴 분석
            self._analyze_style_patterns(question)
            
            # 주제별 키워드 추출
            self._extract_topic_keywords(question)
            
            # 질문 패턴 분류
            self._categorize_question_patterns(question)
        
        logging.info(f"패턴 분석 완료: {len(self.real_questions)}개 질문")
    
    def _analyze_style_patterns(self, question: str):
        """문체 패턴 분석"""
        # 존댓말/반말 패턴
        if re.search(r'[요|니다|습니다|니다]', question):
            self.style_patterns['formal'].append(question)
        elif re.search(r'[야|어|아|지]', question):
            self.style_patterns['informal'].append(question)
        else:
            self.style_patterns['mixed'].append(question)
        
        # 이모지 사용 패턴
        if re.search(r'[😀-🙏🌀-🗿]', question):
            self.style_patterns['emoji'].append(question)
        
        # 말줄임표 패턴
        if re.search(r'\.{2,}', question):
            self.style_patterns['ellipsis'].append(question)
        
        # 감탄사 패턴
        if re.search(r'[아|어|오|우|으|이]+\!+', question):
            self.style_patterns['exclamation'].append(question)
        
        # 불확실함 표현 패턴
        if re.search(r'[같은데|같은|것 같은|모르겠어|잘 모르겠어]', question):
            self.style_patterns['uncertain'].append(question)
        
        # 긴급함 표현 패턴
        if re.search(r'[급해|빨리|시험|내일|오늘]', question):
            self.style_patterns['urgent'].append(question)
    
    def _extract_topic_keywords(self, question: str):
        """주제별 키워드 추출"""
        # 수학 주제별 키워드
        math_topics = {
            '수열': ['수열', '등차수열', '등비수열', '일반항', '공차', '공비'],
            '점화식': ['점화식', '재귀', 'an+1', 'an-1'],
            '귀납법': ['귀납법', '수학적귀납법', 'n=k', 'n=k+1'],
            '수열의합': ['합', '시그마', 'Σ', '합계'],
            '함수': ['함수', 'f(x)', '정의역', '치역'],
            '미분': ['미분', '도함수', 'f\'(x)', '접선'],
            '적분': ['적분', '부정적분', '정적분', '∫'],
            '확률': ['확률', '조합', '순열', '경우의수'],
            '통계': ['평균', '분산', '표준편차', '정규분포']
        }
        
        for topic, keywords in math_topics.items():
            for keyword in keywords:
                if keyword in question:
                    self.topic_keywords[topic].append(question)
                    break
    
    def _categorize_question_patterns(self, question: str):
        """질문 패턴 분류"""
        # 질문 시작 패턴
        if re.match(r'^[가-힣]*[가-힣]+\?', question):
            self.question_patterns['direct_question'].append(question)
        elif re.match(r'^[가-힣]*[가-힣]+[가-힣]*[가-힣]+\?', question):
            self.question_patterns['detailed_question'].append(question)
        
        # 설명 요청 패턴
        if re.search(r'[설명|알려줘|가르쳐|도와줘]', question):
            self.question_patterns['explanation_request'].append(question)
        
        # 확인 요청 패턴
        if re.search(r'[맞나|맞는지|틀렸나|어떻게]', question):
            self.question_patterns['verification_request'].append(question)
        
        # 예시 요청 패턴
        if re.search(r'[예시|예제|문제|풀이]', question):
            self.question_patterns['example_request'].append(question)
    
    def generate_deepfake_question(self, 
                                 target_topic: str, 
                                 style_preference: str = None,
                                 difficulty: str = 'intermediate') -> str:
        """딥페이크식 질문 생성"""
        if not self.real_questions:
            return "기본 질문을 생성할 수 없습니다."
        
        # 스타일 선택
        if style_preference and style_preference in self.style_patterns:
            available_styles = self.style_patterns[style_preference]
        else:
            available_styles = self.real_questions
        
        if not available_styles:
            available_styles = self.real_questions
        
        # 템플릿 질문 선택
        template_question = random.choice(available_styles)
        
        # 주제별 키워드 매핑
        topic_mapping = self._get_topic_mapping(target_topic)
        
        # 딥페이크 질문 생성
        deepfake_question = self._apply_topic_transformation(template_question, topic_mapping)
        
        # 난이도에 따른 조정
        deepfake_question = self._adjust_difficulty(deepfake_question, difficulty)
        
        return deepfake_question
    
    def _get_topic_mapping(self, target_topic: str) -> Dict[str, str]:
        """주제별 키워드 매핑"""
        topic_mappings = {
            '수열': {
                '수열': '수열',
                '등차수열': '등차수열',
                '등비수열': '등비수열',
                '일반항': '일반항',
                '공차': '공차',
                '공비': '공비',
                '점화식': '점화식',
                '재귀': '재귀'
            },
            '점화식': {
                '수열': '점화식',
                '등차수열': '선형점화식',
                '등비수열': '지수점화식',
                '일반항': '일반항',
                '공차': '계수',
                '공비': '계수',
                '점화식': '점화식',
                '재귀': '재귀'
            },
            '귀납법': {
                '수열': '귀납법',
                '등차수열': '수학적귀납법',
                '등비수열': '수학적귀납법',
                '일반항': '성질',
                '공차': '조건',
                '공비': '조건',
                '점화식': '귀납가정',
                '재귀': '귀납단계'
            },
            '수열의합': {
                '수열': '수열의합',
                '등차수열': '등차수열의합',
                '등비수열': '등비수열의합',
                '일반항': '합계',
                '공차': '항의개수',
                '공비': '항의개수',
                '점화식': '합의점화식',
                '재귀': '누적합'
            }
        }
        
        return topic_mappings.get(target_topic, {})
    
    def _apply_topic_transformation(self, template: str, mapping: Dict[str, str]) -> str:
        """템플릿에 주제 변환 적용"""
        result = template
        
        # 키워드 치환
        for old_keyword, new_keyword in mapping.items():
            if old_keyword in result:
                result = result.replace(old_keyword, new_keyword)
        
        # 추가적인 주제별 변환
        if '수열' in result and '수열' not in result:
            result = result.replace('수열', '수열')
        if '점화식' in result and '점화식' not in result:
            result = result.replace('점화식', '점화식')
        if '귀납법' in result and '귀납법' not in result:
            result = result.replace('귀납법', '귀납법')
        
        return result
    
    def _adjust_difficulty(self, question: str, difficulty: str) -> str:
        """난이도에 따른 질문 조정"""
        if difficulty == 'naive':
            # 기본 개념 수준
            if '어떻게' in question:
                question = question.replace('어떻게', '간단하게 어떻게')
            if '설명' in question:
                question = question.replace('설명', '기본 설명')
        
        elif difficulty == 'basic':
            # 기초 수준
            pass
        
        elif difficulty == 'intermediate':
            # 중급 수준
            if '어떻게' in question:
                question = question.replace('어떻게', '구체적으로 어떻게')
        
        elif difficulty == 'advanced':
            # 고급 수준
            if '어떻게' in question:
                question = question.replace('어떻게', '정확하게 어떻게')
            if '설명' in question:
                question = question.replace('설명', '자세한 설명')
        
        elif difficulty == 'olympiad':
            # 올림피아드 수준
            if '어떻게' in question:
                question = question.replace('어떻게', '엄밀하게 어떻게')
            if '설명' in question:
                question = question.replace('설명', '엄밀한 증명')
        
        return question
    
    def generate_multiple_questions(self, 
                                  target_topic: str, 
                                  count: int = 5,
                                  style_variety: bool = True) -> List[str]:
        """여러 개의 딥페이크 질문 생성"""
        questions = []
        
        for i in range(count):
            if style_variety:
                # 다양한 스타일로 생성
                available_styles = list(self.style_patterns.keys())
                style = random.choice(available_styles)
            else:
                style = None
            
            question = self.generate_deepfake_question(target_topic, style)
            questions.append(question)
        
        return questions
    
    def analyze_question_style(self, question: str) -> Dict[str, any]:
        """질문의 스타일 분석"""
        analysis = {
            'formality': 'mixed',
            'has_emoji': False,
            'has_ellipsis': False,
            'has_exclamation': False,
            'uncertainty_level': 0,
            'urgency_level': 0,
            'pattern_type': 'unknown'
        }
        
        # 존댓말/반말 분석
        formal_count = len(re.findall(r'[요|니다|습니다|니다]', question))
        informal_count = len(re.findall(r'[야|어|아|지]', question))
        
        if formal_count > informal_count:
            analysis['formality'] = 'formal'
        elif informal_count > formal_count:
            analysis['formality'] = 'informal'
        
        # 이모지 분석
        analysis['has_emoji'] = bool(re.search(r'[😀-🙏🌀-🗿]', question))
        
        # 말줄임표 분석
        analysis['has_ellipsis'] = bool(re.search(r'\.{2,}', question))
        
        # 감탄사 분석
        analysis['has_exclamation'] = bool(re.search(r'[아|어|오|우|으|이]+\!+', question))
        
        # 불확실함 수준
        uncertainty_words = ['같은데', '같은', '것 같은', '모르겠어', '잘 모르겠어', '아마', '혹시']
        analysis['uncertainty_level'] = sum(1 for word in uncertainty_words if word in question)
        
        # 긴급함 수준
        urgency_words = ['급해', '빨리', '시험', '내일', '오늘', '당장', '바로']
        analysis['urgency_level'] = sum(1 for word in urgency_words if word in question)
        
        # 패턴 타입 분석
        for pattern_type, questions in self.question_patterns.items():
            if question in questions:
                analysis['pattern_type'] = pattern_type
                break
        
        return analysis
    
    def get_style_statistics(self) -> Dict[str, int]:
        """스타일별 통계"""
        stats = {}
        for style, questions in self.style_patterns.items():
            stats[style] = len(questions)
        return stats
    
    def get_topic_statistics(self) -> Dict[str, int]:
        """주제별 통계"""
        stats = {}
        for topic, questions in self.topic_keywords.items():
            stats[topic] = len(questions)
        return stats

def main():
    """메인 실행 함수"""
    print("🎭 딥페이크식 학생 질문 생성기 시작\n")
    
    # 환경 설정 확인
    print("🔧 환경 설정 확인:")
    data_path = os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    max_questions = os.getenv('MAX_QUESTIONS', '1000')
    
    print(f"  데이터 경로: {data_path}")
    print(f"  로그 레벨: {log_level}")
    print(f"  최대 질문 수: {max_questions}")
    print()
    
    # 생성기 초기화
    generator = DeepfakeQuestionGenerator(data_path)
    
    if not generator.real_questions:
        print("❌ 실제 질문 데이터를 로드할 수 없습니다.")
        return
    
    print(f"✅ {len(generator.real_questions)}개의 실제 질문 로드 완료\n")
    
    # 스타일 통계 출력
    style_stats = generator.get_style_statistics()
    print("📊 스타일별 통계:")
    for style, count in style_stats.items():
        print(f"  {style}: {count}개")
    
    print()
    
    # 주제별 통계 출력
    topic_stats = generator.get_topic_statistics()
    print("📚 주제별 통계:")
    for topic, count in topic_stats.items():
        print(f"  {topic}: {count}개")
    
    print("\n" + "="*60 + "\n")
    
    # 다양한 주제로 딥페이크 질문 생성
    topics = ['수열', '점화식', '귀납법', '수열의합']
    
    for topic in topics:
        print(f"🎯 주제: {topic}")
        print("-" * 40)
        
        # 다양한 난이도로 질문 생성
        difficulties = ['naive', 'basic', 'intermediate', 'advanced', 'olympiad']
        
        for difficulty in difficulties:
            question = generator.generate_deepfake_question(topic, difficulty=difficulty)
            print(f"{difficulty:12}: {question}")
        
        print()
    
    print("="*60 + "\n")
    
    # 스타일별 질문 생성 예시
    print("🎭 스타일별 질문 생성 예시:")
    print("-" * 40)
    
    styles = ['formal', 'informal', 'emoji', 'ellipsis', 'uncertain', 'urgent']
    
    for style in styles:
        if style in generator.style_patterns and generator.style_patterns[style]:
            question = generator.generate_deepfake_question('수열', style)
            print(f"{style:10}: {question}")
    
    print("\n" + "="*60 + "\n")
    
    # 여러 질문 한번에 생성
    print("🔄 여러 질문 한번에 생성:")
    print("-" * 40)
    
    multiple_questions = generator.generate_multiple_questions('점화식', count=3, style_variety=True)
    
    for i, question in enumerate(multiple_questions, 1):
        print(f"{i}. {question}")
    
    print("\n✅ 딥페이크 질문 생성 완료!")

if __name__ == "__main__":
    main()
