from __future__ import annotations

import html
import io
import re

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, func, select

from app.db.models import Book, Category, Question, QuestionReport
from app.db.session import SessionLocal
from app.filters import AdminCallbackFilter, AdminFilter
from app.keyboards.inline import kb
from app.keyboards.reply import admin_main
from app.services.admin import audit
from app.services.quiz import parse_txt
from app.states import AdminBookState, AdminCategoryState, AdminImportState, AdminQuestionState

router = Router(name='admin_content')
router.message.filter(AdminFilter())
router.callback_query.filter(AdminCallbackFilter())


def _option_lines(raw: str) -> list[str]:
    lines = [x.strip() for x in raw.splitlines() if x.strip()]
    cleaned: list[str] = []
    for line in lines:
        cleaned.append(re.sub(r'^[A-Da-d][.)]\s*', '', line).strip())
    return cleaned


@router.callback_query(F.data == 'admin:books')
async def books_admin(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).order_by(desc(Book.id)).limit(30))).all())
    rows = [[('➕ Kitob qo‘shish', 'admin:book_add')], [('🗂 Kategoriyalar', 'admin:categories')]]
    rows += [[(f'{"🟢" if b.is_active else "🔴"} 📖 {b.title}', f'admin:book:{b.id}')] for b in books]
    rows.append([('⬅️ Kontent', 'admin:home')])
    await call.message.answer('<b>📖 KITOBLAR BOSHQARUVI</b>\n\nKitob → savollar → testlar shu yerda boshqariladi.', reply_markup=kb(rows))


@router.callback_query(F.data.startswith('admin:book:'))
async def book_admin_view(call: CallbackQuery) -> None:
    await call.answer()
    bid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
        active_count = await session.scalar(select(func.count(Question.id)).where(Question.book_id == bid, Question.is_active.is_(True)))
        total_count = await session.scalar(select(func.count(Question.id)).where(Question.book_id == bid))
        category = await session.get(Category, book.category_id) if book and book.category_id else None
    if not book:
        await call.message.answer('❌ Kitob topilmadi.')
        return
    await call.message.answer(
        f'<b>📖 {html.escape(book.title)}</b>\n\n'
        f'✍️ {html.escape(book.author)}\n'
        f'📂 {html.escape(category.name) if category else "Kategoriya yo‘q"}\n'
        f'🟢 Faol savollar: <b>{active_count or 0}</b>\n'
        f'📦 Jami savollar: <b>{total_count or 0}</b>\n\n'
        f'{html.escape(book.description) if book.description else "Tavsif kiritilmagan."}',
        reply_markup=kb([
            [('✏️ Kitobni tahrirlash', f'admin:book_edit:{bid}')],
            [('➕ Savol qo‘shish', f'admin:question_add_book:{bid}')],
            [('📋 Savollarni ko‘rish', f'admin:questions:listbook:{bid}')],
            [('🟢 ON/OFF', f'admin:book_toggle:{bid}')],
            [('🗑 O‘chirish', f'admin:book_delete:{bid}')],
            [('⬅️ Kitoblar', 'admin:books')],
        ]),
    )


@router.callback_query(F.data == 'admin:book_add')
async def book_add(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminBookState.title)
    await call.message.answer('📖 <b>Yangi kitob</b>\n\n1/4 — Kitob nomini yuboring.')


