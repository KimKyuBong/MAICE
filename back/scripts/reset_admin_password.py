import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db.session import engine
from app.models.models import UserModel, UserRole
from app.core.auth.security import hash_password

async def reset_admin_password():
    async with AsyncSession(engine) as session:
        try:
            # 관리자 계정 조회
            query = select(UserModel).where(
                UserModel.username == "hwansi",
                UserModel.role == UserRole.ADMIN
            )
            result = await session.execute(query)
            admin = result.scalar_one_or_none()
            
            if not admin:
                print("관리자 계정 'hwansi'를 찾을 수 없습니다.")
                return
            
            # 새 비밀번호 설정
            new_password = "password"
            admin.password_hash = hash_password(new_password)
            
            await session.commit()
            
            print(f"관리자 계정({admin.username})의 비밀번호가 재설정되었습니다.")
            print(f"새 비밀번호: {new_password}")
            
        except Exception as e:
            await session.rollback()
            print(f"비밀번호 재설정 중 오류 발생: {str(e)}")
            raise e

if __name__ == "__main__":
    asyncio.run(reset_admin_password()) 