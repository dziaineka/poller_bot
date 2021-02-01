import asyncio
import functools
import logging
from datetime import datetime
from typing import Callable
from aiogram.dispatcher.storage import FSMContext

import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.utils import executor

import config
from scheduler import Scheduler

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
last_channel_poll = None


async def welcome(message: types.Message):
    text = "Привет, этот бот создает опрос по расписанию.\n\n" \
        "Чтобы завести себе такого же, нужно поднять собственную копию бота."

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    github_button = types.InlineKeyboardButton(
        text='Github',
        url='https://github.com/dziaineka/poller_bot')

    keyboard.add(github_button)

    await bot.send_message(message.chat.id,
                           text,
                           reply_markup=keyboard)


@dp.message_handler(commands=['force'])
async def cmd_force_poll(message: types.Message, state: FSMContext):
    logging.info('Forced polling - ' +
                 f'{str(message.from_user.id)}:{message.from_user.username}')

    await post_poll()


@dp.message_handler(content_types=types.ContentTypes.POLL, state='*')
async def set_message_to_repeat(message: types.Message):
    if str(message.from_user.id) not in config.ADMINS:
        return

    global last_channel_poll
    last_channel_poll = message.forward_from_message_id

    text = "Этот опрос будет показан в следующий раз при повторе " \
        "по расписанию."

    await bot.send_message(message.chat.id, text)


@dp.message_handler(content_types=types.ContentTypes.ANY, state='*')
async def any_message(message: types.Message):
    await welcome(message)


def get_today() -> str:
    tz_minsk = pytz.timezone(config.TIMEZONE)
    current_datetime = datetime.now(tz_minsk)
    day = str(current_datetime.day).rjust(2, '0')
    month = str(current_datetime.month).rjust(2, '0')
    year = str(current_datetime.year)

    return f'{day}.{month}.{year}'


def safe(func: Callable):
    @functools.wraps(func)
    async def log_exception():
        try:
            await func()
        except Exception:
            logging.exception("Something went wrong.")

    return log_exception


@safe
async def post_poll():
    question = f'{config.QUESTION} ({get_today()})'

    poll = await bot.send_poll(chat_id=config.CHANNEL_NAME,
                               question=question,
                               options=config.ANSWERS)

    await bot.forward_message(chat_id=config.GROUP_NAME,
                              from_chat_id=config.CHANNEL_NAME,
                              message_id=poll.message_id,
                              disable_notification=False)

    global last_channel_poll
    last_channel_poll = poll.message_id


@safe
async def repeat_poll():
    global last_channel_poll

    if last_channel_poll:
        await bot.forward_message(chat_id=config.GROUP_NAME,
                                  from_chat_id=config.CHANNEL_NAME,
                                  message_id=last_channel_poll,
                                  disable_notification=False)


async def startup(_):
    schdlr = Scheduler(post_poll, repeat_poll)
    asyncio.create_task(schdlr.start())


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=startup)
