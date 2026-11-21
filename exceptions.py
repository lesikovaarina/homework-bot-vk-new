class EndpointStatusError(Exception):
    """Эндпоинт API вернул код ответа, отличный от 200."""


class MissingTokenError(Exception):
    """Отсутствует обязательная переменная окружения."""
