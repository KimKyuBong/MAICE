-- llm_response_logs 테이블에 agent_name 컬럼 추가 (원격 서버용)
-- 이 스크립트는 원격 서버에서 agent_name 컬럼이 누락된 경우 실행

-- 1. agent_name 컬럼이 존재하는지 확인
DO $$
BEGIN
    -- agent_name 컬럼이 없으면 추가
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'llm_response_logs' 
        AND column_name = 'agent_name'
    ) THEN
        ALTER TABLE llm_response_logs 
        ADD COLUMN agent_name VARCHAR(100);
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_llm_response_logs_agent_name 
        ON llm_response_logs(agent_name);
        
        RAISE NOTICE 'agent_name 컬럼과 인덱스가 성공적으로 추가되었습니다.';
    ELSE
        RAISE NOTICE 'agent_name 컬럼이 이미 존재합니다.';
    END IF;
END $$;

-- 2. llm_prompt_logs 테이블에도 agent_name 컬럼이 있는지 확인
DO $$
BEGIN
    -- agent_name 컬럼이 없으면 추가
    IF NOT EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'llm_prompt_logs' 
        AND column_name = 'agent_name'
    ) THEN
        ALTER TABLE llm_prompt_logs 
        ADD COLUMN agent_name VARCHAR(100);
        
        -- 인덱스 추가
        CREATE INDEX IF NOT EXISTS idx_llm_prompt_logs_agent_name 
        ON llm_prompt_logs(agent_name);
        
        RAISE NOTICE 'llm_prompt_logs에 agent_name 컬럼과 인덱스가 성공적으로 추가되었습니다.';
    ELSE
        RAISE NOTICE 'llm_prompt_logs에 agent_name 컬럼이 이미 존재합니다.';
    END IF;
END $$;

-- 3. 테이블 구조 확인
SELECT 
    table_name,
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name IN ('llm_response_logs', 'llm_prompt_logs')
ORDER BY table_name, ordinal_position;
