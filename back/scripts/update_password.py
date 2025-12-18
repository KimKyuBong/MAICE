import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import engine
from models.models import UserModel
from utils.helpers import get_password_hash

async def update_user_password(username: str, new_password: str):
    async with AsyncSession(engine) as session:
        try:
            # 사용자 조회
            query = select(UserModel).where(UserModel.username == username)
            result = await session.execute(query)
            user = result.scalars().first()
            
            if not user:
                print(f"사용자 '{username}'를 찾을 수 없습니다.")
                return
            
            # 새 비밀번호 해시 생성 및 업데이트
            password_hash = get_password_hash(new_password)
            user.password_hash = password_hash
            
            await session.commit()
            print(f"사용자 '{username}'의 비밀번호가 성공적으로 업데이트되었습니다!")
            
        except Exception as e:
            await session.rollback()
            print(f"비밀번호 업데이트 중 오류 발생: {str(e)}")
            raise

if __name__ == "__main__":
    username = "hwansi"
    new_password = "abc123"
    asyncio.run(update_user_password(username, new_password)) 