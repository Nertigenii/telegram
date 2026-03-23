import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.client.bot import DefaultBotProperties
from aiogram.exceptions import TelegramForbiddenError, TelegramRetryAfter

import os

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8382103178
SUPPORT_USERNAME = "manager_angels"  # без @
# ===== ОБЯЗАТЕЛЬНАЯ ПОДПИСКА =====


# ===== Логи =====
LOG_BOT_TOKEN = "8638120110:AAE7luaeqX7t6TciXFUVhIkq90OC5Q2q368"
LOG_CHAT_ID = -1003808836404  # ID чата/группы для логов
log_bot = Bot(token=LOG_BOT_TOKEN)


import asyncio

async def send_log(user: Message | CallbackQuery, action: str):
    user_id = user.from_user.id
    username = user.from_user.username or "Нет юзернейма"
    text = f"👤 Пользователь: @{username}\n🆔 ID: {user_id}\n📌 Действие: {action}"

    while True:
        try:
            await log_bot.send_message(LOG_CHAT_ID, text)
            break
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
 
# ================== DATABASE ==================

class Database:
    def __init__(self, path: str):
        self.path = path
        self.db = None

    async def connect(self):
        self.db = await aiosqlite.connect(self.path)
        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            coins INTEGER DEFAULT 0,
            is_banned INTEGER DEFAULT 0,
            is_admin INTEGER DEFAULT 0,
            name TEXT DEFAULT '',
            description TEXT DEFAULT '',
            photo TEXT DEFAULT ''
        )
        """)
            

        await self.db.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_id TEXT
        )
        """)
        try:
            await self.db.execute("""
                ALTER TABLE users ADD COLUMN referrer_id INTEGER
            """)
        except Exception:
            pass  # колонка уже существует

        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, is_admin) VALUES (?, 1)",
            (ADMIN_ID,)
        )

        try:
            await self.db.execute("""
                ALTER TABLE users ADD COLUMN is_blocked INTEGER DEFAULT 0
            """)
        except:
            pass
        
        await self.db.commit()

    async def add_user(self, user_id: int, referrer_id: int | None = None):
        user = await self.get_user(user_id)

        if user:
            return False  # Уже зарегистрирован

        await self.db.execute(
            "INSERT INTO users (user_id, referrer_id) VALUES (?, ?)",
            (user_id, referrer_id)
    )
        await self.db.commit()
        return True  # Новый пользователь

    async def get_user(self, user_id: int):
        async with self.db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        ) as cursor:
            return await cursor.fetchone()

    async def update_coins(self, user_id: int, amount: int):
        await self.db.execute(
            "UPDATE users SET coins = coins + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await self.db.commit()

    async def set_admin(self, user_id: int):
        await self.db.execute(
            "UPDATE users SET is_admin = 1 WHERE user_id = ?",
            (user_id,)
        )
        await self.db.commit()

    async def ban_toggle(self, user_id: int):
        user = await self.get_user(user_id)
        if not user:
            return None

        new_status = 0 if user[2] else 1
        await self.db.execute(
            "UPDATE users SET is_banned = ? WHERE user_id = ?",
            (new_status, user_id)
        )
        await self.db.commit()
        return new_status

    async def get_all_users(self):
        async with self.db.execute(
            "SELECT user_id FROM users WHERE is_banned = 0 AND is_blocked = 0"
        ) as cursor:
            return await cursor.fetchall()
    
    async def add_video(self, file_id: str):
        await self.db.execute(
            "INSERT INTO videos (file_id) VALUES (?)",
            (file_id,)
        )
        await self.db.commit()

    async def get_random_video(self):
        async with self.db.execute(
            "SELECT file_id FROM videos ORDER BY RANDOM() LIMIT 1"
        ) as cursor:
            return await cursor.fetchone()

    async def get_stats(self):
    # Общее количество пользователей
        async with self.db.execute("SELECT COUNT(*) FROM users WHERE is_blocked = 0") as cursor:
            total_users = (await cursor.fetchone())[0]

    # Сумма всех монет
        async with self.db.execute("SELECT SUM(coins) FROM users") as cursor:
            total_coins = (await cursor.fetchone())[0] or 0

    # Количество видео
        async with self.db.execute("SELECT COUNT(*) FROM videos") as cursor:
            total_videos = (await cursor.fetchone())[0]

        return total_users, total_coins, total_videos

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "database.db")

