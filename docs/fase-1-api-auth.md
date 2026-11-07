# Fase 1 · Auth (plan API de 31 rutas)

Documento de seguimiento de la primera fase del plan de la API de 31 rutas.
No debe confundirse con [`fase-1-fundaciones.md`](fase-1-fundaciones.md), que
corresponde a la fase anterior del proyecto (núcleo transversal y contenedores).

## 1. Objetivo

Dejar operativa la autenticación real del backend: registro, inicio y cierre de
sesión, consulta del usuario autenticado, exportación de datos y eliminación de
cuenta. Como prerrequisito se completó la base técnica que faltaba: modelos ORM,
migración inicial de Alembic, hash de contraseñas, JWT y rate limit.

## 2. Alcance

- Base ORM de las 11 tablas del esquema v6.
- Migración inicial de Alembic en paridad con `dataBase/schema.sql`.
- Seguridad: Argon2id, JWT HS256 y límite de intentos de login.
- Módulo `app/auth/` con las 6 rutas del contrato.
- Pruebas unitarias de seguridad y de integración de los endpoints.
- Documentación del proceso y de las decisiones.

## 3. Fuera de alcance

- Catálogo, playlists, favoritos, escucha y recomendaciones (fases 2 a 4).
- Exportación completa de playlists, favoritos, historial y preferencias: en
  esta fase se devuelven colecciones vacías; se completan en la fase 5.
- Semillas de géneros y artistas en una base limpia: la base actual ya las
  tiene; el mecanismo de seed se resuelve en la fase 2.
- Colección de Postman, Newman y CI de la fase 6.

## 4. Proceso ejecutado

| Paso | Qué se hizo | Verificación |
|---|---|---|
| 1 | Se verificó la base actual: 11 tablas, `track_id` v6, 45 géneros y 440 artistas. | Consultas `information_schema` y conteos. |
| 2 | Se corrigió el `.env` local: `MUSIC_PROVIDER=simulated`, `DATABASE_URL`, `JWT_SECRET` de 64 caracteres y `CORS_ORIGINS`. | Arranque de la aplicación y `pytest`. |
| 3 | Se agregaron `PyJWT` y `argon2-cffi` a `requirements.txt`. | `pip install` en el entorno `open-music`. |
| 4 | Se creó la base declarativa y los 11 modelos ORM. | `Base.metadata` contiene las 11 tablas. |
| 5 | Se creó Alembic con migración inicial. | `alembic upgrade head` en base limpia y paridad de esquema. |
| 6 | Se aplicó la línea base a la base existente con `alembic stamp head`. | `alembic current` y `alembic check` sin diferencias. |
| 7 | Se implementó seguridad: hash Argon2id, JWT y rate limiter. | `tests/unit/test_security.py`. |
| 8 | Se implementó `auth` por capas: schemas, repository, service, dependencies y router. | 6 rutas en `/api/auth`. |
| 9 | Se escribieron pruebas de integración con PostgreSQL de prueba. | `tests/integration/test_auth_endpoints.py`. |
| 10 | Se ejecutaron pruebas y lint, y se documentó el resultado. | 87 pruebas y `ruff` en verde. |

## 5. Cambios por capa

- `app/core/base.py`: `Base`, convención de nombres compatible con PostgreSQL y
  mixins de timestamps.
- `app/auth/models.py`, `app/catalog/models.py`, `app/playlists/models.py`,
  `app/favorites/models.py`, `app/listening/models.py`,
  `app/recommendations/models.py`: modelos ORM de las 11 tablas.
- `migrations/env.py` y `migrations/versions/0323eb7fe24c_initial_schema.py`:
  migración inicial y configuración de Alembic.
- `app/core/security.py`: Argon2id, creación/validación de JWT y
  `LoginRateLimiter`.
- `app/auth/schemas.py`: contratos de entrada y salida; `accept_privacy` es
  obligatorio.
- `app/auth/repository.py`: consultas y escrituras de `users`.
- `app/auth/service.py`: reglas de registro, login, exportación y eliminación.
- `app/auth/dependencies.py`: `get_current_user` y `get_optional_user`.
- `app/auth/router.py`: las 6 rutas del contrato.
- `tests/conftest.py`: base de pruebas aislada, sesión transaccional y cliente
  HTTP con la dependencia de base de datos sustituida.
- `tests/unit/test_security.py` y `tests/integration/test_auth_endpoints.py`:
  cobertura de seguridad y de los endpoints.
- `.github/workflows/test.yml`: servicio PostgreSQL 16 efímero para que las
  pruebas de integración corran en CI sin una base externa.

## 6. Contrato HTTP

| Método | Ruta | Autenticación | Éxito | Errores esperados |
|---|---|---|---|---|
| `POST` | `/api/auth/register` | No | `201` con `id`, `email`, `created_at` | `409 EMAIL_TAKEN`, `422 VALIDATION_ERROR` |
| `POST` | `/api/auth/login` | No | `200` con `access_token`, `token_type`, `expires_in` | `401 INVALID_CREDENTIALS`, `429 RATE_LIMITED` |
| `POST` | `/api/auth/logout` | Bearer | `204` sin cuerpo | `401 UNAUTHORIZED` |
| `GET` | `/api/auth/me` | Bearer | `200` con datos públicos del usuario | `401 UNAUTHORIZED` |
| `GET` | `/api/auth/export` | Bearer | `200` con `user` y colecciones | `401 UNAUTHORIZED` |
| `DELETE` | `/api/auth/account` | Bearer | `204` sin cuerpo | `401 UNAUTHORIZED` |

