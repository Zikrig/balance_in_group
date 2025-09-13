from aiogram.filters import Filter
from aiogram.types import Message
from app.config import ADMINS

class IsAdmin(Filter):
    def __init__(self):
        pass

    async def __call__(self, message: Message) -> bool:
        return message.from_user.id in ADMINS