"""Валидация ИНН по контрольной сумме."""


def validate_inn(inn: str) -> bool:
    """
    Валидация ИНН по контрольной сумме.

    ИНН юр. лица: 10 цифр
    ИНН физ. лица/ИП: 12 цифр

    Args:
        inn: Строка с ИНН

    Returns:
        True если ИНН валидный, False иначе
    """
    if not inn or not isinstance(inn, str):
        return False

    # Убираем пробелы
    inn = inn.strip()

    # Проверяем что только цифры
    if not inn.isdigit():
        return False

    if len(inn) == 10:
        # ИНН юр. лица (10 цифр)
        return _validate_inn_10(inn)
    elif len(inn) == 12:
        # ИНН физ. лица / ИП (12 цифр)
        return _validate_inn_12(inn)

    return False


def _validate_inn_10(inn: str) -> bool:
    """Валидация ИНН юр. лица (10 цифр)."""
    coefficients = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    checksum = sum(int(inn[i]) * coefficients[i] for i in range(9))
    control_digit = (checksum % 11) % 10
    return int(inn[9]) == control_digit


def _validate_inn_12(inn: str) -> bool:
    """Валидация ИНН физ. лица / ИП (12 цифр)."""
    # Коэффициенты для 11-й цифры (контрольная 1)
    coef1 = [7, 2, 4, 10, 3, 5, 9, 4, 6, 8]
    # Коэффициенты для 12-й цифры (контрольная 2)
    coef2 = [3, 7, 2, 4, 10, 3, 5, 9, 4, 6, 8]

    # Проверка первой контрольной цифры (11-я позиция)
    checksum1 = sum(int(inn[i]) * coef1[i] for i in range(10))
    control1 = (checksum1 % 11) % 10

    if int(inn[10]) != control1:
        return False

    # Проверка второй контрольной цифры (12-я позиция)
    checksum2 = sum(int(inn[i]) * coef2[i] for i in range(11))
    control2 = (checksum2 % 11) % 10

    return int(inn[11]) == control2


def normalize_inn(inn: str) -> str:
    """
    Нормализация ИНН (убирает пробелы и лишние символы).

    Args:
        inn: Строка с ИНН

    Returns:
        Нормализованный ИНН (только цифры)
    """
    if not inn:
        return ""
    return "".join(c for c in str(inn) if c.isdigit())
