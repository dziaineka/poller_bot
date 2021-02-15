from os import getenv
from os.path import join, dirname
from dotenv import load_dotenv

# Create .env file path.
dotenv_path = join(dirname(__file__), '.env')

# Load file from the path.
load_dotenv(dotenv_path)

BOT_TOKEN = getenv('BOT_TOKEN')
ADMINS = getenv('ADMINS').split(";;")
CHANNEL_NAME = getenv('CHANNEL_NAME')
GROUP_NAME = getenv('GROUP_NAME')
QUESTION = getenv("QUESTION")
ANSWERS = getenv("ANSWERS").split(";;")
NEW_POLL_TIMES = getenv("NEW_POLL_TIMES").split(";;")
REPEAT_POLL_TIMES = getenv("REPEAT_POLL_TIMES").split(";;")
TIMEZONE = getenv("TIMEZONE") or 'Europe/Minsk'

# Amount of messages in group after previous poll which make bot to be
# allowed to forward poll again
GROUP_MESSAGES_COUNT_THRESHOLD = \
    int(getenv("GROUP_MESSAGES_COUNT_THRESHOLD") or 5)
