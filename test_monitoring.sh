#!/bin/bash

# MAICE 모니터링 테스트 스크립트

echo "========================================="
echo "MAICE 모니터링 시스템 테스트"
echo "========================================="

# 1. Redis 메트릭 키 확인
echo ""
echo "1. Redis 메트릭 키 확인"
echo "-----------------------------------------"
docker-compose exec -T redis redis-cli KEYS "maice:metrics:*" | head -20

# 2. 에이전트 상태 키 확인
echo ""
echo "2. 에이전트 상태 키 확인"
echo "-----------------------------------------"
docker-compose exec -T redis redis-cli KEYS "maice:agent_status:*"

# 3. QuestionClassifier 메트릭 확인
echo ""
echo "3. QuestionClassifier 메트릭 확인"
echo "-----------------------------------------"
docker-compose exec -T redis redis-cli GET "maice:metrics:QuestionClassifier:counter:classification_requests_total"
docker-compose exec -T redis redis-cli GET "maice:metrics:QuestionClassifier:counter:classification_success_total"

# 4. AnswerGenerator 메트릭 확인
echo ""
echo "4. AnswerGenerator 메트릭 확인"
echo "-----------------------------------------"
docker-compose exec -T redis redis-cli GET "maice:metrics:AnswerGenerator:counter:answer_requests_total"
docker-compose exec -T redis redis-cli GET "maice:metrics:AnswerGenerator:counter:answer_success_total"

# 5. 모니터링 API 테스트 (관리자 토큰 필요)
echo ""
echo "5. 모니터링 API 엔드포인트 확인"
echo "-----------------------------------------"
echo "다음 엔드포인트들이 사용 가능합니다:"
echo "  - GET /api/monitoring/agents/status"
echo "  - GET /api/monitoring/agents/{agent_name}/metrics"
echo "  - GET /api/monitoring/metrics/summary"
echo "  - GET /api/monitoring/processing-logs/{session_id}"
echo "  - GET /api/monitoring/processing-summary"
echo "  - GET /api/monitoring/health/detailed"
echo ""
echo "테스트하려면 관리자 계정으로 로그인 후 Bearer 토큰을 사용하세요."

echo ""
echo "========================================="
echo "테스트 완료"
echo "========================================="


