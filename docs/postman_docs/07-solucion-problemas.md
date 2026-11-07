# 07 · Solución de problemas

## El backend no arranca

| Síntoma | Causa probable | Solución |
|---|---|---|
| `CONFIG_ERROR` por `DATABASE_URL` | Falta la variable o no empieza por `postgresql+psycopg://` | Revisar `.env` |
| `CONFIG_ERROR` por `JWT_SECRET` | Menos de 32 caracteres | Generar uno más largo |
| `CONFIG_ERROR` por `YOUTUBE_API_KEY` | `MUSIC_PROVIDER=youtube` sin clave | Usar `MUSIC_PROVIDER=simulated` |
| `Address already in use` | Puerto ocupado | Usar `8011` o detener el proceso |
| Error de conexión a PostgreSQL | Contenedor detenido o puerto incorrecto | `docker compose up -d db`, revisar `5434` |

## La base no tiene datos

| Síntoma | Solución |
|---|---|
| `GET /genres` devuelve `[]` | La base no tiene semillas; ejecutar `schema.sql` o cargar géneros |
| `GET /search` no devuelve resultados | Ejecutar `python -m app.catalog.seed_importer --all` |
| `tracks` está vacío | Igual que el anterior |
| `genre_seeds` está vacío | Igual que el anterior |

## Error 500 al buscar

| Causa | Solución |
|---|---|
| Falta el género `sin_clasificar` | Cargar la lista cerrada de géneros |
| `MUSIC_PROVIDER=youtube` sin red/clave | Cambiar a `simulated` |
| El proveedor devolvió datos inválidos | Revisar logs JSON del servidor |

## Postman

| Síntoma | Causa | Solución |
|---|---|---|
| `{{base_url}}` sin resolver | Environment no seleccionado | Seleccionar `Open Music UTP - Local` |
| `access_token` vacío | `Login` no se ejecutó o falló | Ejecutar `Register` y `Login` primero |
| `track_id` vacío | La búsqueda no devolvió resultados | Revisar semillas o usar `q=cafeteros` |
| `401` en `Me` | Token vencido o inválido | Volver a hacer login |
| `429` inesperado | Rate limit contaminado | Reiniciar `uvicorn` o usar otro `run_email` |
| `404` en una ruta | La fase aún no implementa ese módulo | Revisar el mapa de rutas |
| Las pruebas no aparecen | Pestaña incorrecta | Abrir `Test Results` |

## Orden de ejecución

Si ejecutas `Delete account` antes de `Me`, `Export` o los negativos, el token
dejará de servir. Respeta este orden:

1. Health
2. Auth
3. Catalog
4. Negativos
5. Privacy (eliminar al final)

## Catálogo inconsistente después de la demo

`POST /unplayable` deja la canción marcada. Para restaurar:

```bash
cd backend
python -m app.catalog.seed_importer --all
```

El importador vuelve a dejar las canciones semilla como embebibles.

## Comandos de diagnóstico

```bash
# Estado de la base
docker compose ps
docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "\dt"'

# Estado de migraciones
cd backend
alembic current
alembic check

# Pruebas
pytest -q

# Salud del backend
curl http://localhost:8010/api/health
curl http://localhost:8010/api/health/ready
```
