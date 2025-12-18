#!/usr/bin/env python3
"""
CurriculumTermAgent 통합 테스트
에이전트가 실제로 작동하는지 테스트합니다.
"""

import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

from agent.agents.curriculum_term.agent import CurriculumTermAgent
from agent.agents.curriculum_term.tools.curriculum_term_tool import CurriculumTermTool

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_agent_integration():
    """에이전트 통합 테스트"""
    print("=== CurriculumTermAgent 통합 테스트 시작 ===\n")
    
    try:
        # 1. 에이전트 초기화 테스트
        print("1. 에이전트 초기화...")
        agent = CurriculumTermAgent()
        print("✓ 에이전트 초기화 성공")
        
        # 2. 도구 초기화 테스트
        print("\n2. 도구 초기화...")
        tool = agent.curriculum_tool
        if tool.curriculum_corpus:
            print(f"✓ 데이터베이스 로드 성공: {tool.curriculum_corpus}")
        else:
            print("⚠ 데이터베이스를 찾을 수 없습니다. 일부 기능이 제한될 수 있습니다.")
        
        # 3. 질문 분석 테스트
        print("\n3. 질문 분석 테스트...")
        test_questions = [
            "미분과 적분의 기본 정리에 대해 설명해주세요",
            "수열의 일반항을 구하는 방법을 알려주세요",
            "함수의 정의역과 치역이 무엇인가요?",
            "사인법칙을 이용해서 삼각형의 넓이를 구하는 방법을 설명해주세요"
        ]
        
        for i, question in enumerate(test_questions, 1):
            print(f"\n--- 테스트 질문 {i}: {question} ---")
            
            try:
                # 에이전트를 통한 질문 분석
                result = await agent.analyze_question_and_suggest_terms(question)
                
                if result.get("success"):
                    print("✓ 질문 분석 성공")
                    print(f"  - 제안 용어: {', '.join(result.get('suggested_terms', [])[:5])}")
                    print(f"  - 개념 수준: {result.get('concept_level', 'N/A')}")
                    print(f"  - 피해야 할 용어: {', '.join(result.get('avoid_terms', [])[:3])}")
                    print(f"  - 분석: {result.get('analysis', 'N/A')}")
                    
                    # 권장사항 출력
                    recommendations = result.get('recommendations', [])
                    if recommendations:
                        print("  - 권장사항:")
                        for rec in recommendations[:3]:
                            print(f"    * {rec}")
                else:
                    print(f"✗ 질문 분석 실패: {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                print(f"✗ 질문 분석 중 오류: {e}")
        
        # 4. 용어 검증 테스트
        print("\n4. 용어 검증 테스트...")
        test_content = """
        이 문제는 도함수를 이용하여 함수의 극값을 구하는 문제입니다.
        정적분과 부정적분의 차이점을 이해하고, 합성함수의 미분법을 적용해야 합니다.
        또한 수학적 귀납법을 사용하여 등식이 성립함을 증명할 수 있습니다.
        """
        
        try:
            verification_result = await agent.verify_final_response({
                "answer": test_content
            }, "answer")
            
            if verification_result.get("curriculum_verified"):
                print("✓ 용어 검증 성공")
                violations = verification_result.get("term_violations", [])
                suggestions = verification_result.get("term_suggestions", [])
                
                if violations:
                    print(f"  - 용어 위반: {len(violations)}개")
                    for violation in violations[:2]:
                        print(f"    * {violation['term']}: {violation['issue']}")
                
                if suggestions:
                    print(f"  - 용어 제안: {len(suggestions)}개")
                    for suggestion in suggestions[:2]:
                        print(f"    * {suggestion['original']} → {suggestion['replacement']}")
                
                if verification_result.get("text_corrected"):
                    print("  - 텍스트가 자동으로 수정되었습니다.")
            else:
                print(f"✗ 용어 검증 실패: {verification_result.get('verification_error', 'Unknown error')}")
                
        except Exception as e:
            print(f"✗ 용어 검증 중 오류: {e}")
        
        # 5. 직접 도구 사용 테스트
        print("\n5. 직접 도구 사용 테스트...")
        try:
            search_result = await tool.search("수열", k=3)
            
            if "error" not in search_result:
                print("✓ 도구 검색 성공")
                curriculum_count = len(search_result.get("curriculum_results", []))
                textbook_count = len(search_result.get("textbook_results", []))
                print(f"  - 교과과정 결과: {curriculum_count}건")
                print(f"  - 교과서 결과: {textbook_count}건")
            else:
                print(f"✗ 도구 검색 실패: {search_result['error']}")
                
        except Exception as e:
            print(f"✗ 도구 검색 중 오류: {e}")
        
        print("\n=== 통합 테스트 완료 ===")
        
    except Exception as e:
        print(f"✗ 통합 테스트 중 치명적 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_agent_integration())
