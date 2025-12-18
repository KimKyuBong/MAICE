-- 중복 메시지 정리 스크립트
-- 실행 전 백업 권장: pg_dump -h 192.168.1.105 -U postgres maice_web > backup_before_cleanup.sql

-- 1. 중복 메시지 현황 확인
SELECT 
    conversation_session_id,
    sender,
    message_type,
    COUNT(*) as total_messages,
    COUNT(DISTINCT content) as unique_content_count,
    COUNT(*) - COUNT(DISTINCT content) as duplicate_count
FROM session_messages 
WHERE sender = 'maice'
GROUP BY conversation_session_id, sender, message_type
HAVING COUNT(*) > COUNT(DISTINCT content)
ORDER BY duplicate_count DESC;

-- 2. 중복 메시지 상세 조회
SELECT 
    conversation_session_id,
    content,
    message_type,
    COUNT(*) as duplicate_count,
    MIN(id) as keep_id,
    MAX(id) as latest_id,
    MIN(created_at) as first_created,
    MAX(created_at) as last_created
FROM session_messages 
WHERE sender = 'maice' 
GROUP BY conversation_session_id, content, message_type
HAVING COUNT(*) > 1
ORDER BY conversation_session_id DESC, duplicate_count DESC;

-- 3. 중복 메시지 삭제 (가장 최근 것만 유지)
-- 주의: 실제 실행하기 전에 위의 SELECT 문으로 확인하세요!
DELETE FROM session_messages 
WHERE id NOT IN (
    SELECT MAX(id) 
    FROM session_messages 
    GROUP BY conversation_session_id, content, message_type, sender
);

-- 4. 정리 후 확인
SELECT 
    COUNT(*) as total_messages,
    COUNT(CASE WHEN sender = 'maice' THEN 1 END) as maice_messages,
    COUNT(CASE WHEN sender = 'user' THEN 1 END) as user_messages
FROM session_messages;

-- 5. 최근 세션들의 메시지 개수 확인
SELECT 
    sm.conversation_session_id,
    COUNT(*) as message_count,
    MAX(sm.created_at) as last_message_time
FROM session_messages sm
WHERE sm.created_at > CURRENT_DATE - INTERVAL '7 days'
GROUP BY sm.conversation_session_id
ORDER BY last_message_time DESC
LIMIT 10;
