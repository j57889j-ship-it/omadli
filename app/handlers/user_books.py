from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, func, select

from app.db.models import AnswerLog, Book, Category, FavoriteBook, Question, QuizAttempt, User
from app.db.session import SessionLocal
from app.keyboards.inline import back, kb
from app.services.formatting import e, pct
from app.states import BookSearchState

router = Router(name='user_books')


async def book_rows() -> list[Book]:
    async with SessionLocal() as session:
        return list((await session.scalars(select(Book).where(Book.is_active.is_(True)).order_by(desc(Book.created_at)).limit(50))).all())


async def book_menu_text() -> str:
    return '<b>📚 KITOBLAR</b>\n\nKitobni tanlang yoki kerakli bo‘limga o‘ting.'


@router.message(F.text == '📚 KITOBLAR')
async def books_menu(message: Message) -> None:
    await message.answer(await book_menu_text(), reply_markup=kb([
        [('🔎 Kitob qidirish', 'books:search')],
        [('📖 Barcha kitoblar', 'books:all')],
        [('🔥 Mashhur kitoblar', 'books:popular')],
        [('🆕 Yangi kitoblar', 'books:new')],
        [('📂 Janrlar', 'books:categories'), ('❤️ Sevimlilarim', 'books:favorites')],
        [('⬅️ Bosh menyu', 'user:home')],
    ]))


@router.callback_query(F.data == 'books:search')
async def books_search(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(BookSearchState.waiting_query)
    await call.message.answer('🔎 Kitob nomi yoki muallifini yuboring:')


@router.message(BookSearchState.waiting_query)
async def books_search_value(message: Message, state: FSMContext) -> None:
    query = message.text.strip()
    async with SessionLocal() as session:
        books = list((await session.scalars(
            select(Book).where(Book.is_active.is_(True), (Book.title.ilike(f'%{query}%')) | (Book.author.ilike(f'%{query}%'))).order_by(Book.title).limit(20)
        )).all())
    await state.clear()
    rows = [[(f'📖 {b.title}', f'book:view:{b.id}')] for b in books]
    rows.append([('⬅️ Kitoblar', 'books:home')])
    await message.answer('<b>🔎 QIDIRUV NATIJALARI</b>', reply_markup=kb(rows or [[('⬅️ Kitoblar','books:home')]]))


@router.callback_query(F.data == 'books:all')
async def books_all(call: CallbackQuery) -> None:
    await call.answer()
    books = await book_rows()
    rows = [[(f'📖 {b.title}', f'book:view:{b.id}')] for b in books]
    rows.append([('⬅️ Orqaga', 'books:home')])
    await call.message.edit_text('<b>📚 BARCHA KITOBLAR</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','books:home')]]))


@router.callback_query(F.data == 'books:new')
async def books_new(call: CallbackQuery) -> None:
    await call.answer()
    books = await book_rows()
    rows = [[(f'🆕 {b.title}', f'book:view:{b.id}')] for b in books[:15]]
    rows.append([('⬅️ Orqaga', 'books:home')])
    await call.message.edit_text('<b>🆕 YANGI KITOBLAR</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','books:home')]]))


@router.callback_query(F.data == 'books:popular')
async def books_popular(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        result = await session.execute(
            select(Book, func.count(AnswerLog.id).label('answers'))
            .join(Question, Question.book_id == Book.id)
            .join(AnswerLog, AnswerLog.question_id == Question.id, isouter=True)
            .where(Book.is_active.is_(True))
            .group_by(Book.id)
            .order_by(desc('answers'), desc(Book.id))
            .limit(15)
        )
        rows_data = result.all()
    rows = [[(f'🔥 {book.title} — {int(count)} javob', f'book:view:{book.id}')] for book, count in rows_data]
    rows.append([('⬅️ Orqaga', 'books:home')])
    await call.message.edit_text('<b>🔥 MASHHUR KITOBLAR</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','books:home')]]))


@router.callback_query(F.data == 'books:categories')
async def categories(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        cats = list((await session.scalars(select(Category).order_by(Category.name))).all())
    rows = [[(f'📂 {c.name}', f'cat:{c.id}')] for c in cats]
    rows.append([('⬅️ Orqaga', 'books:home')])
    await call.message.edit_text('<b>📂 JANRLAR</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','books:home')]]))


