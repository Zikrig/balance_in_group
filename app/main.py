import re
import asyncio
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import Command
from app.config import BOT_TOKEN, DB_URL
from app.database import Database
from app.filters import IsAdmin

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
db = Database(DB_URL)

# Добавим в ADMIN_COMMANDS описание новых команд
ADMIN_COMMANDS = """
👑 Администраторские команды:

Изменить баланс Очков Клуба на [число] @username - Изменить очки клуба
Изменить баланс Кредитного рейтинга на [число] @username - Изменить кредитный рейтинг
Добавить Очки Клуба [число] @username - Добавить очки клуба
Убрать Очки Клуба [число] @username - Убрать очки клуба
Добавить Кредитный рейтинг [число] @username - Добавить кредитный рейтинг
Убрать Кредитный рейтинг [число] @username - Убрать кредитный рейтинг
Удалить пользователя @username - Удалить пользователя
/банк_статистика - Показать статистику всех пользователей

💡 Примеры:
Изменить баланс Очков Клуба на 100.5 @ivanov
Добавить Очки Клуба 50 @petrov
Удалить пользователя @noname
"""

USER_COMMANDS = """
🤖 Банковский бот - список команд:

📋 Для всех пользователей:
!Банк - Показать личный счет

💡 Просто скопируйте нужную команду и отправьте в чат
"""


@dp.message(IsAdmin(), F.text.startswith("/start"))
async def start_handler(message: Message):
    response = USER_COMMANDS + "\n\n" + ADMIN_COMMANDS
    await message.answer(response)

@dp.message(F.text.startswith("/start"))
async def start_handler(message: Message):
    response = USER_COMMANDS
    await message.answer(response)
    
# Обработчик удаления пользователя
@dp.message(IsAdmin(), F.text.startswith("Удалить пользователя"))
async def delete_user_cmd(message: Message):
    pattern = r"Удалить пользователя @(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        await message.reply("❌ Неправильный формат команды. Пример: Удалить пользователя @username")
        return
    
    username = match.group(1)
    user = await db.get_user_by_username(username)
    
    if not user:
        await message.reply(f"❌ Пользователь @{username} не найден")
        return
    
    await db.delete_user(user['tg_id'])
    await message.reply(f"✅ Пользователь @{username} удален")

# Обработчики для добавления/убавления баллов
@dp.message(IsAdmin(), F.text.startswith("Добавить Очки Клуба"))
async def add_club_points(message: Message):
    await adjust_points(message, "club_points", 1)

@dp.message(IsAdmin(), F.text.startswith("Убрать Очки Клуба"))
async def remove_club_points(message: Message):
    await adjust_points(message, "club_points", -1)

@dp.message(IsAdmin(), F.text.startswith("Добавить Кредитный рейтинг"))
async def add_credit_rating(message: Message):
    await adjust_points(message, "credit_rating", 1)

@dp.message(IsAdmin(), F.text.startswith("Убрать Кредитный рейтинг"))
async def remove_credit_rating(message: Message):
    await adjust_points(message, "credit_rating", -1)

# Общая функция для изменения баллов
async def adjust_points(message: Message, field: str, multiplier: int):
    pattern = rf"(Добавить|Убрать) {'Очки Клуба' if 'Очки' in message.text else 'Кредитный рейтинг'}\s+([-+]?\d*\.?\d+)\s+@(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        await message.reply(f"❌ Неправильный формат команды. Пример: {'Добавить' if multiplier > 0 else 'Убрать'} {'Очки Клуба' if field == 'club_points' else 'Кредитный рейтинг'} 50 @username")
        return
    
    points = float(match.group(2)) * multiplier
    username = match.group(3)
    
    user = await db.get_user_by_username(username)
    if not user:
        await message.reply(f"❌ Пользователь @{username} не найден")
        return
    
    current_value = user.get(field, 0)
    new_value = current_value + points
    
    if field == 'club_points':
        await db.update_club_points(user['tg_id'], new_value)
    else:
        await db.update_credit_rating(user['tg_id'], new_value)
    
    await message.reply(f"✅ {'Добавлено' if multiplier > 0 else 'Убрано'} {abs(points):.2f} {'очков клуба' if field == 'club_points' else 'кредитного рейтинга'} пользователю @{username}. Новое значение: {new_value:.2f}")
    

