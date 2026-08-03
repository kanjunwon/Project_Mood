import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, Text, Date, Time, TIMESTAMP, BigInteger,
    SmallInteger, Numeric, Boolean, ForeignKey, ARRAY, UniqueConstraint
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    diaries = relationship("Diary", back_populates="user")
    personal_tests = relationship("PersonalTest", back_populates="user")


class Diary(Base):
    __tablename__ = "diaries"
    __table_args__ = (UniqueConstraint("user_id", "entry_date", name="uq_user_entry_date"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    entry_date = Column(Date, nullable=False)
    what = Column(Text, nullable=False)
    why = Column(Text, nullable=False)
    who = Column(ARRAY(String), nullable=False)
    event_time = Column(Time, nullable=False)
    where_ = Column("where", Text, nullable=False)
    generated_diary_text = Column(Text)
    status = Column(String(20), default="pending")  # pending|processing|completed|failed
    image_url = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="diaries")
    emotions = relationship("EmotionAnalysis", back_populates="diary", cascade="all, delete")


class EmotionAnalysis(Base):
    __tablename__ = "emotion_analyses"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    diary_id = Column(BigInteger, ForeignKey("diaries.id", ondelete="CASCADE"))
    emotion = Column(String(30), nullable=False)
    score = Column(Numeric(5, 4), nullable=False)
    is_primary = Column(Boolean, default=False)

    diary = relationship("Diary", back_populates="emotions")


class PersonalTest(Base):
    __tablename__ = "personal_tests"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    completed_at = Column(TIMESTAMP(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="personal_tests")
    answers = relationship("PersonalTestAnswer", back_populates="test", cascade="all, delete")


class PersonalTestAnswer(Base):
    __tablename__ = "personal_test_answers"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    test_id = Column(BigInteger, ForeignKey("personal_tests.id", ondelete="CASCADE"))
    question_no = Column(SmallInteger, nullable=False)  # 1~19
    answer_value = Column(SmallInteger, nullable=False)  # 매우그렇다=5 ~ 매우아니다=1

    test = relationship("PersonalTest", back_populates="answers")
