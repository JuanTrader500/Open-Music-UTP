# 01 · Preparación del entorno

## 1. Ubicación del proyecto

```bash
cd /home/juan500/Documents/Universidad/patronesDiseño/open-music-utp
```

## 2. Base de datos

El contenedor debe estar activo y saludable:

```bash
docker compose ps
```

Salida esperada: `open-music-db` con estado `healthy`.

Si no está activo:

```bash
docker compose up -d db
```

En esta máquina el puerto local es `5434` (hay un override temporal porque el
`5433` estaba ocupado). El `.env` ya apunta a `localhost:5434`.

Verificar las tablas:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'
```

Deben aparecer las 11 tablas del esquema más `alembic_version`.

## 3. Entorno de Python

```bash
cd backend
# activa tu entorno Python 3.12 (venv o conda)
python --version
```

Debe ser Python 3.12.

## 4. Migraciones

```bash
alembic current
alembic check
```

Esperado:

- `alembic current`: `0323eb7fe24c (head)`.
- `alembic check`: `No new upgrade operations detected`.

Si la base está vacía:

```bash
alembic upgrade head
```

Si la base ya tiene el esquema v6:

```bash
alembic stamp head
```

No ejecutes `alembic upgrade head` sobre una base que ya tiene las tablas sin
revisar antes su estado.

## 5. Semillas del catálogo

```bash
python -m app.catalog.seed_importer --all
```

Salida esperada:

```text
PL_SIM_ROCK: 3 canciones importadas
PL_SIM_POP: 2 canciones importadas
PL_SIM_SALSA: 2 canciones importadas
```

El comando es idempotente: se puede ejecutar varias veces sin duplicar datos.
Además asegura los 45 géneros y los 440 artistas base del esquema, y restaura
`is_embeddable=true` en las canciones semilla, lo que sirve para repetir la demo
después de probar C-03. Con esto una base limpia creada con `alembic upgrade
head` queda lista sin ejecutar `schema.sql`.

Verificación rápida en la base:

```bash
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  -c "select count(*) from genres; select count(*) from artists; select count(*) from tracks;"'
```

Esperado: 45 géneros, 444 artistas (440 base + 4 simulados) y 7 canciones.

## 6. Arranque del servidor

```bash
cd backend
uvicorn app.main:app --reload --port 8010
```

Verificación:

```bash
curl http://localhost:8010/api/health
curl http://localhost:8010/api/health/ready
curl http://localhost:8010/api/catalog/genres
```

Esperado:

```json
{"status":"ok"}
{"status":"ready"}
[{"id":1,"code":"rock","name":"Rock"}, ...]
```

Documentación interactiva: <http://localhost:8010/api/docs>.

> Si el puerto `8010` está ocupado, usa `8011` y cambia `base_url` en el
> environment de Postman.

## 7. Variables de entorno relevantes

| Variable | Valor para la demo |
|---|---|
| `MUSIC_PROVIDER` | `simulated` |
| `DATABASE_URL` | `postgresql+psycopg://...@localhost:5434/openmusic` |
| `JWT_SECRET` | Cadena de 32+ caracteres |
| `SEARCH_MIN_CHARS` | 2 por defecto |
| `YOUTUBE_MAX_RESULTS` | 20 por defecto |
| `LOGIN_ATTEMPTS_PER_MINUTE` | 5 por defecto |
| `PASSWORD_MIN_LENGTH` | 8 por defecto |

## 8. Checklist previo a la demo

- [ ] `docker compose ps` muestra la BD healthy.
- [ ] `alembic current` está en head.
- [ ] `python -m app.catalog.seed_importer --all` ejecutado.
- [ ] `uvicorn` escuchando en el puerto elegido.
- [ ] `curl /api/health` y `/api/health/ready` responden 200.
- [ ] Postman con la colección y el environment importados.
- [ ] `base_url` del environment coincide con el puerto real.
