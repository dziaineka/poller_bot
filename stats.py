import datetime
import logging
from collections import defaultdict
from typing import List, Optional, Tuple

import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import find_peaks
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.tl import types as teletypes
import aiogram

import config

logger = logging.getLogger(__name__)


def get_option(
    answers: List[teletypes.PollAnswer], substr: str
) -> Optional[bytes]:
    for answer in answers:
        if answer.text.startswith(substr):
            return answer.option


def gather_options(answers: List[teletypes.PollAnswer]) -> Optional[dict]:
    used_answers = []
    options = {}

    for answer in answers:
        if answer.text in config.ANSWERS:
            used_answers.append(answer)
            options.update({answer.text: answer.option})

    for answer in answers:
        if answer in used_answers:
            continue

        for answer_text in config.ANSWERS:
            first_char = answer_text[0]
            if answer.text.startswith(first_char):
                used_answers.append(answer)
                options.update({answer_text: answer.option})

    if len(options) == len(answers):
        return options
    else:
        return None


def get_result(results: teletypes.PollResults, option: Optional[bytes]) -> int:
    if option is None:
        return 0

    if results.results:
        for result in results.results:
            if result.option.startswith(option):
                return result.voters
    return 0


def get_avg(data, w):
    avg = []
    window = []
    for d in data:
        window.append(d)
        if len(window) > w:
            window = window[1:]
        avg.append(sum(window) / len(window))
    return avg


def get_peaks(series):
    return find_peaks(series, height=0.45, distance=30)[0]


def get_empty_stats() -> dict:
    options = {
        "option_count": defaultdict(list),
        "option_ratio": defaultdict(list),
    }
    return {"options": options, "date": [], "total": []}


class Stats:
    def __init__(self) -> None:
        self.client = TelegramClient(
            StringSession(config.TELETHON_STRING_SESSION),
            config.TELEGRAM_API_ID,
            config.TELEGRAM_API_HASH,
        )

    @staticmethod
    def time_to_post() -> bool:
        day = datetime.datetime.today().day
        month = datetime.datetime.today().month
        return (day, month) in config.STATS_POST_DATES

    async def post(self, bot: aiogram.Bot):
        logger.info("Time to post stats")
        year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
        stats = await self.get_stats(year_ago)
        (main_graph_path, total_voters_graph_path) = self.create_graphs(stats)

        with open(main_graph_path, "rb") as graph:
            await bot.send_photo(
                chat_id=config.GROUP_NAME,
                photo=graph,
                disable_notification=True,
                caption="агульны графік"
            )

        with open(total_voters_graph_path, "rb") as graph:
            await bot.send_photo(
                chat_id=config.GROUP_NAME,
                photo=graph,
                disable_notification=True,
                caption="колькасць галасуючых"
            )

    def create_graphs(self, stats: dict) -> Tuple[str, str]:
        averages = {}
        averages_values = []
        highest_indices = {}
        window = 3
        main_graph_path = "zdrada.png"
        total_voters_path = "total_voters.png"

        for answer in config.ANSWERS:
            average = get_avg(stats["options"]["option_ratio"][answer], window)
            averages.update({answer: average})
            averages_values.append(average)
            highest_indices.update({answer: get_peaks(average)})

        y = np.vstack(averages_values)

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.stackplot(stats["date"], y)
        ax.legend(config.ANSWERS, markerscale="0.2", fontsize="xx-small")

        x_points = []
        y_points = []

        for answer in config.ANSWERS:
            for idx in highest_indices[answer]:
                d = stats["date"][idx]
                d_str = f"{d.month}-{d.day}"
                v = 1.0 - averages[answer][idx]
                ax.annotate(
                    "%s(%s): %.2f" % (answer[0], d_str, v),
                    xy=(d, v),
                    fontsize=6,
                )
                x_points.append(d)
                y_points.append(v)

        plt.plot(x_points, y_points, "o", markersize=1)
        plt.savefig(main_graph_path, dpi=200)

        fig.clear()
        avg_voters = get_avg(stats["total"], window)
        plt.plot(stats["date"], avg_voters)
        plt.savefig(total_voters_path, dpi=200)

        return main_graph_path, total_voters_path

    async def get_stats(self, offset_date) -> dict:
        stats = get_empty_stats()

        async with self.client:
            async for message in self.client.iter_messages(
                config.CHANNEL_NAME, offset_date=offset_date, reverse=True
            ):
                poll = message.poll

                if not (
                    poll and poll.poll.question.startswith(config.QUESTION)
                ):
                    continue

                answers = poll.poll.answers
                total = 0
                results = {}

                options = gather_options(answers)

                if options is None:
                    continue

                for answer in config.ANSWERS:
                    option = options[answer]
                    result = get_result(poll.results, option)
                    results.update({answer: result})

                    if result:
                        total += result

                # nobody voted
                if total == 0:
                    continue

                stats["date"].append(message.date)
                stats["total"].append(total)

                for option in results:
                    result = results[option]
                    stats["options"]["option_count"][option].append(result)
                    stats["options"]["option_ratio"][option].append(
                        result / total
                    )

        return stats
