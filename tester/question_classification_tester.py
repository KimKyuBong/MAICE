#!/usr/bin/env python3
"""
질문분류 및 명료화 단계 테스터
생성된 300개 딥페이크 질문을 사용하여 에이전트의 질문분류 및 명료화 기능을 테스트
"""

import asyncio
import json
import logging
import os
import random
import time
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# OpenAI 클라이언트
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    logging.warning("openai를 사용할 수 없습니다. 'pip install openai'를 실행하세요.")

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('question_classification_tester.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class QuestionClassificationTester:
    """질문분류 및 명료화 단계 테스터"""
    
    def __init__(self):
        self.openai_client = None
        self.model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
        self.test_questions = []
        self.results = []
        
        # OpenAI 클라이언트 초기화
        if OPENAI_AVAILABLE:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = AsyncOpenAI(api_key=api_key)
                logging.info(f"✅ OpenAI 클라이언트 초기화 완료 (모델: {self.model})")
            else:
                logging.warning("❌ OpenAI API 키가 설정되지 않았습니다")
        else:
            logging.warning("❌ OpenAI 패키지가 설치되지 않았습니다")
    
    def load_test_questions(self, file_path: str) -> bool:
        """테스트용 질문 데이터 로드"""
        try:
            if not os.path.exists(file_path):
                logging.error(f"파일을 찾을 수 없습니다: {file_path}")
                return False
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'output_questions' not in data:
                logging.error("output_questions 필드를 찾을 수 없습니다")
                return False
            
            # 성공적으로 생성된 질문만 필터링
            valid_questions = []
            for q in data['output_questions']:
                if (isinstance(q, dict) and 
                    'new_question' in q and 
                    q['new_question'] and 
                    not q['new_question'].startswith('[생성 실패]') and
                    not q['new_question'].startswith('[배치')):
                    valid_questions.append(q)
            
            self.test_questions = valid_questions
            logging.info(f"✅ {len(self.test_questions)}개의 유효한 테스트 질문 로드 완료")
            return True
            
        except Exception as e:
            logging.error(f"테스트 질문 로드 실패: {e}")
            return False
    
    async def test_question_classification(self, question: Dict[str, Any]) -> Dict[str, Any]:
        """개별 질문의 분류 테스트"""
        try:
            # 1단계: 질문 분류
            classification_prompt = f"""
다음 학생 질문을 분석하여 다음 항목들을 분류해주세요:

질문: {question['new_question']}

분류 항목:
1. 수학 주제 (수열, 점화식, 귀납법, 수열의합, 등차수열, 등비수열, 수학적귀납법, 조합론 중 선택)
2. 질문 유형 (개념 이해, 계산 방법, 증명, 문제 풀이, 오개념 확인 등)
3. 난이도 (초급, 중급, 고급)
4. 학생 수준 (기초, 보통, 심화)
5. 명료화 필요 여부 (예/아니오)
6. 명료화가 필요한 이유 (명료화가 필요하다면)

JSON 형식으로 응답해주세요:
{{
    "classification": {{
        "topic": "주제명",
        "question_type": "질문유형",
        "difficulty": "난이도",
        "student_level": "학생수준",
        "needs_clarification": true/false,
        "clarification_reason": "이유"
    }}
}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "당신은 학생 질문을 분석하고 분류하는 전문가입니다. 정확하고 일관된 분류를 제공하세요."},
                    {"role": "user", "content": classification_prompt}
                ],
                max_completion_tokens=1000
            )
            
            classification_result = response.choices[0].message.content.strip()
            
            # JSON 파싱
            try:
                classification_data = json.loads(classification_result)
                classification = classification_data.get('classification', {})
            except:
                classification = {"error": "JSON 파싱 실패"}
            
            # 2단계: 명료화 질문 생성 (필요한 경우)
            clarification_questions = []
            if classification.get('needs_clarification', False):
                clarification_prompt = f"""
다음 학생 질문에 대해 명료화가 필요합니다:

원본 질문: {question['new_question']}
분류: {classification.get('topic', '')} - {classification.get('question_type', '')}
명료화 이유: {classification.get('clarification_reason', '')}

이 학생에게 명료화를 위해 물어볼 2-3개의 구체적인 질문을 생성해주세요.
각 질문은 학생이 자신의 의도를 더 명확하게 표현할 수 있도록 도와야 합니다.

JSON 형식으로 응답해주세요:
{{
    "clarification_questions": [
        "명료화 질문 1",
        "명료화 질문 2",
        "명료화 질문 3"
    ]
}}
"""
                
                clarification_response = await self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "당신은 학생 질문을 명료화하는 전문가입니다. 구체적이고 도움이 되는 명료화 질문을 생성하세요."},
                        {"role": "user", "content": clarification_prompt}
                    ],
                    max_completion_tokens=1000
                )
                
                clarification_text = clarification_response.choices[0].message.content.strip()
                try:
                    clarification_data = json.loads(clarification_text)
                    clarification_questions = clarification_data.get('clarification_questions', [])
                except:
                    clarification_questions = ["명료화 질문 생성 실패"]
            
            return {
                'question_id': question['id'],
                'original_question': question['new_question'],
                'target_topic': question['target_topic'],
                'classification': classification,
                'clarification_questions': clarification_questions,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logging.error(f"질문 분류 테스트 실패 (ID: {question.get('id', 'unknown')}): {e}")
            return {
                'question_id': question.get('id', 'unknown'),
                'original_question': question.get('new_question', ''),
                'target_topic': question.get('target_topic', ''),
                'classification': {"error": str(e)},
                'clarification_questions': [],
                'timestamp': datetime.now().isoformat()
            }
    
    async def run_batch_test(self, batch_size: int = 10, delay: float = 1.0) -> None:
        """배치 단위로 테스트 실행"""
        if not self.test_questions:
            logging.error("테스트 질문이 로드되지 않았습니다")
            return
        
        total_questions = len(self.test_questions)
        total_batches = (total_questions + batch_size - 1) // batch_size
        
        logging.info(f"🚀 배치 테스트 시작: 총 {total_questions}개 질문, {total_batches}개 배치")
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, total_questions)
            batch_questions = self.test_questions[start_idx:end_idx]
            
            logging.info(f"📦 배치 {batch_num + 1}/{total_batches} 처리 중... ({start_idx+1}-{end_idx})")
            
            batch_results = []
            for i, question in enumerate(batch_questions):
                logging.info(f"  질문 {start_idx + i + 1}/{total_questions} 처리 중...")
                result = await self.test_question_classification(question)
                batch_results.append(result)
                
                # API 제한 고려하여 잠시 대기
                if i < len(batch_questions) - 1:
                    await asyncio.sleep(0.5)
            
            self.results.extend(batch_results)
            
            # 배치 완료 후 잠시 대기
            if batch_num < total_batches - 1:
                logging.info(f"⏳ 다음 배치 준비 중... ({delay}초 대기)")
                await asyncio.sleep(delay)
        
        logging.info(f"✅ 모든 테스트 완료: {len(self.results)}개 결과")
    
    def analyze_results(self) -> Dict[str, Any]:
        """테스트 결과 분석"""
        if not self.results:
            return {"error": "분석할 결과가 없습니다"}
        
        # 기본 통계
        total_questions = len(self.results)
        successful_classifications = sum(1 for r in self.results if 'error' not in r.get('classification', {}))
        needs_clarification = sum(1 for r in self.results if r.get('classification', {}).get('needs_clarification', False))
        
        # 주제별 분포
        topic_distribution = {}
        for result in self.results:
            topic = result.get('classification', {}).get('topic', 'unknown')
            topic_distribution[topic] = topic_distribution.get(topic, 0) + 1
        
        # 질문 유형별 분포
        question_type_distribution = {}
        for result in self.results:
            q_type = result.get('classification', {}).get('question_type', 'unknown')
            question_type_distribution[q_type] = question_type_distribution.get(q_type, 0) + 1
        
        # 난이도별 분포
        difficulty_distribution = {}
        for result in self.results:
            difficulty = result.get('classification', {}).get('difficulty', 'unknown')
            difficulty_distribution[difficulty] = difficulty_distribution.get(difficulty, 0) + 1
        
        # 학생 수준별 분포
        student_level_distribution = {}
        for result in self.results:
            level = result.get('classification', {}).get('student_level', 'unknown')
            student_level_distribution[level] = student_level_distribution.get(level, 0) + 1
        
        return {
            'summary': {
                'total_questions': total_questions,
                'successful_classifications': successful_classifications,
                'classification_success_rate': successful_classifications / total_questions * 100,
                'needs_clarification': needs_clarification,
                'clarification_rate': needs_clarification / total_questions * 100
            },
            'distributions': {
                'topics': topic_distribution,
                'question_types': question_type_distribution,
                'difficulties': difficulty_distribution,
                'student_levels': student_level_distribution
            }
        }
    
    def save_results(self, filename: str = None) -> str:
        """테스트 결과 저장"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'output/question_classification_test_results_{timestamp}.json'
        
        # 출력 디렉토리 생성
        os.makedirs('output', exist_ok=True)
        
        # 결과 데이터 구성
        result_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'model': self.model,
                'total_questions': len(self.test_questions),
                'tested_questions': len(self.results)
            },
            'analysis': self.analyze_results(),
            'detailed_results': self.results
        }
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        logging.info(f"✅ 결과가 '{filename}'에 저장되었습니다")
        return filename
    
    def print_summary(self) -> None:
        """테스트 결과 요약 출력"""
        analysis = self.analyze_results()
        
        if 'error' in analysis:
            logging.error(f"분석 오류: {analysis['error']}")
            return
        
        summary = analysis['summary']
        distributions = analysis['distributions']
        
        print("\n" + "="*60)
        print("📊 질문분류 및 명료화 테스트 결과 요약")
        print("="*60)
        
        print(f"\n📈 기본 통계:")
        print(f"  총 질문 수: {summary['total_questions']}개")
        print(f"  성공적 분류: {summary['successful_classifications']}개")
        print(f"  분류 성공률: {summary['classification_success_rate']:.1f}%")
        print(f"  명료화 필요: {summary['needs_clarification']}개")
        print(f"  명료화 비율: {summary['clarification_rate']:.1f}%")
        
        print(f"\n🎯 주제별 분포:")
        for topic, count in sorted(distributions['topics'].items()):
            percentage = count / summary['total_questions'] * 100
            print(f"  {topic}: {count}개 ({percentage:.1f}%)")
        
        print(f"\n❓ 질문 유형별 분포:")
        for q_type, count in sorted(distributions['question_types'].items()):
            percentage = count / summary['total_questions'] * 100
            print(f"  {q_type}: {count}개 ({percentage:.1f}%)")
        
        print(f"\n📚 난이도별 분포:")
        for difficulty, count in sorted(distributions['difficulties'].items()):
            percentage = count / summary['total_questions'] * 100
            print(f"  {difficulty}: {count}개 ({percentage:.1f}%)")
        
        print(f"\n👨‍🎓 학생 수준별 분포:")
        for level, count in sorted(distributions['student_levels'].items()):
            percentage = count / summary['total_questions'] * 100
            print(f"  {level}: {count}개 ({percentage:.1f}%)")

async def main():
    """메인 실행 함수"""
    print("🚀 질문분류 및 명료화 단계 테스터 시작")
    print("="*60)
    
    # 테스터 초기화
    tester = QuestionClassificationTester()
    
    if not tester.openai_client:
        print("❌ OpenAI 클라이언트 초기화 실패")
        return
    
    # 테스트 질문 로드
    test_file = 'output/deepfake_test_results_20250818_070138.json'
    if not tester.load_test_questions(test_file):
        print("❌ 테스트 질문 로드 실패")
        return
    
    # 배치 테스트 실행
    print(f"📋 {len(tester.test_questions)}개 질문으로 테스트 시작...")
    await tester.run_batch_test(batch_size=20, delay=2.0)
    
    # 결과 분석 및 출력
    tester.print_summary()
    
    # 결과 저장
    output_file = tester.save_results()
    print(f"\n💾 상세 결과가 저장되었습니다: {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
