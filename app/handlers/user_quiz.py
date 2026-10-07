from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from app.keyboards.inline import back, kb
from app.services.quiz import answer_question, create_attempt, finish_attempt, wrong_questions
from app.services.users import get_user
from app.services.formatting import bar, e, pct
from app.states import QuizState

router = Router(name='user_quiz')


def question_text(index: int, total: int, prompt: str, difficulty: str) -> str:
    diff = {'easy': '🟢 Oson', 'medium': '🟡 O‘rta', 'hard': '🔴 Qiyin'}.get(difficulty, '🟡 O‘rta')
    return f'📚 <b>TEST</b>\n\n<b>{bar(index/total)}</b> {index}/{total}\n🎯 {diff}\n\n❓ <b>{e(prompt)}</b>'


async def begin(call: CallbackQuery, state: FSMContext, book_id: int | None, mode: str, difficulty: str = 'mixed') -> None:
    user = await get_user(call.from_user.id)
    if not user:
        await call.message.answer('Avval /start bosing.')
        return
    try:
        attempt, questions = await create_attempt(user.id, book_id, mode, 10, difficulty)
    except ValueError as exc:
        await call.message.answer(f'❌ {e(exc)}')
        return
    await state.set_state(QuizState.running)
    await state.update_data(attempt_id=attempt.id, question_ids=[q.id for q in questions], index=0, answers=0)
    q = questions[0]
    await call.message.answer(question_text(1, len(questions), q.prompt, q.difficulty), reply_markup=kb([
        [(f'A) {q.option_a}', f'answer:{q.id}:0')],
        [(f'B) {q.option_b}', f'answer:{q.id}:1')],
        [(f'C) {q.option_c}', f'answer:{q.id}:2')],
        [(f'D) {q.option_d}', f'answer:{q.id}:3')],
        [('⚠️ Savolni report qilish', f'report:{q.id}')],
    ]))


@router.message(F.text == '🧠 TESTLAR')
async def tests_menu(message: Message) -> None:
    await message.answer('<b>🧠 TESTLAR</b>\n\nQanday test ishlamoqchisiz?', reply_markup=kb([
        [('📖 Kitob bo‘yicha', 'quiz:books')],
        [('🎲 Tasodifiy test', 'quiz:random')],
        [('⚡ Tezkor 5 ta', 'quiz:quick')],
        [('🎯 10 ta savol', 'quiz:quick10')],
        [('🔥 Qiyin savollar', 'quiz:hard_all')],
        [('📅 Bugungi challenge', 'quiz:daily')],
        [('❌ Xato savollarim', 'profile:mistakes')],
    ]))


@router.callback_query(F.data == 'quiz:books')
async def choose_book(call: CallbackQuery) -> None:
    await call.answer()
    from sqlalchemy import select
    from app.db.models import Book
    from app.db.session import SessionLocal
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).where(Book.is_active.is_(True)).order_by(Book.title))).all())
    await call.message.edit_text('<b>📖 KITOB TANLANG</b>', reply_markup=kb([[('📖 ' + b.title, f'quiz:book:{b.id}')] for b in books] or [[('⬅️ Orqaga','user:home')]]))


@router.callback_query(F.data.startswith('quiz:book:'))
async def quiz_book(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, int(call.data.split(':')[2]), 'book')


@router.callback_query(F.data.startswith('quiz:hard:'))
async def quiz_hard(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, int(call.data.split(':')[2]), 'hard', 'hard')


@router.callback_query(F.data == 'quiz:random')
async def quiz_random(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, None, 'random')


@router.callback_query(F.data == 'quiz:quick')
async def quiz_quick(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, None, 'quick')


@router.callback_query(F.data == 'quiz:quick10')
async def quiz_quick10(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, None, 'quick10')


@router.callback_query(F.data == 'quiz:hard_all')
async def quiz_hard_all(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, None, 'hard_all', 'hard')


