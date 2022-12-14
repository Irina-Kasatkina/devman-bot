# coding=utf-8

"""Отслеживает проверку работ на dvmn.org и информирует пользователя в telegram-чате."""

import json
import logging
import os
import time

import requests
import telegram
import telegram.error
from dotenv import load_dotenv


logger = logging.getLogger('devman_bot.logger')


LONG_POLLING_TIMEOUT = 100


class TelegramLogsHandler(logging.Handler):
    """Перенаправляет логи бота в чат Telegram."""

    def __init__(self, telegram_bot_token, telegram_chat_id):
        super().__init__()
        self.bot = telegram.Bot(token=telegram_bot_token)
        self.chat_id = telegram_chat_id

    def emit(self, record):
        log_entry = self.format(record)
        self.bot.send_message(chat_id=self.chat_id, text=log_entry)


def monitor_devman_attempts(devman_api_token, telegram_bot, telegram_chat_id):
    """Отслеживает проверку работ на dvmn.org и информирует пользователя в telegram-чате."""

    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {devman_api_token}'}
    timestamp = 0
    params = {}
    delay = 1

    logger.info('Бот запущен.')
    while True:
        try:
            params = {'timestamp': timestamp} if timestamp else {}

            response = requests.get(url, headers=headers, params=params, timeout=LONG_POLLING_TIMEOUT)
            response.raise_for_status()

            reviews_monitoring = response.json()
            if reviews_monitoring['status'] == 'timeout':
                timestamp = reviews_monitoring['timestamp_to_request']
            elif reviews_monitoring['status'] == 'found':
                timestamp = reviews_monitoring['last_attempt_timestamp']
                for attempt in reviews_monitoring['new_attempts']:
                    message = generate_message_on_attempt(attempt)
                    telegram_bot.send_message(chat_id=telegram_chat_id, 
                                              text=message, 
                                              parse_mode=telegram.constants.PARSEMODE_HTML)
            delay = 1
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
            delay += 10
        except Exception as ex:
            logger.exception(ex)
            time.sleep(delay)
            delay += 10


def generate_message_on_attempt(attempt):
    """Формирует текст сообщения для telegram-бота."""

    message = (f'У вас проверили работу "<a href="{attempt["lesson_url"]}">'
               f'{attempt["lesson_title"]}</a>"\n\n')
    if attempt['is_negative']:
        message = f'{message}К сожалению, в работе нашлись ошибки.\n'
    else:
        message = f'{message}Преподавателю всё понравилось, можно приступать к следующему уроку!\n'
    return message


def main():
    load_dotenv()
    devman_api_token = os.environ['DEVMAN_API_TOKEN']
    telegram_bot_token = os.environ['TELEGRAM_BOT_TOKEN']
    telegram_chat_id = os.environ['TELEGRAM_CHAT_ID']

    telegram_bot = telegram.Bot(token=telegram_bot_token)

    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.setLevel(logging.INFO)
    logger.addHandler(TelegramLogsHandler(telegram_bot_token, telegram_chat_id))

    monitor_devman_attempts(devman_api_token, telegram_bot, telegram_chat_id)


if __name__ == '__main__':
    main()
