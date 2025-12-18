#!/usr/bin/env python3
"""
테스트 계정 생성 스크립트
에이전트 모드와 프리패스 모드 테스트를 위한 20개 테스트 계정 생성
"""

import asyncio
import sys
import os
from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.models import UserModel
from app.core.config import Settings

async def create_test_users():
    """20개의 테스트 계정 생성 (에이전트 10개, 프리패스 10개)"""
    
    # 데이터베이스 연결 설정
    settings = Settings()
    # postgresql:// -> postgresql+asyncpg:// 변환
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("🚀 테스트 계정 생성 시작...")
            
            # 기존 테스트 계정 삭제 (선택사항)
            await session.execute(text("DELETE FROM users WHERE google_email LIKE '%test@example.com'"))
            await session.commit()
            print("✅ 기존 테스트 계정 삭제 완료")
            
            # 테스트 계정 데이터
            test_users = []
            
            # 에이전트 모드 테스트 계정 (10개)
            for i in range(1, 11):
                test_users.append({
                    "google_id": f"test_agent_{i:03d}",
                    "google_email": f"agent{i:03d}.test@example.com",
                    "google_name": f"에이전트테스터{i:03d}",
                    "assigned_mode": "agent",
                    "mode_assigned_at": datetime.utcnow()
                })
            
            # 프리패스 모드 테스트 계정 (10개)
            for i in range(1, 11):
                test_users.append({
                    "google_id": f"test_freepass_{i:03d}",
                    "google_email": f"freepass{i:03d}.test@example.com",
                    "google_name": f"프리패스테스터{i:03d}",
                    "assigned_mode": "freepass",
                    "mode_assigned_at": datetime.utcnow()
                })
            
            # 사용자 생성
            created_count = 0
            for user_data in test_users:
                user = UserModel(
                    google_id=user_data["google_id"],
                    google_email=user_data["google_email"],
                    google_name=user_data["google_name"],
                    assigned_mode=user_data["assigned_mode"],
                    mode_assigned_at=user_data["mode_assigned_at"],
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(user)
                created_count += 1
            
            await session.commit()
            
            print(f"✅ 테스트 계정 생성 완료: {created_count}개")
            print(f"   - 에이전트 모드: 10개 (agent001.test@example.com ~ agent010.test@example.com)")
            print(f"   - 프리패스 모드: 10개 (freepass001.test@example.com ~ freepass010.test@example.com)")
            
            # 생성된 계정 확인
            result = await session.execute(text("""
                SELECT assigned_mode, COUNT(*) as count 
                FROM users 
                WHERE google_email LIKE '%test@example.com' 
                GROUP BY assigned_mode
            """))
            
            print("\n📊 생성된 테스트 계정 현황:")
            for row in result:
                mode = row[0]
                count = row[1]
                print(f"   - {mode} 모드: {count}개")
                
        except Exception as e:
            await session.rollback()
            print(f"❌ 테스트 계정 생성 실패: {e}")
            raise
        finally:
            await session.close()
            await engine.dispose()

async def list_test_users():
    """생성된 테스트 계정 목록 조회"""
    
    settings = Settings()
    # postgresql:// -> postgresql+asyncpg:// 변환
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            result = await session.execute(text("""
                SELECT id, google_email, google_name, assigned_mode, created_at
                FROM users 
                WHERE google_email LIKE '%test@example.com' 
                ORDER BY assigned_mode, google_email
            """))
            
            users = result.fetchall()
            
            if not users:
                print("❌ 테스트 계정이 없습니다.")
                return
            
            print(f"📋 테스트 계정 목록 ({len(users)}개):")
            print("-" * 80)
            
            current_mode = None
            for user in users:
                if user[3] != current_mode:
                    current_mode = user[3]
                    print(f"\n🔹 {current_mode.upper()} 모드:")
                
                print(f"   ID: {user[0]:2d} | {user[1]:25s} | {user[2]:15s} | {user[4].strftime('%m-%d %H:%M')}")
                
        except Exception as e:
            print(f"❌ 테스트 계정 목록 조회 실패: {e}")
        finally:
            await session.close()
            await engine.dispose()

async def delete_test_users():
    """모든 테스트 계정 삭제"""
    
    settings = Settings()
    # postgresql:// -> postgresql+asyncpg:// 변환
    database_url = settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            result = await session.execute(text("DELETE FROM users WHERE google_email LIKE '%test@example.com'"))
            deleted_count = result.rowcount
            await session.commit()
            
            print(f"✅ 테스트 계정 삭제 완료: {deleted_count}개")
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 테스트 계정 삭제 실패: {e}")
            raise
        finally:
            await session.close()
            await engine.dispose()

async def main():
    """메인 함수"""
    if len(sys.argv) < 2:
        print("사용법:")
        print("  python create_test_users.py create  # 테스트 계정 생성")
        print("  python create_test_users.py list    # 테스트 계정 목록 조회")
        print("  python create_test_users.py delete  # 테스트 계정 삭제")
        return
    
    command = sys.argv[1].lower()
    
    if command == "create":
        await create_test_users()
    elif command == "list":
        await list_test_users()
    elif command == "delete":
        confirm = input("정말로 모든 테스트 계정을 삭제하시겠습니까? (y/N): ")
        if confirm.lower() == 'y':
            await delete_test_users()
        else:
            print("❌ 삭제가 취소되었습니다.")
    else:
        print(f"❌ 알 수 없는 명령어: {command}")

if __name__ == "__main__":
    asyncio.run(main())
