import asyncio
import json
import os
import uuid
from datetime import datetime

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from db.session import engine
from models.models import Base, UserModel, QuestionModel, SurveyResponseModel, TeacherEvaluationModel, GPTEvaluationModel, UserRole

async def restore_data():
    # Drop and recreate schema
    async with engine.begin() as conn:
        await conn.execute(text("DROP SCHEMA public CASCADE"))
        await conn.execute(text("CREATE SCHEMA public"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO postgres"))
        await conn.execute(text("GRANT ALL ON SCHEMA public TO public"))
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session for data operations
    async with AsyncSession(engine) as session:
        try:
            # Load data from JSON file
            script_dir = os.path.dirname(os.path.abspath(__file__))
            data_file = os.path.join(script_dir, "../maice_data_2025-04-02.json")
            
            print(f"Loading data from {data_file}")
            with open(data_file, "r", encoding='utf-8') as f:
                data = json.load(f)
            
            print("Starting data restoration...")
            # Insert data
            for response in data["responses"]:
                # Create user if not exists
                user_query = select(UserModel).where(UserModel.username == response["stnum"])
                result = await session.execute(user_query)
                user = result.scalars().first()
                
                if not user:
                    print(f"Creating new user: {response['stnum']}")
                    user = UserModel(
                        username=response["stnum"],
                        password_hash="default_password_hash",
                        role=UserRole.STUDENT,
                        access_token=str(uuid.uuid4()),
                        question_count=0,
                        max_questions=10,
                        created_at=datetime.utcnow()
                    )
                    session.add(user)
                    await session.flush()
                
                # Create question
                print(f"Creating question for user {user.username}")
                question = QuestionModel(
                    user_id=user.id,
                    question_text=response["question"],
                    answer_text=response["response"],
                    image_path=None,
                    created_at=datetime.utcnow()
                )
                session.add(question)
                await session.flush()
                
                # Create survey response if scores exist
                if "guidance_score" in response or "clarity_score" in response or "level_score" in response:
                    print(f"Creating survey response for question {question.id}")
                    survey_response = SurveyResponseModel(
                        user_id=user.id,
                        question_id=question.id,
                        response_text="",  # 응답 텍스트는 비워둡니다
                        relevance_score=response.get("guidance_score", 3),  # 기본값 3
                        guidance_score=response.get("clarity_score", 3),  # 기본값 3
                        clarity_score=response.get("level_score", 3),  # 기본값 3
                        feedback_text="",
                        difficult_words="",
                        created_at=datetime.utcnow()
                    )
                    session.add(survey_response)
            
            await session.commit()
            print("Data restoration completed successfully!")
            
        except Exception as e:
            await session.rollback()
            print(f"Error during data restoration: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(restore_data()) 