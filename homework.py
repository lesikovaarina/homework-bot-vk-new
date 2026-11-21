import logging
import os
import sys
import time
from http import HTTPStatus

import requests
import vk_api
from dotenv import load_dotenv


load_dotenv()

PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
VK_TOKEN = os.getenv('VK_TOKEN')
VK_USER_ID = os.getenv('VK_USER_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность переменных окружения."""
    if not PRACTICUM_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная окружения: PRACTICUM_TOKEN'
        )
        return False
    if not VK_TOKEN:
        logging.critical(
            'Отсутствует обязательная переменная окружения: VK_TOKEN'
        )
        return False
    if not VK_USER_ID:
        logging.critical(
            'Отсутствует обязательная переменная окружения: VK_USER_ID'
        )
        return False
    return True


def send_message(vk, message):
    """Отправляет сообщение в ВК."""
    try:
        vk.messages.send(
            user_id=VK_USER_ID,
            message=message,
            random_id=vk_api.utils.get_random_id()
        )
    except (vk_api.exceptions.VkApiError,
            requests.RequestException) as error:
        logging.error(f'Ошибка при отправке сообщения в ВК: {error}')
        return False
    logging.debug(f'Бот отправил сообщение "{message}"')
    return True


def get_api_answer(timestamp):
    """Делает запрос к API Яндекс Практикума."""
    try:
        response = requests.get(
            ENDPOINT, headers=HEADERS, params={'from_date': timestamp}
        )
    except requests.RequestException as error:
        raise ConnectionError(
            f'Ошибка при запросе к API: {error}'
        ) from error
    if response.status_code != HTTPStatus.OK:
        raise ConnectionError(
            f'Эндпоинт {ENDPOINT} недоступен. '
            f'Код ответа API: {response.status_code}'
        )
    return response.json()


def check_response(response):
    """Проверяет ответ API на корректность."""
    if not isinstance(response, dict):
        raise TypeError(
            f'Ответ API не является словарем. Получен {type(response)}'
        )
    if 'homeworks' not in response:
        raise KeyError('В ответе API отсутствует ключ "homeworks"')
    homeworks = response['homeworks']
    if 'current_date' not in response:
        raise KeyError('В ответе API отсутствует ключ "current_date"')
    if not isinstance(homeworks, list):
        raise TypeError('Значение по ключу "homeworks" не является списком')
    return homeworks


def parse_status(homework):
    """Извлекает статус домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError('В ответе API нет ключа "homework_name"')
    if 'status' not in homework:
        raise KeyError('В ответе API нет ключа "status"')
    homework_name = homework['homework_name']
    status = homework['status']
    if status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {status}')
    verdict = HOMEWORK_VERDICTS.get(status)
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit('Программа принудительно остановлена.')
    # Создаем сессию для бота
    vk_session = vk_api.VkApi(token=VK_TOKEN)
    vk = vk_session.get_api()
    timestamp = int(time.time())

    last_message = ''
    while True:
        try:
            get_api_answer_response = get_api_answer(timestamp)
            homeworks = check_response(get_api_answer_response)
            timestamp = get_api_answer_response['current_date']
            if homeworks:
                message = parse_status(homeworks[0])
                send_message(vk, message)
            else:
                logging.debug('Новых статусов нет')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            if message != last_message:
                send_message(vk, message)
                last_message = message
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    main()
