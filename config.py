import logging
from os import getenv
from os.path import dirname, join
from typing import Optional

from dotenv import load_dotenv


def get_logging_level(level: Optional[str]) -> int:
    if level == 'CRITICAL':
        return logging.CRITICAL
    elif level == 'FATAL':
        return logging.FATAL
    elif level == 'ERROR':
        return logging.ERROR
    elif level == 'WARNING':
        return logging.WARNING
    elif level == 'WARN':
        return logging.WARN
    elif level == 'INFO':
        return logging.INFO
    elif level == 'DEBUG':
        return logging.DEBUG
    elif level == 'NOTSET':
        return logging.NOTSET
    else:
        return logging.INFO


# Create .env file path.
dotenv_path = join(dirname(__file__), '.env')

# Load file from the path.
load_dotenv(dotenv_path)

BOT_TOKEN = getenv('BOT_TOKEN', "")

# Users who can send commands to bot (e.g. /force) and do other interaction
ADMINS = getenv('ADMINS', "").split(";;")

CHANNEL_NAME = getenv('CHANNEL_NAME', "")
GROUP_NAME = getenv('GROUP_NAME', "")

QUESTION = getenv("QUESTION")
ANSWERS = getenv("ANSWERS", "").split(";;")

# Times to post new poll (UTC)
NEW_POLL_TIMES = getenv("NEW_POLL_TIMES", "").split(";;")

# Times to repeat poll which was postes according to previous setting (UTC)
REPEAT_POLL_TIMES = getenv("REPEAT_POLL_TIMES", "").split(";;")

# Timezone name for bot to determine date for poll title.
TIMEZONE = getenv("TIMEZONE") or 'Europe/Minsk'

# Amount of messages in group after previous poll which make bot to be
# allowed to forward poll again
GROUP_MESSAGES_COUNT_THRESHOLD = \
    int(getenv("GROUP_MESSAGES_COUNT_THRESHOLD") or 5)

LOGGING_LEVEL = get_logging_level(getenv("LOGGING_LEVEL"))
