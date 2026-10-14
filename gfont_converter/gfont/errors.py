"""Понятные пользователю ошибки (на русском) для CLI и GUI."""

from __future__ import annotations

import errno
from pathlib import Path


class UserError(Exception):
    """Ошибка, текст которой можно показать пользователю как есть."""


class Cancelled(Exception):
    """Операция отменена пользователем."""


def describe_os_error(exc: OSError, path: Path | str, action: str = "записать") -> str:
    p = str(path)
    if isinstance(exc, PermissionError) or exc.errno in (errno.EACCES, errno.EPERM):
        return (f"Не удалось {action} файл «{p}»: файл занят другой программой "
                f"(например, открыт в приложении) или нет прав на запись в эту папку.")
    if exc.errno == errno.ENOSPC:
        return f"Не удалось {action} файл «{p}»: на диске нет места."
    if isinstance(exc, FileNotFoundError):
        return f"Файл или папка не найдены: «{p}»."
    if isinstance(exc, IsADirectoryError):
        return f"«{p}» — это папка, а не файл."
    return f"Не удалось {action} файл «{p}»: {exc.strerror or exc}"