@router.callback_query(F.data.startswith('admin:book_edit:'))
async def book_edit(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    bid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
    if not book:
        await call.message.answer('❌ Kitob topilmadi.')
        return
    await state.set_state(AdminBookState.title)
    await state.update_data(editing_book_id=bid)
    await call.message.answer(f'✏️ <b>{html.escape(book.title)}</b>\n\n1/4 — Yangi kitob nomini yuboring. /cancel bilan bekor qilish mumkin.')


@router.message(AdminBookState.title)
async def book_title(message: Message, state: FSMContext) -> None:
    title = (message.text or '').strip()
    if len(title) < 2:
        await message.answer('❌ Kitob nomi juda qisqa.')
        return
    await state.update_data(title=title)
    await state.set_state(AdminBookState.author)
    await message.answer('2/4 — ✍️ Muallif nomini yuboring.')


@router.message(AdminBookState.author)
async def book_author(message: Message, state: FSMContext) -> None:
    author = (message.text or '').strip()
    if not author:
        await message.answer('❌ Muallif nomini kiriting.')
        return
    await state.update_data(author=author)
    await state.set_state(AdminBookState.description)
    await message.answer('3/4 — 📝 Qisqa tavsif yuboring yoki <code>-</code> yozing.')


@router.message(AdminBookState.description)
async def book_description(message: Message, state: FSMContext) -> None:
    raw = (message.text or '').strip()
    await state.update_data(description='' if raw == '-' else raw)
    await state.set_state(AdminBookState.category)
    await message.answer('4/4 — 📂 Kategoriya nomini yuboring yoki <code>-</code> yozing.')


@router.message(AdminBookState.category)
async def book_category(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    category_name = (message.text or '').strip()
    async with SessionLocal() as session:
        category = None
        if category_name != '-':
            category = await session.scalar(select(Category).where(func.lower(Category.name) == category_name.casefold()))
            if not category:
                category = Category(name=category_name[:120])
                session.add(category)
                await session.flush()
        editing_id = data.get('editing_book_id')
        if editing_id:
            book = await session.get(Book, int(editing_id))
            if not book:
                await state.clear()
                await message.answer('❌ Tahrirlanayotgan kitob topilmadi.', reply_markup=admin_main())
                return
            book.title = data['title']
            book.author = data['author']
            book.description = data['description']
            book.category_id = category.id if category else None
            action = 'book_edit'
        else:
            book = Book(title=data['title'], author=data['author'], description=data['description'], category_id=category.id if category else None)
            session.add(book)
            action = 'book_add'
        await session.commit()
    await audit(message.from_user.id, action, data['title'])
    await state.clear()
    await message.answer('✅ <b>Kitob saqlandi.</b>', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:book_toggle:'))
async def book_toggle(call: CallbackQuery) -> None:
    bid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
        if not book:
            await call.answer('Kitob topilmadi', show_alert=True)
            return
        book.is_active = not book.is_active
        await session.commit()
        status = book.is_active
    await audit(call.from_user.id, 'book_toggle', f'id={bid},active={status}')
    await call.answer('✅ Holat yangilandi')


@router.callback_query(F.data.startswith('admin:book_delete:'))
async def book_delete(call: CallbackQuery) -> None:
    await call.answer()
    bid = int(call.data.split(':')[2])
    await call.message.answer(
        '⚠️ <b>Kitobni o‘chirish</b>\n\nSavollar va unga bog‘liq test ma’lumotlari ham o‘chishi mumkin.',
        reply_markup=kb([[('✅ Ha', f'admin:book_delete_yes:{bid}'), ('❌ Yo‘q', f'admin:book:{bid}')]]),
    )


@router.callback_query(F.data.startswith('admin:book_delete_yes:'))
async def book_delete_yes(call: CallbackQuery) -> None:
    bid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
        if not book:
            await call.answer('Kitob topilmadi', show_alert=True)
            return
        title = book.title
        await session.delete(book)
        await session.commit()
    await audit(call.from_user.id, 'book_delete', f'{bid}:{title}')
    await call.answer('🗑 O‘chirildi')
    await call.message.answer('✅ Kitob o‘chirildi.', reply_markup=admin_main())


@router.callback_query(F.data == 'admin:categories')
async def categories_admin(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        cats = list((await session.scalars(select(Category).order_by(Category.name))).all())
        counts = {c.id: int(await session.scalar(select(func.count(Book.id)).where(Book.category_id == c.id))) for c in cats}
    rows = [[('➕ Kategoriya qo‘shish', 'admin:category_add')]]
    rows += [[(f'📂 {c.name} — {counts.get(c.id, 0)} kitob', f'admin:category:{c.id}')] for c in cats]
    rows.append([('⬅️ Kontent', 'admin:home')])
    await call.message.answer('<b>🗂 KATEGORIYALAR</b>', reply_markup=kb(rows))


@router.callback_query(F.data == 'admin:category_add')
async def category_add(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminCategoryState.waiting_name)
    await call.message.answer('🗂 Yangi kategoriya nomini yuboring.')


@router.message(AdminCategoryState.waiting_name)
async def category_name(message: Message, state: FSMContext) -> None:
    name = (message.text or '').strip()
    if len(name) < 2:
        await message.answer('❌ Kategoriya nomi juda qisqa.')
        return
    async with SessionLocal() as session:
        exists = await session.scalar(select(Category).where(func.lower(Category.name) == name.casefold()))
        if exists:
            await state.clear()
            await message.answer('⚠️ Bu kategoriya allaqachon mavjud.', reply_markup=admin_main())
            return
        session.add(Category(name=name[:120]))
        await session.commit()
    await audit(message.from_user.id, 'category_add', name)
    await state.clear()
    await message.answer('✅ Kategoriya qo‘shildi.', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:category:'))
async def category_view(call: CallbackQuery) -> None:
    await call.answer()
    cid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        category = await session.get(Category, cid)
        count = int(await session.scalar(select(func.count(Book.id)).where(Book.category_id == cid)) or 0)
    if not category:
        return
    await call.message.answer(f'📂 <b>{html.escape(category.name)}</b>\n\n📚 Kitoblar: <b>{count}</b>', reply_markup=kb([
        [('🗑 Kategoriyani o‘chirish', f'admin:category_delete:{cid}')],
        [('⬅️ Kategoriyalar', 'admin:categories')],
    ]))


@router.callback_query(F.data.startswith('admin:category_delete:'))
async def category_delete(call: CallbackQuery) -> None:
    cid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        category = await session.get(Category, cid)
        if not category:
            await call.answer('Topilmadi', show_alert=True)
            return
        title = category.name
        books = list((await session.scalars(select(Book).where(Book.category_id == cid))).all())
        for book in books:
            book.category_id = None
        await session.delete(category)
        await session.commit()
    await audit(call.from_user.id, 'category_delete', title)
    await call.answer('🗑 Kategoriya o‘chirildi')
    await call.message.answer('✅ Kategoriya o‘chirildi, kitoblar saqlanib qoldi.')


@router.callback_query(F.data == 'admin:questions')
async def questions_admin(call: CallbackQuery) -> None:
    await call.answer()
    await call.message.answer('<b>❓ SAVOLLAR MARKAZI</b>\n\nBitta savolni qo‘lda qo‘shing yoki 100 tagacha savolni TXT bilan import qiling.', reply_markup=kb([
        [('➕ Bitta savol', 'admin:question_add')],
        [('📋 Savollar ro‘yxati', 'admin:questions:list')],
        [('📥 TXT import', 'admin:import')],
        [('⚠️ Savol reportlari', 'admin:reports')],
        [('⬅️ Kontent', 'admin:home')],
    ]))


@router.callback_query(F.data == 'admin:questions:list')
async def question_book_list(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).order_by(Book.title).limit(50))).all())
    rows = [[(f'📖 {b.title}', f'admin:questions:listbook:{b.id}')] for b in books]
    rows.append([('⬅️ Savollar markazi', 'admin:questions')])
    await call.message.answer('<b>📋 SAVOLLAR — KITOB TANLANG</b>', reply_markup=kb(rows or [[('⬅️ Orqaga', 'admin:questions')]]))


@router.callback_query(F.data.startswith('admin:questions:listbook:'))
async def question_list_by_book(call: CallbackQuery) -> None:
    await call.answer()
    bid = int(call.data.split(':')[3])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
        questions = list((await session.scalars(select(Question).where(Question.book_id == bid).order_by(Question.id.desc()).limit(25))).all())
    if not book:
        return
    rows = [[(f'{"🟢" if q.is_active else "🔴"} Q{q.id}: {q.prompt[:45]}', f'admin:q:{q.id}')] for q in questions]
    rows.append([('➕ Yangi savol', f'admin:question_add_book:{bid}')])
    rows.append([('⬅️ Savollar', 'admin:questions')])
    await call.message.answer(f'<b>📖 {html.escape(book.title)}</b>\n\nOxirgi {len(questions)} ta savol:', reply_markup=kb(rows))


@router.callback_query(F.data == 'admin:question_add')
async def question_add(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).where(Book.is_active.is_(True)).order_by(Book.title))).all())
    rows = [[(f'📖 {b.title}', f'admin:question_add_book:{b.id}')] for b in books]
    rows.append([('⬅️ Savollar', 'admin:questions')])
    await call.message.answer('<b>➕ SAVOL QO‘SHISH</b>\n\nAvval kitobni tanlang.', reply_markup=kb(rows or [[('⬅️ Orqaga', 'admin:questions')]]))


