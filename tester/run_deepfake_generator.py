#!/usr/bin/env python3
"""
딥페이크 질문 생성기 실행 스크립트
"""

import os
import sys
import asyncio
from pathlib import Path

# .env 파일 로드
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ .env 파일 로드 완료")
except ImportError:
    print("⚠️ python-dotenv가 설치되지 않았습니다. pip install python-dotenv를 실행하세요.")
    print("환경변수를 직접 설정하거나 .env 파일을 사용할 수 없습니다.")

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

def check_environment():
    """환경 설정 확인"""
    print("🔧 환경 설정 확인:")
    
    # OpenAI API 키 확인
    api_key = os.getenv('OPENAI_API_KEY')
    print(f"  OpenAI API 키: {'✅ 설정됨' if api_key else '❌ 설정되지 않음'}")
    
    # LLM 모델 확인
    model = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
    print(f"  LLM 모델: {model}")
    
    # 데이터 경로 확인
    data_path = os.getenv('DATA_PATH', 'data/evaluation_statistics.json')
    print(f"  데이터 경로: {data_path}")
    
    # 로그 레벨 확인
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    print(f"  로그 레벨: {log_level}")
    
    # 최대 질문 수 확인
    max_questions = os.getenv('MAX_QUESTIONS', '1000')
    print(f"  최대 질문 수: {max_questions}")
    
    print()
    return api_key, model, data_path

