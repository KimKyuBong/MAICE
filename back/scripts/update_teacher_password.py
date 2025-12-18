import asyncio
from sqlalchemy import select, update
from models.models import UserModel, UserRole
from db.session import async_session
from utils.helpers import get_password_hash

async def update_teacher_password():
    async with async_session() as session:
        # 교사 계정 조회
        query = select(UserModel).where(UserModel.role == UserRole.TEACHER)
        result = await session.execute(query)
        teacher = result.scalar_one_or_none()
        
        if not teacher:
            print("교사 계정을 찾을 수 없습니다.")
            return
            
        # 새 비밀번호 해시 생성
        new_password = "password"
        password_hash = get_password_hash(new_password)
        
        # 비밀번호 업데이트
        teacher.password_hash = password_hash
        await session.commit()
        
        print(f"교사 계정({teacher.username})의 비밀번호가 업데이트되었습니다.")
        print(f"새 비밀번호: {new_password}")

if __name__ == "__main__":
    asyncio.run(update_teacher_password()) 