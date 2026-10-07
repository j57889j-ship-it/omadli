from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from random import sample

from sqlalchemy import desc, select

from app.db.models import AnswerLog, Book, QuizAttempt, Question, User
from app.db.session import SessionLocal
from app.services.achievements import refresh_achievements
from app.services.users import update_streak


from app.utils.question_parser import ParsedQuestion, parse_txt

async def create_attempt(user_id: int, book_id: int | None, mode: str, requested: int = 10, difficulty: str = 'mixed') -> tuple[QuizAttempt, list[Question]]:
    async with SessionLocal() as session:
        query = select(Question).where(Question.is_active.is_(True))
        if book_id:
            query = query.where(Question.book_id == book_id)
        if difficulty in {'easy', 'medium', 'hard'}:
            query = query.where(Question.difficulty == difficulty)
        pool = list((await session.scalars(query.order_by(Question.id))).all())
        if not pool:
            raise ValueError('Savollar topilmadi.')
        chosen = sample(pool, min(max(1, requested), len(pool)))
        attempt = QuizAttempt(user_id=user_id, book_id=book_id, total_questions=len(chosen), mode=mode)
        session.add(attempt)
        await session.commit()
        await session.refresh(attempt)
        return attempt, chosen


async def answer_question(attempt_id: int, telegram_id: int, question_id: int, chosen_index: int) -> tuple[bool, int, str, int]:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        attempt = await session.get(QuizAttempt, attempt_id)
        question = await session.get(Question, question_id)
        if not user or not attempt or not question or attempt.user_id != user.id:
            raise ValueError('Test sessiyasi topilmadi.')
        already = await session.scalar(select(AnswerLog).where(AnswerLog.attempt_id == attempt_id, AnswerLog.question_id == question_id))
        if already:
            raise ValueError('Bu savolga allaqachon javob berilgan.')
        correct = chosen_index == question.answer_index
        points_map = {'easy': 5, 'medium': 10, 'hard': 20}
        points = points_map.get(question.difficulty, 10) if correct else 0
        session.add(AnswerLog(attempt_id=attempt.id, user_id=user.id, question_id=question.id, chosen_index=chosen_index, is_correct=correct, points=points))
        user.questions_answered += 1
        if correct:
            user.correct_answers += 1
            user.points += points
            user.rank_points += points
        attempt.correct_answers += 1 if correct else 0
        attempt.points_earned += points
        await session.commit()
        explanation = question.explanation
        streak = await update_streak(user)
        await refresh_achievements(telegram_id)
        return correct, points, explanation, streak


async def finish_attempt(attempt_id: int, telegram_id: int) -> QuizAttempt | None:
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        attempt = await session.get(QuizAttempt, attempt_id)
        if not user or not attempt or attempt.user_id != user.id:
            return None
        attempt.finished_at = datetime.now(timezone.utc)
        await session.commit()
        await session.refresh(attempt)
        return attempt


async def wrong_questions(telegram_id: int, limit: int = 10) -> list[Question]:
    async with SessionLocal() as session:
        result = await session.execute(
            select(Question).join(AnswerLog, AnswerLog.question_id == Question.id).join(User, AnswerLog.user_id == User.id).where(User.telegram_id == telegram_id, AnswerLog.is_correct.is_(False)).order_by(desc(AnswerLog.id)).limit(limit)
        )
        seen: set[int] = set()
        out: list[Question] = []
        for q in result.scalars().all():
            if q.id not in seen:
                out.append(q)
                seen.add(q.id)
        return out
