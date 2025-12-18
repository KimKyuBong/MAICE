#!/usr/bin/env python3
"""
CurriculumTermAgent 독립 실행 스크립트
에이전트를 직접 실행하여 교과과정 용어 분석 및 검증을 수행합니다.
"""

import asyncio
import logging
import sys
import os
from typing import Dict, Any

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from agent.agents.curriculum_term.agent import CurriculumTermAgent

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def run_curriculum_agent():
    """교과과정 용어 에이전트 실행"""
    print("=== CurriculumTermAgent 실행 ===\n")
    
    try:
        # 에이전트 초기화
        agent = CurriculumTermAgent()
        print("✓ 에이전트 초기화 완료")
        
        # 대화형 인터페이스
        print("\n교과과정 용어 분석 및 검증을 시작합니다.")
        print("종료하려면 'quit' 또는 'exit'를 입력하세요.\n")
        
        while True:
            try:
                # 사용자 입력 받기
                user_input = input("질문이나 검증할 내용을 입력하세요: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '종료']:
                    print("에이전트를 종료합니다.")
                    break
                
                if not user_input:
                    continue
                
                print(f"\n--- 입력: {user_input} ---")
                
                # 질문 분석 수행
                print("질문 분석 중...")
                analysis_result = await agent.analyze_question_and_suggest_terms(user_input)
                
                if analysis_result.get("success"):
                    print("✓ 질문 분석 완료")
                    print(f"  - 제안 용어: {', '.join(analysis_result.get('suggested_terms', [])[:5])}")
                    print(f"  - 개념 수준: {analysis_result.get('concept_level', 'N/A')}")
                    print(f"  - 피해야 할 용어: {', '.join(analysis_result.get('avoid_terms', [])[:3])}")
                    print(f"  - 분석: {analysis_result.get('analysis', 'N/A')}")
                    
                    # 권장사항 출력
                    recommendations = analysis_result.get('recommendations', [])
                    if recommendations:
                        print("  - 권장사항:")
                        for rec in recommendations:
                            print(f"    * {rec}")
                else:
                    print(f"✗ 질문 분석 실패: {analysis_result.get('error', 'Unknown error')}")
                
                # 용어 검증 수행
                print("\n용어 검증 중...")
                verification_result = await agent.verify_final_response({
                    "answer": user_input
                }, "answer")
                
                if verification_result.get("curriculum_verified"):
                    print("✓ 용어 검증 완료")
                    violations = verification_result.get("term_violations", [])
                    suggestions = verification_result.get("term_suggestions", [])
                    
                    if violations:
                        print(f"  - 용어 위반: {len(violations)}개")
                        for violation in violations[:3]:
                            print(f"    * {violation['term']}: {violation['issue']}")
                    
                    if suggestions:
                        print(f"  - 용어 제안: {len(suggestions)}개")
                        for suggestion in suggestions[:3]:
                            print(f"    * {suggestion['original']} → {suggestion['replacement']}")
                    
                    if verification_result.get("text_corrected"):
                        print("  - 수정된 텍스트:")
                        print(f"    {verification_result.get('answer', '')}")
                else:
                    print(f"✗ 용어 검증 실패: {verification_result.get('verification_error', 'Unknown error')}")
                
                print("\n" + "="*50 + "\n")
                
            except KeyboardInterrupt:
                print("\n\n에이전트를 종료합니다.")
                break
            except Exception as e:
                print(f"오류 발생: {e}")
                print("계속하려면 Enter를 누르세요...")
                input()
        
    except Exception as e:
        print(f"치명적 오류: {e}")
        import traceback
        traceback.print_exc()

async def run_single_analysis(question: str):
    """단일 질문 분석 실행"""
    try:
        agent = CurriculumTermAgent()
        print(f"질문: {question}")
        
        # 질문 분석
        result = await agent.analyze_question_and_suggest_terms(question)
        print(f"분석 결과: {result}")
        
    except Exception as e:
        print(f"오류: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # 명령행 인수로 질문이 주어진 경우
        question = " ".join(sys.argv[1:])
        asyncio.run(run_single_analysis(question))
    else:
        # 대화형 모드
        asyncio.run(run_curriculum_agent())