@router.callback_query(F.data.startswith('admin:question_add_book:'))
async def question_add_book(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    bid = int(call.data.split(':')[3])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
    if not book:
        await call.message.answer('❌ Kitob topilmadi.')
        return
    await state.set_state(AdminQuestionState.waiting_prompt)
    await state.update_data(book_id=bid, editing_question_id=None)
    await call.message.answer(f'📖 <b>{html.escape(book.title)}</b>\n\n1/3 — ❓ Savol matnini yuboring.')


@router.message(AdminQuestionState.waiting_prompt)
async def question_prompt(message: Message, state: FSMContext) -> None:
    prompt = (message.text or '').strip()
    if len(prompt) < 5:
        await message.answer('❌ Savol matni juda qisqa.')
        return
    await state.update_data(prompt=prompt)
    await state.set_state(AdminQuestionState.waiting_options)
    await message.answer('2/3 — Variantlarni <b>4 qatorda</b> yuboring:\n<code>A) ...\nB) ...\nC) ...\nD) ...</code>')


@router.message(AdminQuestionState.waiting_options)
async def question_options(message: Message, state: FSMContext) -> None:
    options = _option_lines(message.text or '')
    if len(options) != 4 or any(len(x) < 1 for x in options):
        await message.answer('❌ Aynan 4 ta variant kerak. Har birini alohida qatorda yuboring.')
        return
    await state.update_data(options=options)
    await state.set_state(AdminQuestionState.waiting_answer)
    await message.answer('3/3 — To‘g‘ri javobni yuboring: <code>A</code>, <code>B</code>, <code>C</code> yoki <code>D</code>. Istasangiz yoniga darajani yozing: <code>B hard</code>.')


@router.message(AdminQuestionState.waiting_answer)
async def question_answer(message: Message, state: FSMContext) -> None:
    tokens = (message.text or '').strip().lower().split()
    if not tokens or tokens[0] not in {'a', 'b', 'c', 'd'}:
        await message.answer('❌ Javob faqat A, B, C yoki D bo‘lishi kerak.')
        return
    answer_index = ord(tokens[0]) - ord('a')
    difficulty = tokens[1] if len(tokens) > 1 else 'medium'
    if difficulty not in {'easy', 'medium', 'hard'}:
        difficulty = 'medium'
    data = await state.get_data()
    async with SessionLocal() as session:
        editing_id = data.get('editing_question_id')
        duplicate_stmt = select(Question).where(Question.book_id == data['book_id'], func.lower(Question.prompt) == data['prompt'].casefold())
        if editing_id:
            duplicate_stmt = duplicate_stmt.where(Question.id != int(editing_id))
        duplicate = await session.scalar(duplicate_stmt)
        if duplicate:
            await state.clear()
            await message.answer('⚠️ Bu savol shu kitobda allaqachon mavjud.', reply_markup=admin_main())
            return
        if editing_id:
            q = await session.get(Question, int(editing_id))
            if not q:
                await state.clear()
                await message.answer('❌ Tahrirlanayotgan savol topilmadi.', reply_markup=admin_main())
                return
            q.prompt = data['prompt']
            q.option_a, q.option_b, q.option_c, q.option_d = data['options']
            q.answer_index = answer_index
            q.difficulty = difficulty
            action = 'question_edit'
        else:
            q = Question(
                book_id=data['book_id'],
                prompt=data['prompt'],
                option_a=data['options'][0],
                option_b=data['options'][1],
                option_c=data['options'][2],
                option_d=data['options'][3],
                answer_index=answer_index,
                difficulty=difficulty,
            )
            session.add(q)
            action = 'question_add'
        await session.commit()
    await audit(message.from_user.id, action, f'book={data["book_id"]},difficulty={difficulty}')
    await state.clear()
    await message.answer('✅ <b>Savol saqlandi!</b>', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:q_edit:'))
async def question_edit(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    qid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        q = await session.get(Question, qid)
    if not q:
        await call.message.answer('❌ Savol topilmadi.')
        return
    await state.set_state(AdminQuestionState.waiting_prompt)
    await state.update_data(book_id=q.book_id, editing_question_id=q.id)
    await call.message.answer(f'✏️ <b>Q{qid} tahriri</b>\n\n1/3 — Yangi savol matnini yuboring.')


@router.callback_query(F.data.startswith('admin:q:'))
async def question_view(call: CallbackQuery) -> None:
    await call.answer()
    qid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        q = await session.get(Question, qid)
        book = await session.get(Book, q.book_id) if q else None
    if not q or not book:
        return
    answer_letter = 'ABCD'[q.answer_index] if q.answer_index in range(4) else '?'
    await call.message.answer(
        f'<b>❓ Q{q.id}</b> · {html.escape(book.title)}\n\n'
        f'{html.escape(q.prompt)}\n\n'
        f'A) {html.escape(q.option_a)}\nB) {html.escape(q.option_b)}\nC) {html.escape(q.option_c)}\nD) {html.escape(q.option_d)}\n\n'
        f'✅ Javob: <b>{answer_letter}</b>\n🎯 Daraja: <b>{html.escape(q.difficulty)}</b>\n🟢 Holat: <b>{"ON" if q.is_active else "OFF"}</b>',
        reply_markup=kb([
            [('✏️ Tahrirlash', f'admin:q_edit:{qid}')],
            [('🟢 ON/OFF', f'admin:q_toggle:{qid}')],
            [('🗃 Arxivlash', f'admin:q_archive:{qid}')],
            [('⬅️ Savollar', f'admin:questions:listbook:{q.book_id}')],
        ]),
    )


@router.callback_query(F.data.startswith('admin:q_toggle:'))
async def question_toggle(call: CallbackQuery) -> None:
    qid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        q = await session.get(Question, qid)
        if not q:
            await call.answer('Savol topilmadi', show_alert=True)
            return
        q.is_active = not q.is_active
        await session.commit()
        status = q.is_active
    await audit(call.from_user.id, 'question_toggle', f'id={qid},active={status}')
    await call.answer('✅ Holat yangilandi')


@router.callback_query(F.data.startswith('admin:q_archive:'))
async def question_archive(call: CallbackQuery) -> None:
    qid = int(call.data.split(':')[2])
    await call.answer()
    await call.message.answer('🗃 Savolni arxivlashni tasdiqlaysizmi?', reply_markup=kb([
        [('✅ Ha', f'admin:q_archive_yes:{qid}')],
        [('❌ Yo‘q', f'admin:q:{qid}')],
    ]))


@router.callback_query(F.data.startswith('admin:q_archive_yes:'))
async def question_archive_yes(call: CallbackQuery) -> None:
    qid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        q = await session.get(Question, qid)
        book_id = q.book_id if q else None
        if q:
            q.is_active = False
            await session.commit()
    await audit(call.from_user.id, 'question_archive', str(qid))
    await call.answer('🗃 Arxivlandi')
    if book_id:
        await call.message.answer('✅ Savol arxivlandi.', reply_markup=kb([[('⬅️ Kitob savollari', f'admin:questions:listbook:{book_id}')]]))


@router.callback_query(F.data == 'admin:import')
async def import_start(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.set_state(AdminImportState.waiting_file)
    await call.message.answer('📥 <b>TXT IMPORT</b>\n\n100 tagacha savolli `.txt` fayl yuboring. Format README ichida berilgan.')


@router.message(AdminImportState.waiting_file, F.document)
async def import_file(message: Message, state: FSMContext, bot) -> None:
    document = message.document
    if not document.file_name or not document.file_name.lower().endswith('.txt'):
        await message.answer('❌ Faqat `.txt` fayl qabul qilinadi.')
        return
    file = await bot.get_file(document.file_id)
    buffer = io.BytesIO()
    await bot.download_file(file.file_path, buffer)
    content = buffer.getvalue().decode('utf-8', errors='replace')
    questions, errors = parse_txt(content, 100)
    await state.update_data(parsed=[{'prompt': q.prompt, 'options': q.options, 'answer_index': q.answer_index, 'difficulty': q.difficulty, 'explanation': q.explanation} for q in questions])
    async with SessionLocal() as session:
        books = list((await session.scalars(select(Book).where(Book.is_active.is_(True)).order_by(Book.title))).all())
    preview = f'📄 <b>{html.escape(document.file_name)}</b>\n\n✅ Tayyor: <b>{len(questions)}</b>\n⚠️ Muammolar: <b>{len(errors)}</b>'
    if errors:
        preview += '\n\n' + '\n'.join(f'• {html.escape(e)}' for e in errors[:8])
    rows = [[(f'📖 {b.title}', f'admin:import_book:{b.id}')] for b in books]
    rows.append([('❌ Bekor qilish', 'admin:import_cancel')])
    await state.set_state(AdminImportState.choosing_book)
    await message.answer(preview + '\n\nKitobni tanlang:', reply_markup=kb(rows or [[('❌ Bekor qilish', 'admin:import_cancel')]]))


@router.callback_query(F.data == 'admin:import_cancel')
async def import_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    await state.clear()
    await call.message.answer('❌ Import bekor qilindi.', reply_markup=admin_main())


@router.callback_query(F.data.startswith('admin:import_book:'))
async def import_book(call: CallbackQuery, state: FSMContext) -> None:
    await call.answer()
    bid = int(call.data.split(':')[2])
    data = await state.get_data()
    parsed = data.get('parsed', [])
    async with SessionLocal() as session:
        book = await session.get(Book, bid)
        if not book:
            await state.clear()
            await call.message.answer('❌ Kitob topilmadi.')
            return
        existing = {' '.join(str(x[0]).casefold().split()) for x in (await session.execute(select(Question.prompt).where(Question.book_id == bid))).all()}
        added = duplicates = 0
        for item in parsed:
            key = ' '.join(item['prompt'].casefold().split())
            if key in existing:
                duplicates += 1
                continue
            existing.add(key)
            session.add(Question(book_id=bid, prompt=item['prompt'], option_a=item['options'][0], option_b=item['options'][1], option_c=item['options'][2], option_d=item['options'][3], answer_index=item['answer_index'], difficulty=item.get('difficulty', 'medium'), explanation=item.get('explanation', '')))
            added += 1
        await session.commit()
    await audit(call.from_user.id, 'txt_import', f'book={bid},added={added},duplicates={duplicates}')
    await state.clear()
    await call.message.answer(f'✅ <b>Import yakunlandi</b>\n\n➕ Qo‘shildi: <b>{added}</b>\n🔁 Duplicate: <b>{duplicates}</b>', reply_markup=admin_main())


@router.callback_query(F.data == 'admin:reports')
async def reports(call: CallbackQuery) -> None:
    await call.answer()
    async with SessionLocal() as session:
        rows = list((await session.scalars(select(QuestionReport).where(QuestionReport.status == 'open').order_by(desc(QuestionReport.id)).limit(30))).all())
    buttons = [[(f'⚠️ Report #{r.id} — Q{r.question_id}', f'admin:report:{r.id}')] for r in rows]
    buttons.append([('⬅️ Kontent', 'admin:home')])
    await call.message.answer('<b>⚠️ SAVOL REPORTLARI</b>', reply_markup=kb(buttons))


@router.callback_query(F.data.startswith('admin:report:'))
async def report_view(call: CallbackQuery) -> None:
    await call.answer()
    rid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        report = await session.get(QuestionReport, rid)
        q = await session.get(Question, report.question_id) if report else None
    if not report or not q:
        await call.message.answer('❌ Report yoki savol topilmadi.')
        return
    await call.message.answer(f'⚠️ <b>REPORT #{rid}</b>\n\n❓ {html.escape(q.prompt)}\n📝 Sabab: {html.escape(report.reason)}', reply_markup=kb([[('✅ Yopish', f'admin:report_close:{rid}'), ('🗃 Savolni arxivlash', f'admin:report_deleteq:{rid}')]]))


@router.callback_query(F.data.startswith('admin:report_close:'))
async def report_close(call: CallbackQuery) -> None:
    rid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        r = await session.get(QuestionReport, rid)
        if r:
            r.status = 'closed'
            await session.commit()
    await audit(call.from_user.id, 'report_close', str(rid))
    await call.answer('✅ Yopildi')


@router.callback_query(F.data.startswith('admin:report_deleteq:'))
async def report_deleteq(call: CallbackQuery) -> None:
    rid = int(call.data.split(':')[2])
    async with SessionLocal() as session:
        r = await session.get(QuestionReport, rid)
        if r:
            q = await session.get(Question, r.question_id)
            if q:
                q.is_active = False
            r.status = 'closed'
            await session.commit()
    await audit(call.from_user.id, 'report_archive_question', str(rid))
    await call.answer('🗃 Savol arxivlandi')
