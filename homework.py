import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv
from telegram import TelegramError

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s, %(name)s'
)

PRACTICUM_TOKEN = os.getenv('PTOKEN')
TELEGRAM_TOKEN = os.getenv('TTOKEN')
TELEGRAM_CHAT_ID = os.getenv('TID')

RETRY_TIME = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправляем сообщение в телеграмм о статусе дз."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info('Отправлено сообщение о текущем статусе работы')
    except TelegramError('Сообщение не отправленно'):
        logger.error('Сообщение о текущем статусе работы не отправлено')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту и проверяем работу."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    except ConnectionError:
        raise ConnectionError(f'Ошибка при попытке доступака к {ENDPOINT},'
              f'c {HEADERS}, {params}')
    if response.status_code != 200:
        raise ConnectionError(f'Ошибка при попытке доступака к {ENDPOINT},'
              f'c {HEADERS}, {params}, и статус кодом {response.status_code}')
    try:
        return response.json()
    except Exception as error:
        raise (f'Произошла ошибка {error}, при попытке доступака к {ENDPOINT},'
               f'c {HEADERS}, {params}, и статус кодом {response.status_code}')


def check_response(response):
    """Проверка ответа Api на корректность."""
    if not isinstance(response, dict):
        raise TypeError('Тип данных не словарь')
    if 'homeworks' not in response:
        raise KeyError(f'Ключа homeworks нет в словаре:{response}')
    else:
        homework = response['homeworks']
    if 'current_date' not in response:
        raise KeyError(f'Ключа current_date нет в словаре:{response}')
    if isinstance(homework, list):
        return homework


def parse_status(homework):
    """Извлекает статус конкретной дз и проверяет его."""
    if not isinstance(homework, dict):
        raise TypeError(f'Тип данных должен быть dict, {homework}')
    if 'homework_name' not in homework:
        raise KeyError(f'Не удалось получить данные домашки:{homework}')
    else:
        homework_name = homework['homework_name']
    if 'status' not in homework:
        raise KeyError(f'Ключ status не найден:{homework}')
    else:
        homework_status = homework['status']
    if homework_status is None:
        raise Exception(f'Не удалось получить данные дз:{homework_status}')
    if homework_status in HOMEWORK_STATUSES.keys():
        verdict = HOMEWORK_STATUSES[homework_status]
    else:
        raise Exception('В словаре нет ключа homework_status')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверяю наличие всех переменных окружения и логгирую проверку."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        logger.info('Все токены на месте!')
        return True
    logger.critical('Токенов не хватает')
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logger.error('Выполнение программы прервано из-за отсутствия токена')
        sys.exit()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time()) - 36000
    status = ''
    check_ms = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            logging.info('Получен ответ Api')
            checked_response = check_response(response)
            parsed_status = parse_status(checked_response[0])
            if parsed_status != status:
                status = parsed_status
                send_message(bot, parsed_status)
            logging.info('Сообщение с новым статусом отправлено')
            current_timestamp = response['current_date']
            logging.info('Записан текущий статус проверки домашки')
        except TelegramError:
            logging.info('Проблема с телеграм, сообщение не отправлено')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            if message != check_ms:
                check_ms = message
                send_message(bot, message)
                logger.info('Отправлено сообщение об ошибке')
        finally:
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
    handler.setFormatter(formatter)
    logger.addHandler(handler)