db = Database(db_path)




# ================== BOT ==================

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

from aiogram.filters import Command




# ================== KEYBOARDS ==================

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👁 Смотреть", callback_data="watch"),
            InlineKeyboardButton(text="👤 Профиль", callback_data="profile"),
        ],
        [InlineKeyboardButton(text="⭐ Купить монеты", callback_data="buy_menu")],
        [InlineKeyboardButton(text="👥 Пригласить", callback_data="ref_link")],
        [InlineKeyboardButton(text="📝 Задания", callback_data="tasks")],
        [
            InlineKeyboardButton(
                text="🆘 Поддержка",
                url=f"https://t.me/{SUPPORT_USERNAME}"
            )
        ],
    ])

def content_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Видео (10)", callback_data="video")],
        [InlineKeyboardButton(text="📸 Фото (5)", callback_data="photo")],
    ])



def admin_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Выдать монеты", callback_data="give")],
        [InlineKeyboardButton(text="⛔ Бан / Разбан", callback_data="ban")],
        [InlineKeyboardButton(text="➕ Сделать админом", callback_data="make_admin")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="broadcast")],  # ← добавили
        [InlineKeyboardButton(text="📝 Сменить имя бота", callback_data="bot_name")],
        [InlineKeyboardButton(text="💬 Сменить описание бота", callback_data="bot_desc")],
        [InlineKeyboardButton(text="📤 Загрузить видео", callback_data="upload_video")],
    ])

# ================== STATES ==================

class AdminStates(StatesGroup):
    give_user = State()
    give_amount = State()
    ban_user = State()
    new_admin = State()
    upload_video = State()

    change_bot_name = State()
    change_bot_description = State()

    broadcast_message = State()  # ← новое


# ================== USER ==================

@dp.message(CommandStart())
async def start(message: Message):



    args = message.text.split()

    referrer_id = None

    # Если есть реферальный код
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
        except:
            referrer_id = None

    # Нельзя пригласить самого себя
    if referrer_id == message.from_user.id:
        referrer_id = None

    # Добавляем пользователя
    is_new = await db.add_user(message.from_user.id, referrer_id)

    user = await db.get_user(message.from_user.id)

    if user[2]:  # is_banned
        return await message.answer("⛔ Вы забанены")

    # Если пользователь новый и есть реферер
    if is_new and referrer_id:
        ref_user = await db.get_user(referrer_id)

        if ref_user:
            # Начисляем обоим по 5
            await db.update_coins(message.from_user.id, 5)
            await db.update_coins(referrer_id, 5)

            try:
                await bot.send_message(
                    referrer_id,
                    "🎉 По вашей ссылке зарегистрировался пользователь!\n"
                    "💰 Вам начислено 5 монет"
                )
            except:
                pass

    await message.answer(
        f"👋 Привет, {message.from_user.first_name}!",
        reply_markup=main_menu()
    )

    await send_log(message, "Зашёл в бота")


@dp.callback_query(F.data == "watch")
async def watch(callback: CallbackQuery):
    await callback.message.answer("Выберите контент:", reply_markup=content_menu())
    await callback.answer()


