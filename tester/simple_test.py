#!/usr/bin/env python3
"""
간단한 Redis 메시지 발행 테스트 - QuestionImprovementAgent 로직에 맞춤
"""

import redis
import json
import asyncio
from datetime import datetime
from agent.agents.common.event_bus import (
    CLARIFICATION_REQUESTED,
    CLARIFICATION_QUESTION,      # 전용 채널 사용
    CLARIFICATION_COMPLETED,
    ANSWER_REQUESTED,
    ANSWER_COMPLETED,
    USER_CLARIFICATION
)

# 채널명 상수 정의 (event_bus.py와 일치)
USER_QUESTION = "user.question"

async def interactive_test():
    """전체 워크플로우를 직접 진행하는 인터랙티브 테스트"""
    try:
        # Redis 연결
        client = redis.Redis(host='localhost', port=6379, db=0)
        print("✅ Redis 연결 성공")
        
        # Redis 채널 구독
        pubsub = client.pubsub()
        pubsub.subscribe(
            CLARIFICATION_QUESTION,      # 명료화 질문 전용 채널
            CLARIFICATION_REQUESTED,
            CLARIFICATION_COMPLETED,
            ANSWER_REQUESTED,
            ANSWER_COMPLETED
        )
        
        print(f"📡 구독 채널: {ANSWER_COMPLETED}")
        
        # 구독 상태 확인
        print("🔍 구독 상태 확인 중...")
        # 잠시 대기해서 구독이 확실히 설정되도록 함
        import time
        time.sleep(1)
        print("✅ 구독 설정 완료")
        
        while True:
            # 사용자 입력 받기
            print("\n" + "="*50)
            question = input("질문을 입력하세요 (종료하려면 'quit' 입력): ").strip()
            
            if question.lower() == 'quit':
                print("👋 테스트 종료")
                break
                
            if not question:
                print("❌ 질문을 입력해주세요")
                continue
            
            print(f"📝 입력된 질문: '{question}'")
            
            # 질문 제출
            question_payload = {
                "request_id": f"test_{datetime.now().strftime('%H%M%S')}",
                "question": question,  # 에이전트가 기대하는 필드명
                "context": "",
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📝 질문 제출 중... ID: {question_payload['request_id']}")
            
            # user.question 이벤트 발행 (사용자 → QuestionClassifierAgent)
            json_data = json.dumps(question_payload, ensure_ascii=False)
            print(f"📤 Redis로 전송할 데이터: {json_data}")
            print(f"📤 Redis로 전송할 데이터 길이: {len(json_data)}")
            print(f"📤 Redis로 전송할 데이터 바이트: {json_data.encode('utf-8')}")
            
            result = client.publish(USER_QUESTION, json_data)
            print(f"✅ user.question 이벤트 발행 완료 (Redis 결과: {result})")
            
            # 전체 워크플로우 모니터링 시작
            print("🔍 워크플로우 모니터링 시작...")
            
            # 관련 채널들 구독 (에이전트가 구독하는 채널들)
            pubsub.subscribe(
                CLARIFICATION_QUESTION,    # 명료화 질문 전용 채널
                CLARIFICATION_REQUESTED,   # 명료화 요청 이벤트
                CLARIFICATION_COMPLETED,   # 명료화 완료 이벤트
                ANSWER_REQUESTED,          # 답변 요청 이벤트
                ANSWER_COMPLETED           # 답변 완료 이벤트
            )
            
            # 이벤트 수신 대기 (최대 120초 - 답변 생성에 시간이 걸릴 수 있음)
            timeout = 120
            start_time = datetime.now()
            current_request_id = question_payload["request_id"]
            clarification_session = None
            clarification_completed = False  # 명료화 완료 여부 추적
            
            while (datetime.now() - start_time).seconds < timeout:
                try:
                    message = pubsub.get_message(timeout=1.0)
                    
                    if message and message["type"] == "message":
                        channel = message["channel"].decode("utf-8")
                        data = json.loads(message["data"].decode("utf-8"))
                        
                        # 디버깅: 모든 수신된 이벤트 로깅
                        print(f"🔍 디버그: 채널={channel}, request_id={data.get('request_id')}")
                        
                        # 현재 질문과 관련된 이벤트만 처리
                        if data.get('request_id') != current_request_id:
                            print(f"   ⏭️ 다른 세션 이벤트 스킵: {data.get('request_id')} != {current_request_id}")
                            continue
                        
                        print(f"\n📨 {channel} 이벤트 수신:")
                        print(f"   Request ID: {data.get('request_id', 'N/A')}")
                        
                        if channel == CLARIFICATION_QUESTION:  # 전용 채널 사용
                            print(f"   ❓ 명료화 질문 수신!")
                            print(f"   📝 질문: {data.get('question', 'N/A')}")
                            print(f"   🎯 명료화 필드: {data.get('field', 'N/A')}")  # 에이전트가 사용하는 필드명
                            print(f"   📊 진행률: {data.get('completed_fields', 0)}/{data.get('total_fields', 0)}")
                            
                            # 단계별 명료화 진행
                            clarification_session = {
                                "request_id": data.get('request_id', ''),
                                "clarification_field": data.get('field', ''),  # 에이전트가 사용하는 필드명
                                "clarification_question": data.get('question', ''),
                                "total_fields": data.get('total_fields', 0),
                                "responses": {}
                            }
                            
                            await process_clarification_step(client, clarification_session)
                            
                        elif channel == CLARIFICATION_REQUESTED:
                            print(f"   🔍 명료화 요청됨!")
                            print(f"   📝 질문: {data.get('question', 'N/A')}")
                            print(f"   📋 부족한 필드: {data.get('missing_fields', [])}")
                            print(f"   📚 단원 태그: {data.get('unit_tags', [])}")
                            
                            # clarify_questions가 있으면 표시
                            clarify_questions = data.get('clarification_questions', [])
                            if clarify_questions:
                                print(f"   💡 생성된 명료화 질문들:")
                                for i, q in enumerate(clarify_questions):
                                    print(f"      {i+1}. {q}")
                            
                        elif channel == CLARIFICATION_COMPLETED:
                            print(f"   ✅ 명료화 완료!")
                            clarification_completed = True
                            print(f"   ✅ 명료화 완료! 이제 답변 생성을 기다립니다...")
                            # 명료화 완료 후에도 계속 대기 (ANSWER_REQUESTED와 ANSWER_COMPLETED를 기다림)
                            continue
                            
                        elif channel == ANSWER_REQUESTED:
                            print(f"   🎯 답변 생성 요청됨!")
                            print(f"   📝 질문: {data.get('question', 'N/A')}")
                            
                            # clarification_responses가 있는지 확인
                            clarification_responses = data.get('clarification_responses', {})
                            if clarification_responses:
                                print(f"   📋 명료화 응답 수: {len(clarification_responses)}개")
                                for field, response in clarification_responses.items():
                                    print(f"      - {field}: {response[:50]}...")
                            
                            # classification 정보 표시
                            classification = data.get('classification', {})
                            if classification:
                                print(f"   🏷️  분류: {classification.get('quality', 'N/A')}")
                                print(f"   📚 단원: {classification.get('unit_tags', [])}")
                            
                            print(f"   ⏳ AI가 교육적 답변을 생성하고 있습니다...")
                            # ANSWER_COMPLETED를 기다리기 위해 계속 대기
                            continue
                            
                        elif channel == ANSWER_COMPLETED:
                            # 답변 완료 처리
                            print(f"   🎉 교육적 답변 완료!")
                            answer_content = data.get('answer', '')
                            print(f"   📝 답변 길이: {len(answer_content)} 문자")
                            print(f"\n" + "="*80)
                            print("📖 생성된 교육적 답변:")
                            print("="*80)
                            print(answer_content)
                            print("="*80)
                            
                            # 답변 완료되면 항상 종료
                            print(f"\n✅ 워크플로우 완료! 답변이 성공적으로 생성되었습니다.")
                            break
                            
                except Exception as e:
                    print(f"   ❌ 메시지 처리 오류: {e}")
            
            # 구독 해제
            pubsub.unsubscribe(
                CLARIFICATION_REQUESTED,
                CLARIFICATION_COMPLETED,
                ANSWER_REQUESTED,
                ANSWER_COMPLETED
            )
            pubsub.close()
            
            # 타임아웃 처리
            elapsed_time = (datetime.now() - start_time).seconds
            if elapsed_time >= timeout:
                print(f"\n⏰ 타임아웃 ({timeout}초)")
                print(f"   ❌ ANSWER_COMPLETED 이벤트를 받지 못했습니다.")
                print(f"   📊 상태: 명료화 완료={clarification_completed}")
                print(f"   🔍 에이전트 로그를 확인해보세요: docker logs miniserver-agent-1")
            
            print(f"\n⏳ 다음 질문을 입력하거나 'quit'으로 종료하세요")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        client.close()

async def process_clarification_step(client, session):
    """단일 명료화 단계 진행"""
    clarification_field = session["clarification_field"]  # 에이전트가 사용하는 필드명
    clarification_question = session["clarification_question"]
    
    print(f"   🔗 명료화 단계 진행:")
    print(f"      명료화 필드: {clarification_field}")
    print(f"      명료화 질문: {clarification_question}")
    
    # 사용자 입력 받기
    user_response = input("   답변을 입력하세요 (또는 'skip' 입력하여 다음 단계로 넘어가기): ").strip()
    
    if user_response.lower() == 'skip':
        print(f"   ⏭️ 현재 질문을 건너뛰고 다음 단계로 이동합니다.")
        return
        
    if not user_response:
        print("   ❌ 답변을 입력해주세요")
        return
    
    # 사용자 답변 표시
    print(f"   💬 사용자 답변: {user_response}")
        
    # 답변 저장
    session["responses"][clarification_field] = user_response
    print(f"   ✅ 답변 저장: {clarification_field}")
    
    # user.clarification으로 명료화 답변 전송 (에이전트가 기대하는 형식)
    clarification_response = {
        "request_id": session["request_id"],
        "message": user_response,  # 에이전트가 기대하는 파라미터명
        "field": clarification_field,  # 필드명도 함께 전송
        "timestamp": datetime.now().isoformat()
    }
    
    print(f"   📤 전송 시작: user.clarification 채널로...")
    print(f"      전송 데이터: {clarification_response}")
    
    # Redis로 전송
    result = client.publish(USER_CLARIFICATION, 
                 json.dumps(clarification_response, ensure_ascii=False))
    
    print(f"      ✅ user.clarification으로 전송 완료 (Redis 결과: {result})")
    print(f"      📝 전송된 채널: user.clarification")
    print(f"      📝 전송된 데이터: {json.dumps(clarification_response, ensure_ascii=False)}")
    
    # 즉시 다음 단계로 진행 (불필요한 대기 제거)
    print(f"   ➡️ 다음 질문으로 진행...")

if __name__ == "__main__":
    asyncio.run(interactive_test())
