from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import BigInteger, Boolean, Date, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default='Foydalanuvchi')
    points: Mapped[int] = mapped_column(Integer, default=0)
    rank_points: Mapped[int] = mapped_column(Integer, default=0)
    referral_rank_score: Mapped[int] = mapped_column(Integer, default=0)
    questions_answered: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    streak_days: Mapped[int] = mapped_column(Integer, default=0)
    last_answer_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    pending_referrer_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    referral_confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    referral_bonus_awarded: Mapped[bool] = mapped_column(Boolean, default=False)
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Admin(Base):
    __tablename__ = 'admins'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    role: Mapped[str] = mapped_column(String(32), default='moderator')
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Category(Base):
    __tablename__ = 'categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)


class Book(Base):
    __tablename__ = 'books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    author: Mapped[str] = mapped_column(String(255), default='Noma’lum')
    description: Mapped[str] = mapped_column(Text, default='')
    category_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('categories.id', ondelete='SET NULL'), nullable=True)
    cover_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class Question(Base):
    __tablename__ = 'questions'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey('books.id', ondelete='CASCADE'), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    option_a: Mapped[str] = mapped_column(String(500))
    option_b: Mapped[str] = mapped_column(String(500))
    option_c: Mapped[str] = mapped_column(String(500))
    option_d: Mapped[str] = mapped_column(String(500))
    answer_index: Mapped[int] = mapped_column(Integer)
    difficulty: Mapped[str] = mapped_column(String(16), default='medium', index=True)
    explanation: Mapped[str] = mapped_column(Text, default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index('ix_questions_book_active', 'book_id', 'is_active'),)


class QuizAttempt(Base):
    __tablename__ = 'quiz_attempts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    book_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey('books.id', ondelete='SET NULL'), nullable=True)
    total_questions: Mapped[int] = mapped_column(Integer, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, default=0)
    points_earned: Mapped[int] = mapped_column(Integer, default=0)
    mode: Mapped[str] = mapped_column(String(32), default='book')
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class AnswerLog(Base):
    __tablename__ = 'answer_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    attempt_id: Mapped[int] = mapped_column(Integer, ForeignKey('quiz_attempts.id', ondelete='CASCADE'), index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'), index=True)
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey('questions.id', ondelete='CASCADE'), index=True)
    chosen_index: Mapped[int] = mapped_column(Integer)
    is_correct: Mapped[bool] = mapped_column(Boolean)
    points: Mapped[int] = mapped_column(Integer, default=0)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    __table_args__ = (Index('ix_answer_logs_user_question', 'user_id', 'question_id'),)


class FavoriteBook(Base):
    __tablename__ = 'favorite_books'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    book_id: Mapped[int] = mapped_column(Integer, ForeignKey('books.id', ondelete='CASCADE'))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'book_id', name='uq_favorite_user_book'),)


class Achievement(Base):
    __tablename__ = 'achievements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True)
    title: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(String(500))
    icon: Mapped[str] = mapped_column(String(16), default='🏅')
    requirement: Mapped[int] = mapped_column(Integer, default=1)
    metric: Mapped[str] = mapped_column(String(32), default='questions')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class UserAchievement(Base):
    __tablename__ = 'user_achievements'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    achievement_id: Mapped[int] = mapped_column(Integer, ForeignKey('achievements.id', ondelete='CASCADE'))
    earned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    __table_args__ = (UniqueConstraint('user_id', 'achievement_id', name='uq_user_achievement'),)


class BotSetting(Base):
    __tablename__ = 'bot_settings'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(100), unique=True)
    value: Mapped[str] = mapped_column(Text, default='')
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class RequiredChannel(Base):
    __tablename__ = 'required_channels'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), default='Kanal')
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    join_url: Mapped[str] = mapped_column(String(500), default='')
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class QuestionReport(Base):
    __tablename__ = 'question_reports'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey('users.id', ondelete='CASCADE'))
    question_id: Mapped[int] = mapped_column(Integer, ForeignKey('questions.id', ondelete='CASCADE'))
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(32), default='open', index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class DailyChallenge(Base):
    __tablename__ = 'daily_challenges'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    challenge_date: Mapped[date] = mapped_column(Date, unique=True, index=True)
    question_ids_json: Mapped[str] = mapped_column(Text, default='[]')
    reward_points: Mapped[int] = mapped_column(Integer, default=30)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class BroadcastLog(Base):
    __tablename__ = 'broadcast_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger)
    total_targets: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AdminAuditLog(Base):
    __tablename__ = 'admin_audit_logs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_telegram_id: Mapped[int] = mapped_column(BigInteger)
    action: Mapped[str] = mapped_column(String(120), index=True)
    details: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
