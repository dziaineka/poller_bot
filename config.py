from os import getenv
from os.path import join, dirname
from dotenv import load_dotenv

# Create .env file path.
dotenv_path = join(dirname(__file__), '.env')

# Load file from the path.
load_dotenv(dotenv_path)

BOT_TOKEN = getenv('BOT_TOKEN')
CHANNEL_NAME = getenv('CHANNEL_NAME')
GROUP_NAME = getenv('GROUP_NAME')
QUESTION = getenv("QUESTION")
ANSWERS = getenv("ANSWERS")
NEW_POLL_TIME = getenv("NEW_POLL_TIME") or "2000"
REPEAT_POLL_TIMES = getenv("REPEAT_POLL_TIMES") or ""
TIMEZONE = getenv("TIMEZONE") or 'Europe/Minsk'
