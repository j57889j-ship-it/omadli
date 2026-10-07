from aiogram.fsm.state import State, StatesGroup


class QuizState(StatesGroup):
    running = State()


class BookSearchState(StatesGroup):
    waiting_query = State()


class AdminImportState(StatesGroup):
    waiting_file = State()
    choosing_book = State()


class AdminCategoryState(StatesGroup):
    waiting_name = State()


class AdminBookState(StatesGroup):
    title = State()
    author = State()
    description = State()
    category = State()


class AdminQuestionState(StatesGroup):
    choosing_book = State()
    waiting_prompt = State()
    waiting_options = State()
    waiting_answer = State()


class AdminBroadcastState(StatesGroup):
    waiting_message = State()


class AdminChannelPostState(StatesGroup):
    waiting_message = State()


class AdminUserState(StatesGroup):
    waiting_search = State()
    waiting_points = State()
    waiting_user_id = State()


class AdminSettingState(StatesGroup):
    waiting_value = State()


class AdminChannelState(StatesGroup):
    waiting_chat_id = State()
    waiting_join_url = State()
    waiting_title = State()


class AdminReactionState(StatesGroup):
    waiting_emojis = State()
