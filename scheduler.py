import asyncio
import logging
from typing import Callable

import aioschedule as schedule

import config

logger = logging.getLogger(__name__)


class Scheduler:
    def __init__(self,
                 initial_action: Callable,
                 repeat_action: Callable) -> None:
        self.initial_action = initial_action
        self.repeat_action = repeat_action

    async def start(self):
        logger.info('Scheduler started')

        for action_time in config.NEW_POLL_TIMES:
            schedule.every().day.at(action_time).do(self.initial_action)

        for repeat_time in config.REPEAT_POLL_TIMES:
            schedule.every().day.at(repeat_time).do(self.repeat_action)

        while True:
            await schedule.run_pending()
            await asyncio.sleep(0.1)