@router.callback_query(F.data == 'quiz:daily')
async def quiz_daily(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await begin(call, state, None, 'daily')


@router.callback_query(F.data.startswith('quiz:one:'))
async def quiz_one(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    from app.db.models import Question
    from app.db.session import SessionLocal
    from app.services.users import get_user
    user = await get_user(call.from_user.id)
    qid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        q = await session.get(Question, qid)
    if not user or not q:
        await call.message.answer('❌ Savol topilmadi.')
        return
    attempt, _ = await __import__('app.services.quiz', fromlist=['create_attempt']).create_attempt(user.id, q.book_id, 'single', 1)
    await state.set_state(QuizState.running)
    await state.update_data(attempt_id=attempt.id, question_ids=[q.id], index=0, answers=0)
    await call.message.answer(question_text(1, 1, q.prompt, q.difficulty), reply_markup=kb([
        [(f'A) {q.option_a}', f'answer:{q.id}:0')],
        [(f'B) {q.option_b}', f'answer:{q.id}:1')],
        [(f'C) {q.option_c}', f'answer:{q.id}:2')],
        [(f'D) {q.option_d}', f'answer:{q.id}:3')],
    ]))

@router.callback_query(F.data.startswith('answer:'))
async def answer(call: CallbackQuery, state: FSMContext) -> None:
    data = await state.get_data()
    if not data.get('attempt_id'):
        await call.answer('Test sessiyasi topilmadi.', show_alert=True)
        return
    _, qid_s, idx_s = call.data.split(':')
    qid, chosen = int(qid_s), int(idx_s)
    try:
        correct, points, explanation, streak = await answer_question(data['attempt_id'], call.from_user.id, qid, chosen)
    except ValueError as exc:
        await call.answer(str(exc), show_alert=True)
        return
    index = int(data.get('index', 0)) + 1
    question_ids = data['question_ids']
    if correct:
        await call.answer('✅ To‘g‘ri! +{} ball'.format(points))
        feedback = f'🎉 <b>Ajoyib!</b>\n✅ To‘g‘ri javob\n⭐ <b>+{points} ball</b>\n🔥 Streak: <b>{streak}</b>'
    else:
        await call.answer('❌ Noto‘g‘ri')
        feedback = '💡 <b>Noto‘g‘ri.</b>\n' + (e(explanation) if explanation else 'Keyingi savolda omad!')
    await call.message.edit_text(feedback)
    if index >= len(question_ids):
        attempt = await finish_attempt(int(data['attempt_id']), call.from_user.id)
        await state.clear()
        if attempt:
            accuracy = pct(attempt.correct_answers, attempt.total_questions)
            await call.message.answer(
                f'🏆 <b>TEST YAKUNLANDI</b>\n\n'
                f'✅ {attempt.correct_answers} ta to‘g‘ri\n'
                f'❌ {attempt.total_questions - attempt.correct_answers} ta xato\n'
                f'⭐ <b>{attempt.points_earned}</b> ball\n'
                f'🎯 Aniqlik: <b>{accuracy}%</b>\n\n'
                f'🔥 Natijangiz reytingga qo‘shildi!',
                reply_markup=kb([[('🔁 Yana test', 'quiz:random')], [('🏆 Reyting', 'rank:home'), ('🏠 Bosh menyu', 'user:home')]]),
            )
        return
    from sqlalchemy import select
    from app.db.models import Question
    from app.db.session import SessionLocal
    next_id = question_ids[index]
    async with SessionLocal() as session:
        q = await session.get(Question, next_id)
    await state.update_data(index=index)
    await call.message.answer(question_text(index + 1, len(question_ids), q.prompt, q.difficulty), reply_markup=kb([
        [(f'A) {q.option_a}', f'answer:{q.id}:0')],
        [(f'B) {q.option_b}', f'answer:{q.id}:1')],
        [(f'C) {q.option_c}', f'answer:{q.id}:2')],
        [(f'D) {q.option_d}', f'answer:{q.id}:3')],
        [('⚠️ Savolni report qilish', f'report:{q.id}')],
    ]))


@router.callback_query(F.data.startswith('report:'))
async def report_question(call: CallbackQuery) -> None:
    from app.db.models import QuestionReport
    from app.db.session import SessionLocal
    qid = int(call.data.split(':')[1])
    async with SessionLocal() as session:
        user = await session.scalar(__import__('sqlalchemy').select(__import__('app.db.models', fromlist=['User']).User).where(__import__('app.db.models', fromlist=['User']).User.telegram_id == call.from_user.id))
        if user:
            session.add(QuestionReport(user_id=user.id, question_id=qid, reason='User report'))
            await session.commit()
    await call.answer('📝 Savol adminlarga yuborildi.', show_alert=True)


@router.callback_query(F.data == 'profile:mistakes')
async def mistakes(call: CallbackQuery) -> None:
    await call.answer()
    questions = await wrong_questions(call.from_user.id, 10)
    if not questions:
        await call.message.answer('🎉 Hali noto‘g‘ri javoblangan savollaringiz yo‘q!', reply_markup=back('user:home'))
        return
    rows = [[(f'❌ {q.prompt[:45]}', f'quiz:one:{q.id}')] for q in questions]
    rows.append([('⬅️ Profil', 'user:home')])
    await call.message.answer('<b>❌ XATO SAVOLLARIM</b>\n\nQayta ko‘rib chiqing:', reply_markup=kb(rows))
