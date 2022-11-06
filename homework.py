import logging
import os
import sys
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(stream=sys.stdout)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(funcName)s, %(message)s, %(name)s'
)
handler.setFormatter(formatter)
logger.addHandler(handler)

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
    bot.send_message(TELEGRAM_CHAT_ID, message)
    logger.info('Отправлено сообщение о текущем статусе работы')


def get_api_answer(current_timestamp):
    """Делаем запрос к эндпоинту и проверяем работу."""
    timestamp = current_timestamp
    params = {'from_date': timestamp}
    response = requests.get(ENDPOINT, headers=HEADERS, params=params)
    if response.status_code != 200:
        logger.error('API Практикума не отвечает')
        raise ConnectionError()
    return response.json()


def check_response(response):
    """Проверка ответа Api на корректность."""
    if not response['homeworks']:
        logger.error('Нет ключа homeworks')
        raise ValueError()
    homework = response['homeworks']
    if type(homework) != list:
        logger.error('Тип данных не соответствует ожидаемому')
        raise ValueError()
    elif homework == []:
        logger.debug('Нет ДЗ для отслеживания')
        raise ValueError()
    logger.debug('Ответ сервера прошел')
    return homework


def parse_status(homework):
    """Извлекает статус конкретной дз и проверяет его."""
    homework_name = homework['homework_name']
    if homework_name is None:
        logging.error('Не удалось получить данные домашки.')
        return 'Не удалось получить данные домашки.'
    homework_status = homework['status']
    if homework_status is None:
        logging.error('Не удалось получить данные домашки.')
        return 'Не удалось получить данные домашки.'
    try:
        verdict = HOMEWORK_STATUSES[homework_status]
        logging.info('Статус домашней работы получен.')
    except Exception as error:
        logging.error(f'Невозможно получить данные ДЗ. Ошибка: {error}')
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
    is_tokens_valid = check_tokens()
    if not is_tokens_valid:
        logger.error('Выполнение программы прервано из-за отсутствия токена')
        return
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 0
    api_response = get_api_answer(current_timestamp)
    while True:
        try:
            response = api_response
            checked_response = check_response(response)
            parsed_status = parse_status(checked_response)
            send_message(bot, parsed_status)
            print('Сообщение с новым статусом отправлено')
            current_timestamp = response['current_date']
            print('Записан текущий статус проверки домашки')
            time.sleep(RETRY_TIME)

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            logger.info('Отправлено сообщение об ошибке')
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
