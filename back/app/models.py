import json
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, JSON, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(String, primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    gradings = relationship("Grading", back_populates="student")
    submissions = relationship("StudentSubmission", back_populates="student")
    text_extractions = relationship("TextExtraction", back_populates="student")

class TextExtraction(Base):
    __tablename__ = "text_extractions"

    id = Column(Integer, primary_key=True)
    student_id = Column(String, ForeignKey("students.id"), nullable=False)
    problem_key = Column(String, nullable=False)
    extraction_number = Column(Integer, nullable=False)
    extracted_text = Column(Text, nullable=False)
    image_path = Column(String, nullable=False)
    solution_steps = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    __table_args__ = (
        UniqueConstraint('student_id', 'problem_key', 'extraction_number',
                        name='uix_student_problem_extraction'),
    )

    student = relationship("Student", back_populates="text_extractions")
    gradings = relationship("Grading", back_populates="extraction")

    @property
    def solution_steps_json(self):
        """Solution steps as JSON"""
        return json.loads(self.solution_steps) if self.solution_steps else []

    def to_dict(self):
        """Convert to dictionary"""
        return {
            "id": self.id,
            "student_id": self.student_id,
            "problem_key": self.problem_key,
            "extraction_number": self.extraction_number,
            "extracted_text": self.extracted_text,
            "image_path": self.image_path,
            "solution_steps": json.dumps(self.solution_steps_json, ensure_ascii=False),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class StudentSubmission(Base):
    __tablename__ = "student_submissions"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"), index=True)
    problem_key = Column(String, ForeignKey("grading_criteria.problem_key"), index=True)
    
    file_name = Column(String)
    image_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    file_size = Column(Integer)
    mime_type = Column(String)
    
    student = relationship("Student", back_populates="submissions")
    gradings = relationship("Grading", back_populates="submission")
    grading_criteria = relationship("GradingCriteria", back_populates="submissions")

class GradingCriteria(Base):
    __tablename__ = "grading_criteria"

    id = Column(Integer, primary_key=True, index=True)
    problem_key = Column(String, unique=True, index=True)
    total_points = Column(Float)
    correct_answer = Column(String)
    
    detailed_criteria = relationship(
        "DetailedCriteria",
        back_populates="grading_criteria",
        lazy="selectin"
    )
    submissions = relationship("StudentSubmission", back_populates="grading_criteria")

class DetailedCriteria(Base):
    __tablename__ = "detailed_criteria"

    id = Column(Integer, primary_key=True, index=True)
    grading_criteria_id = Column(Integer, ForeignKey("grading_criteria.id"))
    item = Column(String)
    points = Column(Float)
    description = Column(String)
    
    grading_criteria = relationship(
        "GradingCriteria",
        back_populates="detailed_criteria"
    )
    detailed_scores = relationship("DetailedScore", back_populates="criteria")

class DetailedScore(Base):
    __tablename__ = "detailed_scores"

    id = Column(Integer, primary_key=True, index=True)
    grading_id = Column(Integer, ForeignKey("gradings.id"))
    detailed_criteria_id = Column(Integer, ForeignKey("detailed_criteria.id"))
    score = Column(Float)
    feedback = Column(String)
    
    grading = relationship("Grading", back_populates="detailed_scores")
    criteria = relationship("DetailedCriteria", back_populates="detailed_scores")

class Grading(Base):
    __tablename__ = "gradings"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(String, ForeignKey("students.id"))
    problem_key = Column(String)
    submission_id = Column(Integer, ForeignKey("student_submissions.id"))
    extraction_id = Column(Integer, ForeignKey("text_extractions.id"))
    image_path = Column(String)
    extracted_text = Column(String)
    solution_steps = Column(JSON, default=list)
    total_score = Column(Float, default=0.0)
    max_score = Column(Float, default=0.0)
    feedback = Column(String)
    grading_number = Column(Integer, default=1)
    is_consolidated = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)

    student = relationship("Student", back_populates="gradings")
    submission = relationship("StudentSubmission", back_populates="gradings")
    extraction = relationship("TextExtraction", back_populates="gradings")
    detailed_scores = relationship("DetailedScore", back_populates="grading")