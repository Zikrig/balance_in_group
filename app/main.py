import re
import asyncio
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from app.config import BOT_TOKEN, DB_URL
from app.database import Database
from app.filters import IsAdmin

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database(DB_URL)

USER_COMMANDS = """
🤖 Банковский бот - список команд:

📋 Для всех пользователей:
!Банк - Показать личный счет

💡 Просто скопируйте нужную команду и отправьте в чат
"""

ADMIN_COMMANDS = """
👑 Администраторские команды:

!Изменить баланс Очков Клуба на [число] @username - Изменить очки клуба
!Изменить баланс Кредитного рейтинга на [число] @username - Изменить кредитный рейтинг
/банк_статистика - Показать статистику всех пользователей

💡 Примеры:
!Изменить баланс Очков Клуба на 100 @ivanov
!Изменить баланс Кредитного рейтинга на -50 @petrov
"""

@dp.message(IsAdmin(), F.text.startswith("/start"))
async def start_handler(message: Message):
    response = USER_COMMANDS + "\n\n" + ADMIN_COMMANDS
    await message.answer(response)

@dp.message(F.text.startswith("/start"))
async def start_handler(message: Message):
    response = USER_COMMANDS
    await message.answer(response)
    

@dp.message(F.text.startswith("!"))
async def show_bank(message: Message):
    if not message.text.lower() in ['! банк', '!банк']:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or f"пользователь (ID: {user_id})"
    
    await db.create_user(user_id, message.from_user.username or "")
    user = await db.get_user(user_id)
    
    # Проверяем, что все поля существуют
    club_points = user.get('club_points', 0)
    credit_rating = user.get('credit_rating', 0)
    
    response = (
        f"🏦 Личный счёт пользователя {username}\n\n"
        f"🪙 Счёт Очков Клуба: {club_points}\n"
        f"💹 Кредитный рейтинг: {credit_rating}"
    )
    
    await message.reply(response)

@dp.message(IsAdmin(), F.text.startswith("!Изменить баланс Очков Клуба на"))
async def update_club_points(message: Message):
    # Парсим команду: "!Изменить баланс Очков Клуба на 100 @username"
    pattern = r"!Изменить баланс Очков Клуба на (-?\d+) @(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        await message.reply("❌ Неправильный формат команды. Пример: !Изменить баланс Очков Клуба на 100 @username")
        return
    
    points = int(match.group(1))
    username = match.group(2)
    
    user = await db.get_user_by_username(username)
    if not user:
        await message.reply(f"❌ Пользователь @{username} не найден в базе данных")
        return
    
    await db.update_club_points(user['tg_id'], points)
    await message.reply(f"✅ Баланс Очков Клуба пользователя @{username} изменен на {points}")

@dp.message(IsAdmin(), F.text.startswith("!Изменить баланс Кредитного рейтинга на"))
async def update_credit_rating(message: Message):
    # Парсим команду: "!Изменить баланс Кредитного рейтинга на 50 @username"
    pattern = r"!Изменить баланс Кредитного рейтинга на (-?\d+) @(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        await message.reply("❌ Неправильный формат команды. Пример: !Изменить баланс Кредитного рейтинга на 50 @username")
        return
    
    rating = int(match.group(1))
    username = match.group(2)
    
    user = await db.get_user_by_username(username)
    if not user:
        await message.reply(f"❌ Пользователь @{username} не найден в базе данных")
        return
    
    await db.update_credit_rating(user['tg_id'], rating)
    await message.reply(f"✅ Кредитный рейтинг пользователя @{username} изменен на {rating}")

@dp.message(IsAdmin(), Command("банк_статистика"))
async def show_bank_stats(message: Message):
    users = await db.get_all_users()
    
    response = "📊 Статистика банка:\n\n"
    for user in users:
        username_display = f"@{user['username']}" if user.get('username') else f"ID: {user['tg_id']}"
        club_points = user.get('club_points', 0)
        credit_rating = user.get('credit_rating', 0)
        response += f"👤 {username_display}: 🪙 {club_points} | 💹 {credit_rating}\n"
    
    await message.reply(response)

async def main():
    await db.connect()
    await db.create_table()  # Это обновит структуру таблицы при необходимости
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())