@dp.message(F.text.startswith("!"))
async def show_bank(message: Message):
    if not message.text.lower() in ['! банк', '!банк']:
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or f"пользователь (ID: {user_id})"
    
    await db.create_user(user_id, message.from_user.username or "")
    user = await db.get_user(user_id)
    
    club_points = user.get('club_points', 0)
    credit_rating = user.get('credit_rating', 0)
    
    response = (
        f"🏦 Личный счёт пользователя {username}\n\n"
        f"🪙 Счёт Очков Клуба: {club_points:.2f}\n"
        f"💹 Кредитный рейтинг: {credit_rating:.2f}"
    )
    
    await message.reply(response)

@dp.message(IsAdmin(), F.text.startswith("Изменить баланс Очков Клуба на"))
async def update_club_points(message: Message):
    logger.info(f"Получена команда: {message.text}")
    
    # Более гибкое регулярное выражение
    pattern = r"Изменить баланс Очков Клуба на\s+([-+]?\d*\.?\d+)\s+@(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        logger.error(f"Не удалось распарсить команду: {message.text}")
        await message.reply("❌ Неправильный формат команды. Пример: Изменить баланс Очков Клуба на 100.5 @username")
        return
    
    points = float(match.group(1))
    username = match.group(2)
    logger.info(f"Распаршено: points={points}, username={username}")
    
    user = await db.get_user_by_username(username)
    if not user:
        logger.error(f"Пользователь @{username} не найден в базе данных")
        await message.reply(f"❌ Пользователь @{username} не найден в базе данных")
        return
    
    await db.update_club_points(user['tg_id'], points)
    logger.info(f"Обновлены очки клуба для @{username}: {points}")
    await message.reply(f"✅ Баланс Очков Клуба пользователя @{username} изменен на {points:.2f}")

@dp.message(IsAdmin(), F.text.startswith("Изменить баланс Кредитного рейтинга на"))
async def update_credit_rating(message: Message):
    logger.info(f"Получена команда: {message.text}")
    
    # Более гибкое регулярное выражение
    pattern = r"Изменить баланс Кредитного рейтинга на\s+([-+]?\d*\.?\d+)\s+@(\w+)"
    match = re.search(pattern, message.text)
    
    if not match:
        logger.error(f"Не удалось распарсить команду: {message.text}")
        await message.reply("❌ Неправильный формат команды. Пример: Изменить баланс Кредитного рейтинга на 50.25 @username")
        return
    
    rating = float(match.group(1))
    username = match.group(2)
    logger.info(f"Распаршено: rating={rating}, username={username}")
    
    user = await db.get_user_by_username(username)
    if not user:
        logger.error(f"Пользователь @{username} не найден в базе данных")
        await message.reply(f"❌ Пользователь @{username} не найден в базе данных")
        return
    
    await db.update_credit_rating(user['tg_id'], rating)
    logger.info(f"Обновлен кредитный рейтинг для @{username}: {rating}")
    await message.reply(f"✅ Кредитный рейтинг пользователя @{username} изменен на {rating:.2f}")

@dp.message(IsAdmin(), Command("банк_статистика"))
async def show_bank_stats(message: Message):
    users = await db.get_all_users()
    
    response = "📊 Статистика банка:\n\n"
    for user in users:
        username_display = f"@{user['username']}" if user.get('username') else f"ID: {user['tg_id']}"
        club_points = user.get('club_points', 0)
        credit_rating = user.get('credit_rating', 0)
        response += f"👤 {username_display}: 🪙 {club_points:.2f} | 💹 {credit_rating:.2f}\n"
    
    await message.reply(response)

async def main():
    logger.info("Запуск бота...")
    await db.connect()
    await db.create_table()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())