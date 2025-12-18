#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 전 상태 확인 스크립트
"""

import asyncio
import asyncpg
import os
import sys
from urllib.parse import urlparse

async def check_database_state():
    """데이터베이스 상태를 확인하고 마이그레이션 필요성을 판단합니다."""
    try:
        db_url = os.getenv('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/maice_web')
        parsed = urlparse(db_url)
        
        print("🔍 데이터베이스 연결 시도 중...")
        conn = await asyncpg.connect(
            host=parsed.hostname or 'localhost',
            port=parsed.port or 5432,
            user=parsed.username or 'postgres',
            password=parsed.password or 'postgres',
            database=parsed.path[1:] if parsed.path else 'maice_web'
        )
        
        print("✅ 데이터베이스 연결 성공")
        
        # 테이블 존재 여부 확인
        tables_to_check = [
            'conversation_sessions',
            'session_messages',
            'session_summaries'
        ]
        
        missing_tables = []
        for table in tables_to_check:
            exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = $1
                );
            """, table)
            
            if not exists:
                missing_tables.append(table)
                print(f"❌ 테이블 누락: {table}")
            else:
                print(f"✅ 테이블 존재: {table}")
        
        # conversation_sessions 테이블의 컬럼 확인
        if 'conversation_sessions' not in missing_tables:
            columns = await conn.fetch("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'conversation_sessions'
            """)
            
            existing_columns = [row['column_name'] for row in columns]
            required_columns = [
                'conversation_summary',
                'learning_context',
                'last_summary_at'
            ]
            
            missing_columns = [col for col in required_columns if col not in existing_columns]
            
            if missing_columns:
                print(f"❌ conversation_sessions 테이블에서 누락된 컬럼: {missing_columns}")
                return False
            else:
                print("✅ conversation_sessions 테이블의 모든 필수 컬럼이 존재합니다")
        
        await conn.close()
        
        if missing_tables:
            print(f"❌ 누락된 테이블: {missing_tables}")
            print("🔄 마이그레이션이 필요합니다")
            return False
        
        print("✅ 모든 테이블과 컬럼이 존재합니다")
        return True
        
    except Exception as e:
        print(f"❌ 데이터베이스 상태 확인 실패: {e}")
        return False

async def main():
    """메인 함수"""
    print("🔍 데이터베이스 마이그레이션 상태 확인 시작...")
    
    needs_migration = not await check_database_state()
    
    if needs_migration:
        print("🔄 마이그레이션이 필요합니다")
        sys.exit(1)  # 마이그레이션 필요
    else:
        print("✅ 마이그레이션이 필요하지 않습니다")
        sys.exit(0)  # 마이그레이션 불필요

if __name__ == "__main__":
    asyncio.run(main())
