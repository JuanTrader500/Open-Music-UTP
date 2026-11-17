# Fase 2 · Catálogo

Documento de seguimiento de la segunda fase del plan de la API de 31 rutas.

## 1. Objetivo

Implementar las 5 rutas de catálogo con persistencia real en PostgreSQL y el
proveedor simulado, de modo que la búsqueda sea demostrable sin consumir cuota
de YouTube.

## 2. Rutas

| ID | Método | Ruta | Auth | Requisito |
|---|---|---|---|---|
| C-01 | GET | `/api/catalog/search` | No | RF-010/011, RN-012 |
| C-02 | GET | `/api/catalog/tracks/{track_id}` | No | RF-010 |
| C-03 | POST | `/api/catalog/tracks/{track_id}/unplayable` | No | RF-009, RN-012 |
| C-04 | GET | `/api/catalog/genres` | No | RF-011, RF-021 |
| C-05 | GET | `/api/catalog/artists` | No | RF-021 |

## 3. Archivos

| Archivo | Responsabilidad |
|---|---|
| `app/catalog/schemas.py` | Contratos de entrada/salida |
| `app/catalog/repository.py` | Consultas y upserts |
| `app/catalog/genres.py` | Prioridad de resolución de género |
| `app/catalog/service.py` | Reglas, transacciones y proveedor |
| `app/catalog/router.py` | Endpoints HTTP |
| `app/catalog/seed_importer.py` | Importación idempotente de semillas |
| `app/catalog/seed_data.py` | 45 géneros y 440 artistas base del esquema v6 |

## 4. Reglas aplicadas

- `q` se valida con `search_min_chars`; una consulta corta no llama al proveedor.
- `limit` no puede superar `youtube_max_results`.
- Solo se devuelven canciones con `is_embeddable=true`.
- La búsqueda persiste artistas, canciones y género.
- El artista se reutiliza por `name_normalized`.
- El género se resuelve con prioridad semilla > artista > categoría > sin clasificar.
- Una canción marcada como no reproducible no reaparece en búsquedas.
- El importador de semillas restaura el catálogo y es idempotente.
- El router no conoce el proveedor ni el ORM.
- Los errores conservan el envelope `{"code","message"}`.

## 5. Semillas

| Playlist | Género |
|---|---|
| `PL_SIM_ROCK` | `rock` |
| `PL_SIM_POP` | `pop` |
| `PL_SIM_SALSA` | `salsa` |

Comando:

```bash
python -m app.catalog.seed_importer --all
```

Resultado en una base limpia:

- 45 géneros.
- 440 artistas base.
- 4 artistas de las canciones simuladas (444 en total).
- 3 semillas de playlist.
- 7 canciones embebibles.

## 6. Pruebas

| Archivo | Cobertura |
|---|---|
| `tests/unit/test_genres.py` | Prioridad de género y normalización |
| `tests/unit/test_catalog_service.py` | Búsqueda, persistencia, semillas, RN-012 |
| `tests/unit/test_seed_data.py` | 45 géneros y 440 artistas base, idempotencia |
| `tests/integration/test_catalog_endpoints.py` | C-01 a C-05 y negativos |
| `tests/unit/test_orm_parity.py` | Paridad ORM ↔ PostgreSQL |

## 7. Verificación

```bash
cd backend
ruff format --check .
ruff check .
pytest --cov=app --cov-fail-under=70
alembic check
python -m app.catalog.seed_importer --all
```

## 8. Postman

Carpeta `02 Catalog` de la colección:

1. Géneros.
2. Artistas.
3. Búsqueda y guardado de `track_id`.
4. Detalle.
5. Marcar no reproducible.
6. Repetir búsqueda.
7. Query inválida.
8. Track inexistente.

La guía completa está en [`postman_docs/`](postman_docs/README.md).

## 9. Pendientes

- Fase 3: playlists y favoritos.
- Fase 4: escucha y recomendaciones.
- Fase 5: exportación completa, cascada y negativos globales.
- Fase 6: colección de las 31 rutas y Newman en CI.
