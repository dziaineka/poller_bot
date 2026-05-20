import asyncio
import functools
import logging
import sys
from datetime import datetime
from typing import Awaitable, Callable, Optional
from zoneinfo import ZoneInfo

import aioschedule as schedule
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ContentType
from aiogram.filters import Command
from aiogram.fsm.storage.memory import MemoryStorage

import config
from stats import Stats

logging.basicConfig(
    stream=sys.stdout,
    level=config.LOGGING_LEVEL,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger("poller_bot")

bot = Bot(token=config.BOT_TOKEN)

storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Allow bot to forward poll without counting threshold
# (because counter resets at restart)
messages_after_last_poll_counter = config.GROUP_MESSAGES_COUNT_THRESHOLD


@dp.message(Command("stats"))
async def cmd_post_stats(message: types.Message):
    logger.info(
        "Post stats command - "
        + f"{str(message.from_user.id)}:{message.from_user.username}"
    )
    # https://github.com/LonamiWebs/Telethon/issues/1634#issuecomment-1280611854
    tasks = []
    tasks.append(asyncio.create_task(Stats().post(bot)))


@dp.message(Command("force"))
async def cmd_force_poll(message: types.Message):
    logger.info(
        "Forced polling - "
        + f"{str(message.from_user.id)}:{message.from_user.username}"
    )
    if str(message.from_user.id) in config.ADMINS:
        await post_poll()


async def welcome(message: types.Message):
    logger.info(
        "Welcome - "
        + f"{str(message.from_user.id)}:{message.from_user.username}"
    )

    text = (
        "Привет, этот бот создает опрос по расписанию.\n\n"
        "Чтобы завести себе такого же, нужно поднять собственную копию бота."
    )

    keyboard = types.InlineKeyboardMarkup(row_width=1)

    github_button = types.InlineKeyboardButton(
        text="Github", url="https://github.com/dziaineka/poller_bot"
    )

    keyboard.add(github_button)

    await bot.send_message(message.chat.id, text, reply_markup=keyboard)


@dp.message(F.content_type == ContentType.POLL)
async def set_message_to_repeat(message: types.Message):
    if str(message.from_user.id) not in config.ADMINS:
        return

    text = (
        f"Чтобы этот пост был показан в следующий раз по расписанию "
        f"нужно запинить его в канале {config.CHANNEL_NAME}."
    )

    await bot.send_message(message.chat.id, text)


@dp.message()
async def any_message(message: types.Message):
    logger.debug(f"Message from chat {message.chat.username}")

    if message.chat.username == config.GROUP_NAME.removeprefix("@"):
        global messages_after_last_poll_counter
        messages_after_last_poll_counter += 1

        logger.debug(
            "Counter updated to " f"{str(messages_after_last_poll_counter)}"
        )
        return

    await welcome(message)


def get_today() -> str:
    current_datetime = datetime.now(ZoneInfo(config.TIMEZONE))
    day = str(current_datetime.day).rjust(2, "0")
    month = str(current_datetime.month).rjust(2, "0")
    year = str(current_datetime.year)

    return f"{day}.{month}.{year}"


def safe(func: Callable[[], Awaitable[None]]) -> Callable[[], Awaitable[None]]:
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
    question = f"{config.QUESTION} ({get_today()})"

    await maybe_unpin_previous_poll()

    poll = await bot.send_poll(
        chat_id=config.CHANNEL_NAME,
        question=question,
        options=config.ANSWERS,
        disable_notification=True,
    )

    await bot.pin_chat_message(
        chat_id=config.CHANNEL_NAME,
        message_id=poll.message_id,
        disable_notification=True,
    )

    # delete info message about pin action
    await bot.delete_message(
        chat_id=config.CHANNEL_NAME, message_id=poll.message_id + 1
    )

    await bot.forward_message(
        chat_id=config.GROUP_NAME,
        from_chat_id=config.CHANNEL_NAME,
        message_id=poll.message_id,
        disable_notification=False,
    )

    logger.debug(f"New poll posted. Id - {poll.message_id}")

    global messages_after_last_poll_counter
    messages_after_last_poll_counter = 0


async def maybe_unpin_previous_poll():
    last_channel_poll = await get_last_channel_post()

    try:
        await bot.unpin_chat_message(
            chat_id=config.CHANNEL_NAME, message_id=last_channel_poll
        )

        logger.debug(f"Post unpinned. Id - {last_channel_poll}")
    except Exception:
        logger.exception("Unpin failed this time.")


@safe
async def repeat_poll():
    logger.info(f"Repeating poll")
    last_channel_poll = await get_last_channel_post()

    if not last_channel_poll:
        logger.debug(f"Can't find pinned post. Id - {last_channel_poll}")

        text = (
            f"Не смог найти в канале {config.CHANNEL_NAME} запиненное "
            "сообщение, чтобы отфорвардить 🤷‍♂️"
        )

        for admin in config.ADMINS:
            await bot.send_message(admin, text)

        return

    global messages_after_last_poll_counter

    forwarding_allowed = (
        messages_after_last_poll_counter
        >= config.GROUP_MESSAGES_COUNT_THRESHOLD
    )

    logger.debug(
        f"Try to forward. Id - {last_channel_poll}. "
        f"Threshold - {messages_after_last_poll_counter}"
    )

    if last_channel_poll and forwarding_allowed:
        await bot.forward_message(
            chat_id=config.GROUP_NAME,
            from_chat_id=config.CHANNEL_NAME,
            message_id=last_channel_poll,
            disable_notification=False,
        )

        messages_after_last_poll_counter = 0

        logger.debug(f"Post forwarded. Id - {last_channel_poll}")


@safe
async def maybe_post_stats():
    if Stats.time_to_post():
        # We create Stats instance every time when post because posting
        # stats is rare occasion (once a month by default)
        # IMHO no need to keep underlying telegram client
        # instance in memory all the time
        await Stats().post(bot)


async def get_last_channel_post() -> Optional[int]:
    chat_info = await bot.get_chat(config.CHANNEL_NAME)

    if chat_info.pinned_message:
        return chat_info.pinned_message.message_id

    return None


async def start_scheduler():
    logger.info("Scheduler started")

    for action_time in config.NEW_POLL_TIMES:
        schedule.every().day.at(action_time).do(post_poll)

    for repeat_time in config.REPEAT_POLL_TIMES:
        schedule.every().day.at(repeat_time).do(repeat_poll)

    if config.STATS_ENABLED:
        schedule.every().day.at(config.STATS_CHECK_TIME).do(maybe_post_stats)

    while True:
        await schedule.run_pending()
        await asyncio.sleep(1)


async def startup():
    asyncio.create_task(start_scheduler())


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await startup()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
