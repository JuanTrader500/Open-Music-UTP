# Colección Postman · Open Music UTP

## Archivos

- `OpenMusicUTP.postman_collection.json`: 13 rutas de salud, auth y catálogo.
- `local.postman_environment.json`: `base_url` y contraseña de la demo.

## Importar

1. Postman → `Import` → seleccionar ambos archivos.
2. Elegir el environment **Open Music UTP - Local**.
3. Verificar que `base_url` apunte al backend, por defecto
   `http://localhost:8010`.

## Preparar el backend

```bash
cd ..
# activa tu entorno Python 3.12 (venv o conda)
alembic check
python -m app.catalog.seed_importer --all
uvicorn app.main:app --reload --port 8010
```

## Orden de ejecución

1. `00 Health`
2. `01 Auth`
3. `02 Catalog`
4. `08 Negative/Errors`
5. `07 Privacy`

Las pruebas de privacidad van al final porque eliminan la cuenta de la demo.

## Variables

| Variable | Dónde se llena |
|---|---|
| `base_url` | Environment |
| `run_password` | Environment |
| `run_email` | Pre-request de `Register` |
| `user_id` | Test de `Register` |
| `access_token` | Test de `Login` |
| `track_id` | Test de `Search` |
| `catalog_before` | Test de `Search` |
| `rate_email` | Pre-request de `Rate limit 1/6` |

## Ejecutar con Newman

```bash
npx newman run postman/OpenMusicUTP.postman_collection.json \
  -e postman/local.postman_environment.json
```

## Cobertura de la colección

| Carpeta | Rutas |
|---|---|
| `00 Health` | `/api/health`, `/api/health/ready` |
| `01 Auth` | register, login, me, logout, export |
| `02 Catalog` | genres, artists, search, detail, unplayable |
| `07 Privacy` | export, delete account, login posterior |
| `08 Negative/Errors` | 401, 404, 405, 409, 422, 429 |

## Notas

- El JWT es sin estado: después de `Logout` el token sigue vigente hasta que
  expire. Es el comportamiento documentado en D-02.
- `Export` devuelve colecciones vacías en Fase 1; se completan en Fase 5.
- `POST /unplayable` deja la canción marcada. Para restaurar el catálogo:
  `python -m app.catalog.seed_importer --all`.
- El rate limit vive en memoria del proceso; reiniciar `uvicorn` lo limpia.
