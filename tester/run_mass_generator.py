#!/usr/bin/env python3
"""
대량 딥페이크 학생 질문 생성기 실행 스크립트
"""

import os
import sys
import asyncio
from pathlib import Path

# .env 파일 로드
from dotenv import load_dotenv
load_dotenv()

def check_environment():
    """환경 설정 확인"""
    print("🔧 환경 설정 확인:")
    
    # OpenAI API 키
    api_key = os.getenv('OPENAI_API_KEY')
    if api_key:
        print(f"  OpenAI API 키: ✅ 설정됨")
    else:
        print(f"  OpenAI API 키: ❌ 설정되지 않음")
        return False
    
    # LLM 모델
    model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
    print(f"  LLM 모델: {model}")
    
    # 데이터 경로
    data_path = os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
    print(f"  데이터 경로: {data_path}")
    
    # 로그 레벨
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    print(f"  로그 레벨: {log_level}")
    
    # 최대 질문 수
    max_questions = os.getenv('MAX_QUESTIONS', '1000')
    print(f"  최대 질문 수: {max_questions}")
    
    return True

def show_usage_info():
    """사용법 정보 표시"""
    print("""
📚 대량 딥페이크 학생 질문 생성기

🎯 목표:
- 20개씩 학생 질문 예시를 보내서 30개씩 답변 생성
- 20번 반복하여 총 600개 질문 생성
- 수열, 수학적 귀납법 관련 단원에 집중

📋 대상 단원:
1. 수열: 등차수열, 등비수열, 수열의 합, 시그마, 일반항, 공차, 공비
2. 수학적 귀납법: 귀납법, 점화식, 재귀, 귀납가정, 귀납단계
3. 수열의 합: 등차수열의 합, 등비수열의 합, 시그마 공식, 무한급수

⚙️ 환경 설정 (.env 파일):
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-5-mini
DATA_PATH=data/evaluation_statistics.json
LOG_LEVEL=INFO
MAX_QUESTIONS=1000

📁 출력 파일:
- mass_generation_results_YYYYMMDD_HHMMSS.json (전체 결과)
- current_iteration_N.json (각 반복 결과)
- mass_generation.log (상세 로그)
""")

async def run_mass_generation():
    """대량 데이터 생성 실행"""
    try:
        from mass_question_generator import MassQuestionGenerator
        
        print("🚀 대량 데이터 생성 시작...")
        
        # 생성기 초기화
        generator = MassQuestionGenerator()
        
        # 통계 출력
        stats = generator.get_statistics()
        print("\n📊 시스템 통계:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
        
        # 대량 데이터 생성
        print("\n🔄 대량 데이터 생성 중...")
        results = await generator.generate_mass_data(20)
        
        print("\n✅ 대량 데이터 생성 완료!")
        print(f"  총 생성된 데이터: {len(results)} 반복")
        
        # 최종 통계
        total_questions = 0
        for iteration, data in results.items():
            for unit, questions in data.items():
                total_questions += len(questions)
        
        print(f"  총 생성된 질문 수: {total_questions}개")
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        print("mass_question_generator.py 파일이 존재하는지 확인하세요.")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        raise

def main():
    """메인 함수"""
    print("🎭 대량 딥페이크식 학생 질문 생성기")
    print("=" * 50)
    
    # 환경 설정 확인
    if not check_environment():
        print("\n❌ 환경 설정이 올바르지 않습니다.")
        show_usage_info()
        return
    
    print("\n실행 옵션:")
    print("1. 대량 데이터 생성 시작")
    print("2. 사용법 보기")
    print("3. 종료")
    
    while True:
        try:
            choice = input("\n선택하세요 (1-3): ").strip()
            
            if choice == "1":
                print("\n🚀 대량 데이터 생성을 시작합니다...")
                print("⚠️  주의: 이 과정은 시간이 오래 걸리고 API 비용이 발생할 수 있습니다.")
                confirm = input("계속하시겠습니까? (y/N): ").strip().lower()
                
                if confirm in ['y', 'yes']:
                    asyncio.run(run_mass_generation())
                else:
                    print("취소되었습니다.")
                    
            elif choice == "2":
                show_usage_info()
                
            elif choice == "3":
                print("프로그램을 종료합니다.")
                break
                
            else:
                print("잘못된 선택입니다. 1-3 중에서 선택하세요.")
                
        except KeyboardInterrupt:
            print("\n\n⏹️ 사용자에 의해 중단되었습니다.")
            break
        except Exception as e:
            print(f"\n❌ 오류 발생: {e}")

if __name__ == "__main__":
    main()
