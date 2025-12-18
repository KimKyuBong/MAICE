-- 중복 방지를 위한 데이터베이스 제약조건 추가
-- 실행 전 중복 데이터 정리 필수!

-- 1. 기존 중복 데이터가 있는지 확인
SELECT 
    conversation_session_id,
    content,
    message_type,
    sender,
    COUNT(*) as count
FROM session_messages 
GROUP BY conversation_session_id, content, message_type, sender
HAVING COUNT(*) > 1
ORDER BY count DESC;

-- 2. 중복 방지 인덱스 추가 (부분 인덱스 - MAICE 메시지만)
-- 같은 세션, 같은 내용, 같은 타입의 MAICE 메시지는 중복 방지
CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_unique_maice_messages
ON session_messages (conversation_session_id, content, message_type)
WHERE sender = 'maice';

-- 3. 짧은 시간 내 중복 방지를 위한 부분 인덱스
-- 같은 세션, 같은 타입, 최근 1시간 내에서 중복 방지
-- 주의: 이 인덱스는 PostgreSQL 버전과 설정에 따라 작동하지 않을 수 있습니다.
-- CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS idx_prevent_recent_duplicates
-- ON session_messages (conversation_session_id, message_type, sender, date_trunc('hour', created_at))
-- WHERE sender = 'maice';

-- 4. 인덱스 생성 확인
SELECT 
    indexname, 
    indexdef
FROM pg_indexes 
WHERE tablename = 'session_messages' 
    AND indexname LIKE '%unique%';

-- 5. 제약조건이 제대로 작동하는지 테스트 (실제 운영에서는 실행하지 마세요)
-- INSERT INTO session_messages (conversation_session_id, user_id, sender, content, message_type, created_at, updated_at)
-- VALUES (999, 1, 'maice', 'test duplicate', 'maice_answer', NOW(), NOW());
-- 
-- INSERT INTO session_messages (conversation_session_id, user_id, sender, content, message_type, created_at, updated_at)
-- VALUES (999, 1, 'maice', 'test duplicate', 'maice_answer', NOW(), NOW());
-- 
-- -- 위 두 번째 INSERT는 실패해야 합니다.
