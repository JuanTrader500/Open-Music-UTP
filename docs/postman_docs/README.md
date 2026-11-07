# Postman · Open Music UTP

Guía para ejecutar las pruebas manuales y la demostración en vivo del backend.

## Requisitos

- Docker con el contenedor `open-music-db` healthy.
- Entorno conda `open-music` con `backend/requirements-dev.txt`.
- Postman instalado (o Newman para ejecución por consola).
- Colección `backend/postman/OpenMusicUTP.postman_collection.json`.
- Environment `backend/postman/local.postman_environment.json`.

## Orden de lectura

| Documento | Contenido |
|---|---|
| [01-preparacion-entorno.md](01-preparacion-entorno.md) | Base de datos, migraciones, semillas y arranque del servidor |
| [02-importar-coleccion.md](02-importar-coleccion.md) | Importar colección y environment en Postman |
| [03-pruebas-auth.md](03-pruebas-auth.md) | Registro, login, JWT, perfil, exportación y borrado |
| [04-pruebas-catalogo.md](04-pruebas-catalogo.md) | Búsqueda, detalle, no reproducible, géneros y artistas |
| [05-guion-demostracion-vivo.md](05-guion-demostracion-vivo.md) | Guion minuto a minuto para la exposición |
| [06-negativos-y-rate-limit.md](06-negativos-y-rate-limit.md) | Errores 401/404/409/422/429 |
| [07-solucion-problemas.md](07-solucion-problemas.md) | Fallos frecuentes y cómo resolverlos |

## Resumen rápido

```bash
cd backend
# activa tu entorno Python 3.12 (venv o conda)
alembic check
python -m app.catalog.seed_importer --all
uvicorn app.main:app --reload --port 8010
```

Abrir Postman, importar la colección y el environment, seleccionar
`Open Music UTP - Local` y ejecutar las carpetas en este orden:

1. `00 Health`
2. `01 Auth`
3. `02 Catalog`
4. `08 Negative/Errors`
5. `07 Privacy`

> El puerto `8000` puede estar ocupado por otra aplicación. Usa `8010` u `8011`
> y actualiza `base_url` en el environment.

## Estado esperado del backend

- Rutas disponibles: salud (2), auth (6) y catálogo (5).
- Proveedor activo: `MUSIC_PROVIDER=simulated`.
- Base de datos con 45 géneros, 440 artistas base y 4 artistas simulados (444 en total) y 7 canciones simuladas.
- Sin llamadas a YouTube durante la demo.
