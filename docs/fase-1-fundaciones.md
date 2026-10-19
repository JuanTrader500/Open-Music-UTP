# Fase 1 · Fundaciones

Documento de seguimiento de la primera fase de desarrollo. Está dirigido al equipo y a quien continúe el proyecto:
describe qué se construye, en qué orden y cómo verificarlo. Se actualiza al cerrar cada PR.

## 1. Objetivo

Dejar el proyecto listo para desarrollar funcionalidades: repositorio higienizado, configuración centralizada,
núcleo transversal (errores, registros, base de datos y salud), reglas del SRS corregidas, modelos ORM con
migraciones, contenedores/CI y base del frontend. **No incluye funcionalidades de usuario final.**

## 2. Alcance

- Higiene de repositorio y documentación de decisiones.
- Dependencias fijadas y configuración por variables de entorno.
- Núcleo transversal: excepciones, registros estructurados, conexión a PostgreSQL, `/health` y arranque FastAPI.
- Corrección de reglas de negocio del código creacional existente (Builder, Prototype, Factory Method).
- Modelos ORM (11 tablas) y migraciones versionadas con Alembic.
- Docker Compose con `backend`, `frontend` y base de datos; CI con el trabajo `backend`.
- Frontend base: Vue 3 + Vite + Pinia + Vue Router, cliente HTTP y Nginx.

## 3. Fuera de alcance

- Funcionalidades de catálogo, auth, playlists, listening y recomendaciones (fases posteriores).
- Autenticación real, hash de contraseñas y rate limit (se habilitan en F1).
- Mecanismo definitivo de sesión más allá de la configuración (JWT).

## 4. Mapa de PRs

| PR | Rama | Entrega | Depende de |
|---|---|---|---|
| 0 | (decisiones) | `docs/decisiones.md` | — |
| A1 | `chore/higiene-repo` | `.gitignore`, `schema.sql` versionado, documentación | — |
| A2 | `feat/config-dependencias` | requirements, `Settings`, `.env.example`, ruff | A1 |
| A3 | `feat/nucleo-transversal` | excepciones, logs, base de datos, `main.py`, salud | A2 |
| A4 | `refactor/reglas-srs` | Builder, Prototype, Factory, referencias RN | A2 |
| B1 | `feat/modelos-orm` | 11 modelos y prueba de paridad | A2 |
| B2 | `feat/alembic` | Alembic, arranque de migraciones | B1 |
| A5 | `feat/contenedores-ci` | Dockerfile, compose, CI | A3, B2 |
| C1 | `feat/front-base` | dependencias, router, estado, estilos | — |
| C2 | `feat/front-api-cliente` | cliente HTTP y pruebas | C1 |
| C3 | `feat/front-nginx-docker` | nginx, Dockerfile, CSP | C1 |

## 5. Decisiones

El detalle vive en [`decisiones.md`](decisiones.md). Resumen:

- Clave de canción: `track_id`.
- Base de datos: 11 tablas, con `user_genre_preferences` y `user_artist_preferences` separadas.
- Sin rol administrador.
- No se citan versiones de documento; se usan los identificadores `RF`, `RN` y `RNF`.
- Sesión (TBD-04): JWT con `jwt_secret` y caducidad.
- Mínimo de búsqueda: `search_min_chars` en `Settings`.

## 6. Cómo ejecutar

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example ../.env        # ajustar los valores
pytest
ruff check .

# Aplicación (tras A3)
uvicorn app.main:app --reload
# http://localhost:8000/api/health  y  /api/docs

# Despliegue completo (tras A5)
docker compose up -d
```

## 7. Criterios de terminado

- `docker compose up` levanta base de datos, backend y frontend (RNF-035).
- `/api/health` responde 200; `/api/health/ready` responde 200 con la base disponible.
- Las migraciones versionadas se aplican al iniciar el contenedor (RNF-017).
- La configuración es 100 % por variables de entorno; sin constantes de negocio en el código.
- Sin rol administrador; sin `description` ni `is_favorite` en playlists.
- Modelos ORM (11 tablas) y esquema en paridad.
- El trabajo `backend` de CI queda en verde.

## 8. Registro de implementación

| Fecha | PR | Resumen |
|---|---|---|
| 2026-10-18 | 0 | Análisis de alineación SRS vs plan vs código. Se crea `docs/decisiones.md` y este documento. |
| 2026-10-18 | A1 | Ajuste de `.gitignore` (dumps/cobertura y `.opencode/`). Pendiente: versionar `schema.sql`, `git mv` y protección de ramas (lo ejecuta quien administra el repositorio). |
| 2026-10-18 | A2 | `requirements.txt`, `requirements-dev.txt`, `ruff.toml`, `Settings` completo con `from_env()`/`validate_runtime()`, `.env.example` y pruebas de configuración. |
| 2026-10-18 | A3 | Núcleo transversal: excepciones, logs JSON con `Request-ID` y cabeceras de seguridad, conexión a PostgreSQL, `/api/health` y `/api/health/ready`, routers base y arranque FastAPI. |
| 2026-10-18 | A4 | Reglas del SRS: Builder con límites por parámetro, Prototype con `is_skipped(threshold_s)`, Factory Method sin rol administrador, `search_min_chars` sustituye a `MIN_QUERY_LENGTH` y referencias `RN` corregidas. |
| 2026-10-18 | Aud | Auditoría independiente (calidad/sostenibilidad/entendibilidad) y correcciones: CI reparado (job `backend`, `requirements-dev.txt`, `ruff` y cobertura ≥ 70 %), proveedor simulado usa `youtube_max_results`, códigos HTTP completos, paridad `Settings`↔`.env.example`, `TrackMetadata` inmutable, docs del Singleton alineadas con RNF-021 y prueba de arquitectura. Verificado con 63 pruebas y cobertura 94 %. |