@dp.callback_query(F.data == "video")
async def send_random_video(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    cost = 10

    if user[1] < cost:
        await callback.message.answer("❌ Недостаточно монет")
        return

    video = await db.get_random_video()

    if not video:
        await callback.message.answer("❌ Видео пока нет")
        return

    await db.update_coins(callback.from_user.id, -cost)

    await bot.send_video(
        callback.from_user.id,
        video[0]
    )

    # ===== ЛОГ ПОКУПКИ ВИДЕО =====
    await send_log(callback, f"Купил видео за {cost} монет")

    await callback.answer()







@dp.callback_query(F.data == "profile")
async def profile(callback: CallbackQuery):
    user = await db.get_user(callback.from_user.id)
    text = f"""
👤 <b>Профиль</b>
💰 Монеты: {user[1]}
👑 Админ: {"Да" if user[3] else "Нет"}
"""
    await callback.message.answer(text)
    await callback.answer()


@dp.callback_query(F.data == "buy_menu")
async def buy_menu(callback: CallbackQuery):
    support_username = SUPPORT_USERNAME  # username для получения подарков

    text = (
        f"💰 Для покупки монет отправляйте подарок на профиль @dashqaz\n\n"
        "1 монета = 1,5 ⭐\n"
        "После отправки напишите скриншот в поддержку, чтобы вам начислили монеты."
    )

    await callback.message.answer(text)
    await callback.answer()



@dp.callback_query(F.data == "ref_link")
async def ref_link(callback: CallbackQuery):
    bot_info = await bot.get_me()
    ref_url = f"https://t.me/{bot_info.username}?start={callback.from_user.id}"

    await callback.message.answer(
        f"👥 <b>Ваша реферальная ссылка:</b>\n\n"
        f"{ref_url}\n\n"
        f"💰 За каждого приглашённого вы и он получите по 5 монет!"
    )

    await callback.answer()









@dp.callback_query(F.data == "tasks")
async def show_tasks(callback: CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Задание 1: 15 комментариев — 100 монет", callback_data="task_1")],
        [InlineKeyboardButton(text="Задание 2: 10 видео — 500 монет", callback_data="task_2")],
        [InlineKeyboardButton(text="⬅ Назад", callback_data="main_menu")]
    ])

    await callback.message.answer("📝 Доступные задания:", reply_markup=keyboard)
    await callback.answer()


@dp.callback_query(F.data == "task_1")
async def task_1_details(callback: CallbackQuery):
    text = (
        f"📝 <b>Задание 1</b>\n"
        f"Напишите 15 комментариев с упоминанием юзернейма нашего бота.\n"
        f"Награда: 100 монет после проверки.\n\n"
        f"📸 Для подтверждения пришлите скриншот в поддержку: @{SUPPORT_USERNAME}"
    )
    await callback.message.answer(text)

    # ---- Логирование ----
    await send_log(callback, "Открыл Задание 1")  # <-- сюда
    await callback.answer()


@dp.callback_query(F.data == "task_2")
async def task_2_details(callback: CallbackQuery):
    text = (
        f"📝 <b>Задание 2</b>\n"
        f"Выложите 10 видео с упоминанием юзернейма нашего бота.\n"
        f"Награда: 500 монет после проверки.\n\n"
        f"📸 Для подтверждения пришлите скриншот в поддержку: @{SUPPORT_USERNAME}"
    )
    await callback.message.answer(text)

    # ---- Логирование ----
    await send_log(callback, "Открыл Задание 2")  # <-- сюда
    await callback.answer()



@dp.callback_query(F.data == "main_menu")
async def go_main_menu(callback: CallbackQuery):
    await callback.message.answer("Главное меню:", reply_markup=main_menu())
    await callback.answer()