@router.callback_query(F.data.startswith('cat:'))
async def category_books(call: CallbackQuery) -> None:
    await call.answer()
    cat_id = int(call.data.split(':')[1])
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).where(Book.category_id == cat_id, Book.is_active.is_(True)).order_by(Book.title))).all())
    rows = [[(f'📖 {b.title}', f'book:view:{b.id}')] for b in books]
    rows.append([('⬅️ Orqaga', 'books:categories')])
    await call.message.edit_text('<b>📂 KATEGORIYA KITOBLARI</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','books:categories')]]))


@router.callback_query(F.data.startswith('book:view:'))
async def book_view(call: CallbackQuery) -> None:
    await call.answer()
    book_id = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        book = await session.get(Book, book_id)
        total = await session.scalar(select(func.count(Question.id)).where(Question.book_id == book_id, Question.is_active.is_(True)))
    if not book:
        await call.message.answer('Kitob topilmadi.')
        return
    text = (
        f'📖 <b>{e(book.title)}</b>\n\n'
        f'✍️ {e(book.author)}\n'
        f'❓ Savollar: <b>{total or 0}</b>\n\n'
        f'{e(book.description) if book.description else "Kitob haqida ma’lumot hali qo‘shilmagan."}'
    )
    await call.message.edit_text(text, reply_markup=kb([
        [('🧠 Testni boshlash', f'quiz:book:{book.id}')],
        [('🎯 Qiyin savollar', f'quiz:hard:{book.id}'), ('❤️ Sevimliga', f'favorite:{book.id}')],
        [('📊 Mening natijam', f'book:stats:{book.id}')],
        [('⬅️ Kitoblar', 'books:home')],
    ]))


@router.callback_query(F.data == 'books:home')
async def books_home(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.edit_text(await book_menu_text(), reply_markup=kb([
        [('🔎 Kitob qidirish', 'books:search')],
        [('📖 Barcha kitoblar', 'books:all')],
        [('🔥 Mashhur kitoblar', 'books:popular')],
        [('🆕 Yangi kitoblar', 'books:new')],
        [('📂 Janrlar', 'books:categories'), ('❤️ Sevimlilarim', 'books:favorites')],
        [('⬅️ Bosh menyu', 'user:home')],
    ]))


@router.callback_query(F.data.startswith('favorite:'))
async def favorite(call: CallbackQuery) -> None:
    await call.answer()
    book_id = int(call.data.split(':')[1])
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == call.from_user.id))
        if not user:
            return
        row = await session.scalar(select(FavoriteBook).where(FavoriteBook.user_id == user.id, FavoriteBook.book_id == book_id))
        if row:
            await session.delete(row)
            msg = '💔 Sevimlilardan olib tashlandi.'
        else:
            session.add(FavoriteBook(user_id=user.id, book_id=book_id))
            msg = '❤️ Sevimlilarga qo‘shildi.'
        await session.commit()
    await call.message.answer(msg)


@router.callback_query(F.data == 'books:favorites')
@router.callback_query(F.data == 'profile:favorites')
async def favorites(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == call.from_user.id))
        if not user:
            return
        books = list((await session.scalars(select(Book).join(FavoriteBook, FavoriteBook.book_id == Book.id).where(FavoriteBook.user_id == user.id).order_by(Book.title))).all())
    rows = [[(f'❤️ {b.title}', f'book:view:{b.id}')] for b in books]
    rows.append([('⬅️ Orqaga', 'user:home')])
    await call.message.edit_text('<b>❤️ SEVIMLILARIM</b>', reply_markup=kb(rows or [[('⬅️ Orqaga','user:home')]]))


@router.callback_query(F.data.startswith('book:stats:'))
async def book_stats(call: CallbackQuery) -> None:
    await call.answer()
    book_id = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        user = await session.scalar(select(User).where(User.telegram_id == call.from_user.id))
        question_ids = select(Question.id).where(Question.book_id == book_id)
        correct = int(await session.scalar(select(func.count(AnswerLog.id)).where(AnswerLog.user_id == user.id, AnswerLog.question_id.in_(question_ids), AnswerLog.is_correct.is_(True))) or 0) if user else 0
        total = int(await session.scalar(select(func.count(AnswerLog.id)).where(AnswerLog.user_id == user.id, AnswerLog.question_id.in_(question_ids))) or 0) if user else 0
        book = await session.get(Book, book_id)
    await call.message.answer(f'📊 <b>{e(book.title if book else "Kitob")}</b>\n\n✅ To‘g‘ri: <b>{correct}</b>\n🧠 Ishlangan: <b>{total}</b>\n🎯 Aniqlik: <b>{pct(correct,total)}%</b>', reply_markup=back(f'book:view:{book_id}'))
