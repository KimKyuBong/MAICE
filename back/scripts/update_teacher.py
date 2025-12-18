import asyncio
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import engine
from models.models import UserModel, UserRole
from utils.helpers import get_password_hash

async def update_teacher_password(username: str, new_password: str):
    async with AsyncSession(engine) as session:
        try:
            # 사용자 조회
            query = select(UserModel).where(
                UserModel.username == username,
                UserModel.role == UserRole.TEACHER
            )
            result = await session.execute(query)
            teacher = result.scalars().first()
            
            if not teacher:
                print(f"교사 계정 '{username}'를 찾을 수 없습니다.")
                return
            
            # 새 비밀번호 해시 생성 및 업데이트
            password_hash = get_password_hash(new_password)
            teacher.password_hash = password_hash
            
            await session.commit()
            print(f"교사 계정 '{username}'의 비밀번호가 업데이트되었습니다.")
            
        except Exception as e:
            print(f"비밀번호 업데이트 중 오류 발생: {str(e)}")
            raise e

if __name__ == "__main__":
    username = "teacher"
    new_password = "teacher"
    asyncio.run(update_teacher_password(username, new_password)) 