"""Decorador de transacciones para los servicios (patrón Decorator, entrega 2).

Los servicios repiten el mismo bloque `try / commit / except rollback`. Este
decorador centraliza esa política: envuelve un método de instancia, toma la
sesión de `self.db`, hace `commit` si el método termina y `rollback` si lanza
una excepción, que se propaga sin cambios.

Solo se aplica a métodos de escritura; los métodos de lectura no se decoran
para no abrir transacciones innecesarias (RNF-021).
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any


def transactional[**P, R](method: Callable[P, R]) -> Callable[P, R]:
    """Ejecuta el método dentro de una transacción de la sesión `self.db`.

    Si el método termina bien, confirma; si lanza una excepción, revierte y
    relanza la excepción original. El decorador es el único que hace
    `commit`/`rollback` en los servicios decorados.
    """

    @functools.wraps(method)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        db: Any = getattr(args[0], "db", None) if args else None
        if db is None:
            raise AttributeError("@transactional requiere un método con self.db")
        try:
            result = method(*args, **kwargs)
            db.commit()
        except Exception:
            db.rollback()
            raise
        return result

    return wrapper
