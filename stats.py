import datetime
import config
from telethon import TelegramClient
from telethon.tl import types as teletypes
from scipy.signal import find_peaks
import numpy as np
import matplotlib.pyplot as plt
from typing import List, Optional
from collections import defaultdict


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
            "stats", config.TELEGRAM_API_ID, config.TELEGRAM_API_HASH
        )

    @staticmethod
    def time_to_post() -> bool:
        day = datetime.datetime.today().day
        month = datetime.datetime.today().month
        return (day, month) in config.STATS_POST_DATES

    async def post(self):
        year_ago = datetime.datetime.now() - datetime.timedelta(days=365)
        stats = await self.get_stats(year_ago)

        averages = {}
        highest_indices = {}
        window = 3

        for answer in config.ANSWERS:
            average = get_avg(stats["options"]["option_ratio"][answer], window)
            averages.update({answer: average})
            highest_indices.update({answer: get_peaks(average)})

        y = np.vstack(list(averages.values()))

        fig, ax = plt.subplots(figsize=(10, 3))
        ax.stackplot(stats["date"], y)
        ax.legend(config.ANSWERS, markerscale="0.2", fontsize="xx-small")

        x_points = []
        y_points = []

        for option in highest_indices:
            for idx in highest_indices[option]:
                d = stats["Date"][idx]
                d_str = "%s-%s" % (d.month, d.day)
                v = 1.0 - averages[option][idx]
                ax.annotate("z(%s): %.2f" % (d_str, v), xy=(d, v), fontsize=6)
                x_points.append(d)
                y_points.append(v)

        plt.plot(x_points, y_points, "o", markersize=1)
        plt.savefig("zrada.png", dpi=200)
        # plt.show()

        fig.clear()
        avg_voters = get_avg(stats["Total"], window)
        plt.plot(stats["Date"], avg_voters)
        plt.savefig("total_voters.png", dpi=200)

    async def get_stats(self, offset_date) -> dict:
        stats = get_empty_stats()

        async with self.client:
            async for message in self.client.iter_messages(
                config.CHANNEL_NAME, offset_date=offset_date
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
