from sqlalchemy.orm import Session
from app.models import models
from app import schemas
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_user(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

def get_user_by_username(db: Session, username: str):
    return db.query(models.User).filter(models.User.username == username).first()

def create_user(db: Session, user: schemas.UserCreate):
    hashed_password = pwd_context.hash(user.password)
    db_user = models.User(username=user.username, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def get_evaluations(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Evaluation).offset(skip).limit(limit).all()

def create_evaluation(db: Session, evaluation: schemas.EvaluationCreate, user_id: int):
    db_evaluation = models.Evaluation(**evaluation.dict(), user_id=user_id)
    db.add(db_evaluation)
    db.commit()
    db.refresh(db_evaluation)
    return db_evaluation