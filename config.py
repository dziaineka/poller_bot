import logging
from os import getenv
from os.path import dirname, join
from typing import List, Optional, Tuple

from dotenv import load_dotenv


def get_logging_level(level: Optional[str]) -> int:
    if level == "CRITICAL":
        return logging.CRITICAL
    elif level == "FATAL":
        return logging.FATAL
    elif level == "ERROR":
        return logging.ERROR
    elif level == "WARNING":
        return logging.WARNING
    elif level == "WARN":
        return logging.WARN
    elif level == "INFO":
        return logging.INFO
    elif level == "DEBUG":
        return logging.DEBUG
    elif level == "NOTSET":
        return logging.NOTSET
    else:
        return logging.INFO


def parse_date(date: str) -> Tuple[int, int]:
    (day, month) = date.split(".")
    return (int(day), int(month))


def get_post_dates() -> set[Tuple[int, int]]:
    dates = getenv(
        "STATS_POST_DATES",
        "01.01;;01.02;;01.03;;01.04;;01.05;;01.06;;"
        "01.07;;01.08;;01.09;;01.10;;01.11;;01.12",
    ).split(";;")

    return set(map(lambda date: parse_date(date), dates))


# Create .env file path.
dotenv_path = join(dirname(__file__), ".env")

# Load file from the path.
load_dotenv(dotenv_path)

BOT_TOKEN = getenv("BOT_TOKEN", "")

# needed for statistics posting. Get it from my.telegram.org
TELEGRAM_API_ID = int(getenv("TELEGRAM_API_ID", 0))
TELEGRAM_API_HASH = getenv("TELEGRAM_API_HASH", "")
# get string session by running get_string_session.py
TELETHON_STRING_SESSION = getenv("TELETHON_STRING_SESSION", "")

# Users who can send commands to bot (e.g. /force) and do other interaction
ADMINS = getenv("ADMINS", "").split(";;")

CHANNEL_NAME = getenv("CHANNEL_NAME", "")
GROUP_NAME = getenv("GROUP_NAME", "")

QUESTION = getenv("QUESTION")
ANSWERS = getenv("ANSWERS", "").split(";;")

# Times to post new poll (UTC)
NEW_POLL_TIMES = getenv("NEW_POLL_TIMES", "").split(";;")

# Times to repeat poll which was postes according to previous setting (UTC)
REPEAT_POLL_TIMES = getenv("REPEAT_POLL_TIMES", "").split(";;")

# Timezone name for bot to determine date for poll title.
TIMEZONE = getenv("TIMEZONE") or "Europe/Minsk"

# Amount of messages in group after previous poll which make bot to be
# allowed to forward poll again
GROUP_MESSAGES_COUNT_THRESHOLD = int(
    getenv("GROUP_MESSAGES_COUNT_THRESHOLD") or 5
)

LOGGING_LEVEL = get_logging_level(getenv("LOGGING_LEVEL"))

STATS_ENABLED = bool(int(getenv("STATS_ENABLED", 0)))

# Need to post stats checks once a day at a time determined below (UTC)
STATS_CHECK_TIME = getenv("STATS_CHECK_TIME", "12:00")

# What date should we post stats (UTC)
STATS_POST_DATES = get_post_dates()
