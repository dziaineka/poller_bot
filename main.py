import asyncio
import functools
import logging
import sys
from datetime import datetime
from typing import Callable, Optional

import aioschedule as schedule
import pytz
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.storage import FSMContext
from aiogram.utils import executor

import config

logging.basicConfig(
    stream=sys.stdout,
    level=config.LOGGING_LEVEL,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger("parkun_bot")

bot = Bot(token=config.BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# Allow bot to forward poll without counting threshold
# (becouse counter resets at restart)
messages_after_last_poll_counter = config.GROUP_MESSAGES_COUNT_THRESHOLD


async def welcome(message: types.Message):
    logger.info('Welcome - ' +
                f'{str(message.from_user.id)}:{message.from_user.username}')

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


@dp.message_handler(content_types=types.ContentTypes.ANY, state='*')
async def any_message(message: types.Message):
    logger.debug(f"Message from chat {message.chat.username}")

    if message.chat.username == config.GROUP_NAME.removeprefix('@'):
        global messages_after_last_poll_counter
        messages_after_last_poll_counter += 1

        logger.debug("Counter updated to "
                     f"{str(messages_after_last_poll_counter)}")
        return

    await welcome(message)


@dp.message_handler(commands=['force'])
async def cmd_force_poll(message: types.Message, state: FSMContext):
    logger.info('Forced polling - ' +
                f'{str(message.from_user.id)}:{message.from_user.username}')
    if str(message.from_user.id) in config.ADMINS:
        await post_poll()


@dp.message_handler(content_types=types.ContentTypes.POLL, state='*')
async def set_message_to_repeat(message: types.Message):
    if str(message.from_user.id) not in config.ADMINS:
        return

    text = f"Чтобы этот пост был показан в следующий раз по расписанию " \
        f"нужно запинить его в канале {config.CHANNEL_NAME}."

    await bot.send_message(message.chat.id, text)


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
            logger.exception("Something went wrong.")

    return log_exception


@safe
async def post_poll():
    logger.info("New poll time")
    question = f'{config.QUESTION} ({get_today()})'

    await maybe_unpin_previous_poll()

    poll = await bot.send_poll(chat_id=config.CHANNEL_NAME,
                               question=question,
                               options=config.ANSWERS,
                               disable_notification=True)

    await bot.pin_chat_message(chat_id=config.CHANNEL_NAME,
                               message_id=poll.message_id,
                               disable_notification=True)

    # delete info message about pin action
    await bot.delete_message(chat_id=config.CHANNEL_NAME,
                             message_id=poll.message_id+1)

    await bot.forward_message(chat_id=config.GROUP_NAME,
                              from_chat_id=config.CHANNEL_NAME,
                              message_id=poll.message_id,
                              disable_notification=False)

    logger.debug(f"New poll posted. Id - {poll.message_id}")

    global messages_after_last_poll_counter
    messages_after_last_poll_counter = 0


async def maybe_unpin_previous_poll():
    last_channel_poll = await get_last_channel_post()

    try:
        await bot.unpin_chat_message(chat_id=config.CHANNEL_NAME,
                                     message_id=last_channel_poll)

        logger.debug(f"Post unpinned. Id - {last_channel_poll}")
    except Exception:
        logger.exception("Unpin failed this time.")


@safe
async def repeat_poll():
    logger.info(f"Repeating poll")
    last_channel_poll = await get_last_channel_post()

    if not last_channel_poll:
        logger.debug(f"Can't find pinned post. Id - {last_channel_poll}")

        text = f"Не смог найти в канале {config.CHANNEL_NAME} запиненное " \
            "сообщение, чтобы отфорвардить 🤷‍♂️"

        for admin in config.ADMINS:
            await bot.send_message(admin, text)

        return

    global messages_after_last_poll_counter

    forwarding_allowed = \
        messages_after_last_poll_counter >= \
        config.GROUP_MESSAGES_COUNT_THRESHOLD

    logger.debug(f"Try to forward. Id - {last_channel_poll}. "
                 f"Threshold - {messages_after_last_poll_counter}")

    if last_channel_poll and forwarding_allowed:
        await bot.forward_message(chat_id=config.GROUP_NAME,
                                  from_chat_id=config.CHANNEL_NAME,
                                  message_id=last_channel_poll,
                                  disable_notification=False)

        messages_after_last_poll_counter = 0

        logger.debug(f"Post forwarded. Id - {last_channel_poll}")


async def get_last_channel_post() -> Optional[int]:
    chat_info = await bot.get_chat(config.CHANNEL_NAME)

    if chat_info.pinned_message:
        return chat_info.pinned_message.message_id

    return None


async def start_scheduler(post_poll: Callable, repeat_poll: Callable):
    logger.info('Scheduler started')

    for action_time in config.NEW_POLL_TIMES:
        schedule.every().day.at(action_time).do(post_poll)

    for repeat_time in config.REPEAT_POLL_TIMES:
        schedule.every().day.at(repeat_time).do(repeat_poll)

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)


async def startup(_):
    asyncio.create_task(start_scheduler(post_poll, repeat_poll))


if __name__ == '__main__':
    executor.start_polling(dp,
                           skip_updates=True,
                           on_startup=startup)
