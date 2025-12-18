"""
사용자 역할 변경 스크립트

사용 방법:
    python scripts/update_user_role.py user@example.com admin
"""

import asyncio
import sys
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import engine
from app.models.models import UserModel, UserRole

async def check_user_role(email: str):
    """사용자 현재 역할 확인"""
    async with AsyncSession(engine) as session:
        try:
            query = select(UserModel).where(UserModel.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ 사용자를 찾을 수 없습니다: {email}")
                return None
            
            print(f"✅ 사용자 정보:")
            print(f"   - ID: {user.id}")
            print(f"   - 사용자명: {user.username}")
            print(f"   - 이메일: {user.email}")
            print(f"   - 현재 역할: {user.role}")
            
            return user
            
        except Exception as e:
            print(f"❌ 오류 발생: {str(e)}")
            return None

async def update_user_role(email: str, new_role: str):
    """사용자 역할 변경"""
    async with AsyncSession(engine) as session:
        try:
            # 역할 유효성 검증
            valid_roles = [role.value for role in UserRole]
            if new_role not in valid_roles:
                print(f"❌ 잘못된 역할입니다. 가능한 역할: {', '.join(valid_roles)}")
                return False
            
            # 사용자 조회
            query = select(UserModel).where(UserModel.email == email)
            result = await session.execute(query)
            user = result.scalar_one_or_none()
            
            if not user:
                print(f"❌ 사용자를 찾을 수 없습니다: {email}")
                return False
            
            old_role = user.role
            
            # 역할 업데이트
            user.role = new_role
            await session.commit()
            
            print(f"\n✅ 사용자 역할이 변경되었습니다!")
            print(f"   - 사용자: {user.username} ({user.email})")
            print(f"   - 이전 역할: {old_role}")
            print(f"   - 새 역할: {new_role}")
            
            return True
            
        except Exception as e:
            await session.rollback()
            print(f"❌ 역할 변경 중 오류 발생: {str(e)}")
            return False

async def main():
    if len(sys.argv) < 2:
        print("사용 방법:")
        print("  python scripts/update_user_role.py <이메일> [새역할]")
        print("\n예시:")
        print("  python scripts/update_user_role.py user@example.com admin")
        print("\n가능한 역할: admin, teacher, student")
        return
    
    email = sys.argv[1]
    
    # 역할 확인만
    if len(sys.argv) == 2:
        await check_user_role(email)
        return
    
    # 역할 변경
    new_role = sys.argv[2]
    
    print(f"\n🔄 사용자 역할 변경 시작...")
    print(f"   - 이메일: {email}")
    print(f"   - 새 역할: {new_role}")
    print()
    
    # 현재 정보 확인
    user = await check_user_role(email)
    if not user:
        return
    
    # 확인 메시지
    print(f"\n⚠️  정말로 역할을 '{user.role}' → '{new_role}'로 변경하시겠습니까?")
    confirm = input("계속하려면 'yes' 입력: ")
    
    if confirm.lower() != 'yes':
        print("❌ 취소되었습니다.")
        return
    
    # 역할 변경
    success = await update_user_role(email, new_role)
    
    if success:
        print("\n✅ 완료! 다시 로그인하면 새 역할이 적용됩니다.")
    else:
        print("\n❌ 실패했습니다.")

if __name__ == "__main__":
    asyncio.run(main())