@dp.callback_query(F.data == "broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.broadcast_message)
    await callback.message.answer("📢 Введите сообщение для рассылки:")
    await callback.answer()

@dp.message(AdminStates.broadcast_message)
async def broadcast_send(message: Message, state: FSMContext):
    users = await db.get_all_users()
    sent = 0
    failed = 0

    for user in users:
        try:
            await bot.send_message(user[0], message.text)
            await asyncio.sleep(0.05)
            sent += 1

        except TelegramForbiddenError:
            failed += 1

            # пользователь заблокировал бота
            await db.db.execute(
                "UPDATE users SET is_blocked = 1 WHERE user_id = ?",
                (user[0],)
            )
            await db.db.commit()

        except Exception:
            failed += 1

    await message.answer(
        f"✅ Рассылка завершена\n\n"
        f"Отправлено: {sent}\n"
        f"Не удалось: {failed}"
    )

    await state.clear()



# ================== ADMIN ==================

@dp.message(Command("admin"))
async def admin_panel(message: Message):
    # Если это главный админ — всегда пускаем
    if message.from_user.id == ADMIN_ID:
        return await message.answer(
            "⚙ Админ-панель:",
            reply_markup=admin_menu()
        )

    # Остальные проверяются через базу
    user = await db.get_user(message.from_user.id)

    if not user or user[3] == 0:  # user[3] = is_admin
        return await message.answer("⛔ Нет доступа")

    await message.answer(
        "⚙ Админ-панель:",
        reply_markup=admin_menu()
    )

@dp.message(Command("stats"))
async def show_stats(message: Message):
    # Проверка: только админ или пользователь с is_admin = 1
    if message.from_user.id != ADMIN_ID:
        user = await db.get_user(message.from_user.id)
        if not user or user[3] == 0:  # user[3] = is_admin
            return await message.answer("⛔ Нет доступа")

    total_users, total_coins, total_videos = await db.get_stats()
    text = (
        f"📊 <b>Статистика бота</b>\n\n"
        f"👥 Пользователи: {total_users}\n"
        f"💰 Всего монет: {total_coins}\n"
        f"🎬 Видео: {total_videos}"
    )
    await message.answer(text)

@dp.callback_query(F.data == "give")
async def give_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.give_user)
    await callback.message.answer("Введите ID пользователя:")
    await callback.answer()

@dp.callback_query(F.data == "upload_video")
async def upload_video_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("Нет доступа", show_alert=True)

    await state.set_state(AdminStates.upload_video)
    await callback.message.answer(
        "📤 Отправляйте видео (можно несколько подряд).\nДля выхода напишите /cancel"
    )
    await callback.answer()

@dp.message(AdminStates.upload_video, F.video)
async def save_video(message: Message):
    file_id = message.video.file_id
    await db.add_video(file_id)
    await message.answer("✅ Видео сохранено")


@dp.callback_query(F.data == "photo")
async def send_photo(callback: CallbackQuery):
    await callback.message.answer("Функция фото пока не реализована")
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_upload(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Загрузка завершена")

@dp.message(AdminStates.give_user)
async def give_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
    except:
        return await message.answer("❌ Введите числовой ID")

    await state.update_data(user_id=user_id)
    await state.set_state(AdminStates.give_amount)
    await message.answer("Введите количество монет:")


@dp.message(AdminStates.give_amount)
async def give_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    await db.update_coins(data["user_id"], int(message.text))
    await message.answer("✅ Монеты выданы")
    await state.clear()


@dp.callback_query(F.data == "ban")
async def ban_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.ban_user)
    await callback.message.answer("Введите ID пользователя:")
    await callback.answer()


@dp.message(AdminStates.ban_user)
async def ban_process(message: Message, state: FSMContext):
    status = await db.ban_toggle(int(message.text))
    if status is None:
        await message.answer("Пользователь не найден")
    else:
        await message.answer("✅ Разбанен" if status == 0 else "⛔ Забанен")
    await state.clear()


@dp.callback_query(F.data == "make_admin")
async def make_admin_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.new_admin)
    await callback.message.answer("Введите ID пользователя:")
    await callback.answer()


@dp.message(AdminStates.new_admin)
async def make_admin_process(message: Message, state: FSMContext):
    await db.set_admin(int(message.text))
    await message.answer("👑 Пользователь теперь админ")
    await state.clear()
    

@dp.callback_query(F.data == "bot_name")
async def change_bot_name_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.change_bot_name)
    await callback.message.answer("Введите новое имя бота:")
    await callback.answer()


@dp.message(AdminStates.change_bot_name)
async def change_bot_name_process(message: Message, state: FSMContext):
    try:
        await bot.set_my_name(name=message.text)
        await message.answer("✅ Имя бота обновлено")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

    await state.clear()


@dp.callback_query(F.data == "bot_desc")
async def change_bot_desc_start(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AdminStates.change_bot_description)
    await callback.message.answer("Введите новое описание бота:")
    await callback.answer()


@dp.message(AdminStates.change_bot_description)
async def change_bot_desc_process(message: Message, state: FSMContext):
    try:
        await bot.set_my_description(description=message.text)
        await message.answer("✅ Описание бота обновлено")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

    await state.clear()







# ================== MAIN ==================
async def main():
    await db.connect()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