Todos los errores conservan el envelope del proyecto:

```json
{"code": "CODIGO", "message": "Mensaje en español"}
```

Reglas aplicadas:

- Contraseña con mínimo configurable (`PASSWORD_MIN_LENGTH`, por defecto 8).
- Correo normalizado a minúsculas y único (RN-004).
- `accept_privacy=true` obligatorio; no se agregó una columna
  `privacy_accepted_at` (decisión D-07).
- Login limitado a `LOGIN_ATTEMPTS_PER_MINUTE` intentos por minuto y por
  combinación correo + IP. Es un límite en memoria del proceso, adecuado para
  desarrollo y documentado como tal.
- El JWT usa `JWT_SECRET`, `ACCESS_TOKEN_EXPIRE_MINUTES` y el algoritmo HS256.

## 7. Decisiones

- **D-01:** la base de datos existente manda. La migración inicial replica el
  esquema v6; en una base existente se usa `alembic stamp head` y en una base
  limpia `alembic upgrade head`.
- **D-07:** el registro solo exige `accept_privacy`; no se crea una columna
  nueva para la fecha de aceptación.
- **D-09:** favoritos será un módulo propio (`app/favorites/`), ya creado como
  paquete y modelo en esta fase.
- Las dependencias `get_current_user` y `get_optional_user` viven en
  `auth/dependencies.py`, no en `core/security.py`: `core` concentra el
  mecanismo (JWT, hash) y `auth` la carga del usuario, evitando que el núcleo
  dependa de un módulo funcional.
- El rate limit es global en memoria y las pruebas lo limpian entre casos para
  evitar contaminación.

## 8. Cómo ejecutar y verificar

```bash
cd backend
pip install -r requirements-dev.txt

# Base de datos del compose (puerto estándar 5433)
docker compose -f ../docker-compose.yml up -d db

# Base existente con esquema v6 (incluida la que crea schema.sql): marcar línea base
alembic stamp head

# Base vacía (creada a mano o en CI): aplicar la migración
alembic upgrade head

# Base dedicada para pruebas (nombre terminado en _test)
docker compose -f ../docker-compose.yml exec -T db \
  sh -c 'createdb -U "$POSTGRES_USER" openmusic_test'

# Las pruebas nunca usan la base de desarrollo. Si TEST_DATABASE_URL no está
# definida, se deriva del DATABASE_URL del .env cambiando el nombre por *_test.
export TEST_DATABASE_URL='postgresql+psycopg://usuario:clave@localhost:5433/openmusic_test'
pytest
ruff check .
ruff format --check .
alembic check
```

Nota de entorno local: en esta máquina el puerto `5433` estaba ocupado por otro
proyecto. Se levantó PostgreSQL en `127.0.0.1:5434` con un override temporal en
`/tmp/opencode/open-music-db.override.yml`, sin cambiar el compose versionado.
El `.env` local y `TEST_DATABASE_URL` se ajustaron a ese puerto.

## 9. Resultados de verificación

| Comprobación | Resultado |
|---|---|
| Pruebas completas | `120 passed` |
| Cobertura total | 93.27 % (umbral 70 %) |
| Pruebas nuevas de seguridad | 10 |
| Pruebas nuevas de integración de auth | 14 |
| `ruff check .` | Sin errores |
| `ruff format --check .` | 93 archivos formateados |
| `alembic current` | `0323eb7fe24c (head)` |
| `alembic check` | `No new upgrade operations detected` |
| Paridad de esquema | Sin diferencias frente a `openmusic`, salvo `alembic_version` |
| CI | Workflow con PostgreSQL 16 de servicio y `TEST_DATABASE_URL` |

## 10. Registro de implementación

| Fecha | Fase | Resumen |
|---|---|---|
| 2026-11-04 | F0 | Base ORM de 11 tablas, Alembic inicial, línea base en la base existente, hash Argon2id, JWT y rate limit. |
| 2026-11-04 | F1 | 6 endpoints de auth, pruebas unitarias/integración y documentación. Sin `git add` ni commit, a la espera de autorización. |
| 2026-11-06 | F1-08 | Colección Postman de auth, environment local y README; guía de demostración en `docs/postman_docs/`. |
| 2026-11-06 | F0-10 | Prueba de paridad ORM ↔ PostgreSQL y documento `docs/decisiones.md`. |

---

## 11. Cierre de pendientes de Fase 1

- **F1-08:** creada la colección `backend/postman/OpenMusicUTP.postman_collection.json`
  con las carpetas `00 Health`, `01 Auth`, `02 Catalog`, `08 Negative/Errors` y
  `07 Privacy`. Incluye encadenamiento de variables y pruebas de contrato.
- **F0-10:** creada la prueba `backend/tests/unit/test_orm_parity.py`, que valida
  tablas, columnas, tipos, nulabilidad, claves primarias, claves foráneas,
  restricciones `CHECK` e índices contra PostgreSQL.
- **Documentación:** `docs/decisiones.md`, `docs/postman_docs/` y
  `docs/fase-2-catalogo.md`.

Con estos cambios la suite completa queda en **120 pruebas verdes**.

## 12. Pendientes para las siguientes fases

- Fase 3: playlists y favoritos.
- Fase 4: escucha y recomendaciones.
- Fase 5: completar `/api/auth/export` con los datos de los demás módulos.
- Fase 6: colección de las 31 rutas y Newman en CI.
