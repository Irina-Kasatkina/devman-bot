# coding=utf-8

"""Отслеживает проверку работ на dvmn.org и информирует пользователя в telegram-чате."""

import json
import os
import time

import requests
import telegram
import telegram.error
from dotenv import load_dotenv


LONG_POLLING_TIMEOUT = 100


def monitor_devman_attempts(devman_api_token, telegram_bot, telegram_chat_id):
    """Отслеживает проверку работ на dvmn.org и информирует пользователя в telegram-чате."""

    url = 'https://dvmn.org/api/long_polling/'
    headers = {'Authorization': f'Token {devman_api_token}'}
    timestamp = 0
    params = {}
    delay = 1
    while True:
        try:
            if timestamp:
                params = {'timestamp': timestamp}

            response = requests.get(url, headers=headers, params=params, timeout=LONG_POLLING_TIMEOUT)
            response.raise_for_status()

            reviews_monitoring = response.json()
            if reviews_monitoring['status'] == 'timeout':
                timestamp = int(reviews_monitoring['timestamp_to_request'])
            elif reviews_monitoring['status'] == 'found':
                for attempt in reviews_monitoring['new_attempts']:
                    message = generate_message_on_attempt(attempt)
                    telegram_bot.send_message(chat_id=telegram_chat_id, 
                                              text=message, 
                                              parse_mode=telegram.constants.PARSEMODE_HTML)
        except requests.exceptions.ReadTimeout:
            continue
        except requests.exceptions.ConnectionError:
            time.sleep(delay)
            delay = 10


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
    monitor_devman_attempts(devman_api_token, telegram_bot, telegram_chat_id)


if __name__ == '__main__':
    main()