async def run_llm_generator():
    """LLM 기반 딥페이크 생성기 실행"""
    try:
        from llm_deepfake_generator import LLMDeepfakeGenerator
        
        print("🚀 LLM 기반 딥페이크 질문 생성기 실행 중...\n")
        
        # 환경 설정 확인
        api_key, model, data_path = check_environment()
        
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
        
        # 다양한 주제로 딥페이크 질문 생성
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
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
        print("필요한 패키지를 설치하세요: pip install openai")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def run_basic_generator():
    """기본 딥페이크 생성기 실행"""
    try:
        from deepfake_question_generator import DeepfakeQuestionGenerator
        
        print("🚀 기본 딥페이크 질문 생성기 실행 중...\n")
        
        # 환경 설정 확인
        _, _, data_path = check_environment()
        
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
        
        print("\n✅ 기본 딥페이크 질문 생성 완료!")
        
    except ImportError as e:
        print(f"❌ 모듈 import 실패: {e}")
    except Exception as e:
        print(f"❌ 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

async def run_auto_test():
    """자동으로 300개 질문(30개 x 10회)을 생성하고 저장하는 함수"""
    print("🚀 자동 딥페이크 질문 생성 테스트 시작")
    print("=" * 60)
    
    try:
        # 필요한 모듈들 import
        from llm_deepfake_generator import LLMDeepfakeGenerator
        import json
        import random
        import os
        import re
        from datetime import datetime
        import asyncio
        
        # LLMDeepfakeGenerator 로드 (모델 명시: gpt-5-mini)
        model_env = os.getenv('OPENAI_MODEL', 'gpt-5-mini')
        generator = LLMDeepfakeGenerator(model=model_env)
        print("✅ LLMDeepfakeGenerator 로드 완료")
        
        # 1단계: 실제 질문에서 20개를 랜덤으로 선택
        print("🎯 1단계: 실제 질문에서 20개를 랜덤으로 선택 중...")
        print("-" * 50)
        
        real_questions = generator.real_questions
        if len(real_questions) < 20:
            print(f"❌ 실제 질문이 부족합니다. (현재: {len(real_questions)}개, 필요: 20개)")
            return
        
        # 20개 랜덤 선택 (문자열 리스트이므로 직접 사용)
        input_questions = random.sample(real_questions, 20)
        for i, q in enumerate(input_questions, 1):
            print(f"  {i:2d}. {q[:60]}...")
        print(f"✅ 20개 실제 질문 선택 완료\n")
        
        # 2단계: 선택된 질문을 기반으로 300개 변형 질문을 배치(30개 x 10회)로 생성
        print("🎯 2단계: 선택된 질문을 기반으로 300개 변형 질문을 배치(30개 x 10회)로 생성 중...")
        print("-" * 50)
        
        # 수학 주제들
        math_topics = ['수열', '점화식', '귀납법', '수열의합', '등차수열', '등비수열', '수학적귀납법', '조합론']
        
        # 300개 질문을 30개씩 10번에 나누어 생성
        batch_size = 30
        total_batches = 10
        all_output_questions = []
        next_global_id = 1
        
        for batch_num in range(total_batches):
            print(f"📦 배치 {batch_num + 1}/{total_batches} 처리 중...")
            
            # 현재 배치용 프롬프트 생성
            batch_prompts = []
            for i in range(batch_size):
                batch_idx = batch_num * batch_size + i
                input_idx = batch_idx % len(input_questions)
                input_q = input_questions[input_idx]
                target_topic = random.choice(math_topics)
                
                batch_prompts.append({
                    'id': next_global_id + i,
                    'input_id': input_idx + 1,
                    'original_question': input_q,
                    'target_topic': target_topic
                })
            
            # 배치용 JSON 프롬프트 생성 (설명 없이 JSON만 반환 지시)
            combined_prompt = json.dumps({
                "request_type": "batch_question_generation",
                "num_outputs": batch_size,
                "topics": math_topics,
                "input_questions_context": input_questions,
                "output_contract": {
                    "type": "object",
                    "properties": {
                        "generated_questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "id": {"type": "integer"},
                                    "target_topic": {"type": "string"},
                                    "new_question": {"type": "string"}
                                },
                                "required": ["id", "target_topic", "new_question"]
                            }
                        }
                    },
                    "required": ["generated_questions"]
                },
                "instructions": "입력된 20개 질문은 한 반 학생들이 실제로 한 질문들입니다. 이 학생들의 질문 스타일, 어조, 패턴을 학습해서 완전히 새로운 30개 질문을 생성하세요. 기존 질문을 변형하는 게 아니라, 같은 반 학생이 물어볼 법한 새로운 질문을 만드세요. 수학 주제는 topics 리스트에서 선택하고, 고등학교 수준에 맞게 하세요. 오직 하나의 JSON 객체만 반환하세요."
            }, ensure_ascii=False, indent=2)
            
            try:
                print(f"🚀 GPT-5-mini에 {batch_size}개 질문(JSON)을 전송 중...")
                
                response = await generator.openai_client.chat.completions.create(
                    model=generator.model,
                    messages=[
                        {"role": "system", "content": "너는 JSON만 반환하는 생성 에이전트다. 설명이나 자연어 금지. 오직 하나의 JSON 객체만 출력."},
                        {"role": "user", "content": combined_prompt}
                    ],
                    max_completion_tokens=10000
                )
                
                # 응답을 파싱하여 질문 추출
                response_text = response.choices[0].message.content.strip()
                print(f"📝 GPT 응답 받음 (길이: {len(response_text)}자)")
                
                # JSON 강건 파싱: 바로 파싱 실패 시 응답에서 JSON 객체만 추출
                def robust_parse_json(text: str):
                    try:
                        return json.loads(text)
                    except Exception:
                        pass
                    m = re.search(r"\{[\s\S]*\}", text)
                    if m:
                        try:
                            return json.loads(m.group(0))
                        except Exception:
                            return {}
                    return {}
                
                response_data = robust_parse_json(response_text)
                batch_output_questions = []
                
                # 'generated_questions' 우선 사용, 없으면 'outputs' 등 대체 키 시도
                generated_list = response_data.get('generated_questions')
                if not isinstance(generated_list, list):
                    generated_list = response_data.get('outputs')
                if not isinstance(generated_list, list):
                    generated_list = []
                
                # id 매핑이 있으면 활용, 없으면 순서대로 매핑
                generated_map = {}
                for item in generated_list:
                    if isinstance(item, dict) and 'id' in item:
                        generated_map[item['id']] = item
                
                for i, spec in enumerate(batch_prompts):
                    # id 기반 우선, 없으면 순서 기반
                    generated_q = generated_map.get(spec['id'])
                    if not generated_q and i < len(generated_list) and isinstance(generated_list[i], dict):
                        generated_q = generated_list[i]
                    new_question_text = generated_q.get('new_question') if isinstance(generated_q, dict) else ""
                    target_topic = generated_q.get('target_topic') if isinstance(generated_q, dict) and generated_q.get('target_topic') else spec['target_topic']
                    
                    batch_output_questions.append({
                        'id': spec['id'],
                        'input_id': spec['input_id'],
                        'original_question': spec['original_question'],
                        'target_topic': target_topic,
                        'new_question': new_question_text if new_question_text else f"[생성 실패] {spec['original_question']}",
                        'timestamp': datetime.now().isoformat()
                    })
                
                # 현재 배치 결과 출력 (처음 5개 미리보기)
                for preview in batch_output_questions[:5]:
                    print(f"  {preview['id']:3d}. [{preview['target_topic']}] {preview['new_question'][:50]}...")
                if len(batch_output_questions) > 5:
                    print(f"  ... 외 {len(batch_output_questions) - 5}개")
                
                all_output_questions.extend(batch_output_questions)
                next_global_id += batch_size
                print(f"✅ 배치 {batch_num + 1} 완료 ({len(batch_output_questions)}개)")
                
                # API 제한 고려하여 잠시 대기
                if batch_num < total_batches - 1:
                    print("⏳ 다음 배치 준비 중... (2초 대기)")
                    await asyncio.sleep(2)
                
            except Exception as e:
                print(f"❌ 배치 {batch_num + 1} 처리 중 오류: {e}")
                # 실패한 배치에 대해 기본 질문 생성
                for spec in batch_prompts:
                    all_output_questions.append({
                        'id': spec['id'],
                        'input_id': spec['input_id'],
                        'original_question': spec['original_question'],
                        'target_topic': spec['target_topic'],
                        'new_question': f"[배치 {batch_num + 1} 생성 실패] {spec['original_question']}",
                        'timestamp': datetime.now().isoformat()
                    })
                next_global_id += batch_size
        
        print(f"✅ 300개 변형 질문 생성 완료 (실제 생성: {len(all_output_questions)}개)\n")
        
        # 3단계: 결과를 파일로 저장
        print("🎯 3단계: 결과를 파일로 저장 중...")
        print("-" * 50)
        
        # 출력 디렉토리 생성 (tester 디렉토리 안에)
        output_dir = 'output'
        os.makedirs(output_dir, exist_ok=True)
        
        # 결과 데이터 구성
        result_data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'model': generator.model,
                'input_count': len(input_questions),
                'output_count': len(all_output_questions),
                'batch_size': batch_size,
                'total_batches': total_batches
            },
            'input_questions': input_questions,
            'output_questions': all_output_questions
        }
        
        # 파일명 생성 (타임스탬프 포함)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'{output_dir}/deepfake_test_results_{timestamp}.json'
        
        # JSON 파일로 저장
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 결과가 '{filename}'에 저장되었습니다.")
        print(f"📊 생성된 질문 수: {len(all_output_questions)}개")
        print(f"📁 파일 크기: {os.path.getsize(filename) / 1024:.1f} KB")
        
        # 품질 통계 출력
        print("\n📈 품질 통계:")
        topic_counts = {}
        success_count = 0
        for q in all_output_questions:
            topic = q['target_topic']
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
            if not q['new_question'].startswith('[생성 실패]') and not q['new_question'].startswith('[배치'):
                success_count += 1
        
        print(f"  성공률: {success_count}/{len(all_output_questions)} ({success_count/len(all_output_questions)*100:.1f}%)")
        print("  주제별 분포:")
        for topic, count in sorted(topic_counts.items()):
            print(f"    {topic}: {count}개")
        
    except Exception as e:
        print(f"❌ 테스트 실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

def show_environment_help():
    """환경 설정 도움말 표시"""
    print("\n📖 환경 설정 도움말")
    print("="*40)
    print("1. .env 파일 생성:")
    print("   tester 폴더에 .env 파일을 만들고 다음 내용을 추가하세요:")
    print()
    print("   OPENAI_API_KEY=your-openai-api-key-here")
    print("   OPENAI_MODEL=gpt-5-mini")
    print("   DATA_PATH=data/evaluation_statistics.json")
    print("   LOG_LEVEL=INFO")
    print("   MAX_QUESTIONS=1000")
    print()
    print("2. 환경변수 직접 설정:")
    print("   export OPENAI_API_KEY='your-api-key'")
    print("   export OPENAI_MODEL='gpt-5-mini'")
    print()
    print("3. 필요한 패키지 설치:")
    print("   pip install -r requirements.txt")
    print()

def main():
    """메인 실행 함수 - 자동화된 테스트 실행"""
    print("🎭 딥페이크식 학생 질문 생성기 (자동화 모드)\n")
    
    # 환경 설정 확인
    api_key, _, _ = check_environment()
    
    if not api_key:
        print("❌ OpenAI API 키가 설정되지 않았습니다.")
        print("자동화 테스트를 실행하려면 API 키를 설정해야 합니다.")
        print("다음 방법 중 하나로 설정하세요:")
        print("1. .env 파일에 OPENAI_API_KEY=your-api-key 추가")
        print("2. export OPENAI_API_KEY='your-api-key' 실행")
        return
    
    print("🚀 자동화된 딥페이크 테스트를 시작합니다...")
    print("📋 실제 학생 질문 20개 → 변형 질문 30개 → JSON 파일 저장")
    print("="*60)
    
    try:
        # 자동화된 테스트 실행
        asyncio.run(run_auto_test())
    except KeyboardInterrupt:
        print("\n\n⏹️ 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
