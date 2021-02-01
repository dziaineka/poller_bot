import logging

from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.utils import executor
from aiogram.utils.exceptions import MessageNotModified

import config

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)


async def welcome(message: types.Message):
    text = "Hello it's poller bot.\n\n" \
        "It doesn't imply any interaction to you.\n\n" \
        "Deploy your own copy if you want the same functionality."

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    github_button = types.InlineKeyboardButton(
        text='Github',
        url='https://github.com/dziaineka/poller_bot')

    dockerhub_button = types.InlineKeyboardButton(
        text='Dockerhub',
        url='https://hub.docker.com/repository/docker/skaborik/poller_bot')

    keyboard.add(github_button, dockerhub_button)

    await bot.send_message(message.chat.id,
                           text,
                           reply_markup=keyboard)


@dp.message_handler(content_types=types.ContentTypes.ANY, state='*')
async def empty_state(message: types.Message):
    await welcome(message)


if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)
