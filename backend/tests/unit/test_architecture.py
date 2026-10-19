"""Reglas de arquitectura transversales (RNF-021).

El catálogo de patrones se demuestra con `SingletonMeta`/`AppRuntime`, pero la
configuración se accede SIEMPRE con `get_settings()` (inyectada con
`Depends(get_settings)`). Ningún módulo de `app/` salvo `core/config.py` debe
importar `AppRuntime`, `get_runtime` o `SingletonMeta`.
"""

from __future__ import annotations

import ast
from pathlib import Path

APP = Path(__file__).resolve().parents[2] / "app"
_PROHIBIDOS = {"AppRuntime", "get_runtime", "SingletonMeta"}


def _nombres_importados(path: Path) -> list[tuple[int, str]]:
    """Devuelve `(línea, nombre)` de cada nombre importado en el archivo."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    encontrados: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            encontrados.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.Import):
            encontrados.extend((node.lineno, alias.name.split(".")[-1]) for alias in node.names)
    return encontrados


def test_ningun_modulo_usa_el_singleton_de_demostracion():
    infractores = []
    for path in sorted(APP.rglob("*.py")):
        if path.name == "config.py":
            continue
        for lineno, nombre in _nombres_importados(path):
            if nombre in _PROHIBIDOS:
                infractores.append(f"{path.relative_to(APP)}:{lineno}: {nombre}")
    assert infractores == []
