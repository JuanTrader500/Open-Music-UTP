# Open Music UTP

Aplicación web que reproduce música buscada en YouTube, con cuentas de usuario, playlists, registro de escucha y recomendaciones con reglas estáticas (sin aprendizaje automático).
Proyecto académico de la Universidad Tecnológica de Pereira (UTP). Basado en el SRS **SRS-RMW-001 v0.4** (ISO/IEC/IEEE 29148). Licencia MIT.

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, python-dotenv |
| API externa | YouTube Data API v3 (`google-api-python-client`) + IFrame Player API |
| Pruebas | pytest |
| Base de datos | PostgreSQL (volumen Docker) |
| Frontend | HTML/CSS/JS; Vue 3 + Vite propuesto (TBD-01) |
| Despliegue | Docker Compose: `backend`, `frontend`, `db` |

## Estado actual

| Pieza | Estado |
|---|---|
| Estructura del repositorio y documentación | Lista |
| `catalog/providers/` (proveedor de música con **Abstract Factory**) | **Implementado y con pruebas** |
| Todo lo demás | Esqueleto con TODO (cada archivo indica los RF que le corresponden) |

## Inicio rápido (proveedor de música)

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp ../.env.example ../.env        # edita MUSIC_PROVIDER y YOUTUBE_API_KEY
pytest                            # pruebas (no llaman a YouTube)

# Demo sin cuota (datos simulados)
python -m scripts.demo_youtube --provider simulated search rock

# Demo real (requiere YOUTUBE_API_KEY en .env)
python -m scripts.demo_youtube --provider youtube search "salsa"
python -m scripts.demo_youtube --provider youtube playlist <ID_DE_PLAYLIST>
```

La explicación del patrón, el diagrama UML y los puntos para la sustentación están en [`docs/abstract-factory.md`](docs/abstract-factory.md).

## Estructura

```
open-music-utp/
├── README.md · LICENSE · .env.example · .gitignore · docker-compose.yml
├── docs/                      architecture.md · abstract-factory.md · design-patterns.md
├── backend/
│   ├── app/
│   │   ├── main.py            punto de entrada FastAPI
│   │   ├── core/              config, excepciones, base de datos, seguridad, logging
│   │   ├── auth/              cuentas y sesión
│   │   ├── catalog/           catálogo, búsqueda, géneros
│   │   │   └── providers/     Abstract Factory (YouTube / simulado)   <- implementado
│   │   ├── playlists/         playlists y favoritos
│   │   ├── listening/         registro de escucha e historial
│   │   ├── recommendations/   onboarding y recomendaciones
│   │   └── simulation/        CLI de usuarios demo
│   ├── migrations/            migraciones versionadas
│   ├── scripts/               demo_youtube.py
│   └── tests/                 catalog/ · unit/ · integration/ · acceptance/
└── frontend/
    └── src/                   player/ · ui/ · views/ · api/
```

Cada módulo del backend sigue la misma forma: `router.py` (endpoints), `service.py` (lógica, única puerta de entrada para otros módulos), `schemas.py` (pydantic), `models.py` (tablas) y `repository.py` (acceso a datos).

## Módulos y qué hace cada uno

| Módulo | Qué hace | Requisitos |
|---|---|---|
| `core` | Configuración por variables de entorno, excepciones compartidas, conexión a PostgreSQL, hash y sesiones, logs estructurados | RNF-015 a RNF-017, RNF-026 a RNF-031, RNF-034 |
| `catalog` | Catálogo global de canciones: busca, guarda metadatos, asigna género (semilla > artista > categoría YouTube > sin clasificar), importa playlists semilla, excluye videos no embebibles | RF-009 a RF-012, RN-009, RN-012 |
| `catalog/providers` | Capa de acceso a YouTube desacoplada con Abstract Factory; incluye una familia simulada para pruebas sin cuota | RNF-003, RNF-023, RNF-024, RNF-033 |
| `auth` | Registro, inicio y cierre de sesión, límite de intentos, exportar y eliminar datos | RF-017, RF-018, RF-020, RF-022, RN-004, RN-015 |
| `playlists` | Crear, editar, reordenar y eliminar playlists; favoritos; límites por usuario; importar playlists del invitado | RF-013 a RF-016, RF-019, RF-020, RN-010 |
| `listening` | Registra segundos realmente escuchados, marca pistas omitidas (< 30 s), historial y resumen por género y artista | RF-023, RF-024, RN-005, RN-006 |
| `recommendations` | Onboarding de géneros y artistas; recomendaciones por tipo de usuario (invitado, sin historial, con historial) | RF-021, RF-025 a RF-027, RN-006 a RN-009 |
| `simulation` | CLI que genera usuarios y escuchas simulados, reproducibles con semilla y marcados | RF-028, RN-014 |
| `frontend/player` | Control del reproductor IFrame: reproducir, pausar, progreso, volumen, cola, aleatorio, repetir, pistas no reproducibles | RF-001 a RF-009, RNF-004, RNF-011, RNF-014 |
| `frontend/ui` y `views` | Pantallas: inicio, búsqueda, biblioteca, onboarding, login, perfil. Responsive y accesible | RF-012, RNF-001, RNF-002, RNF-007 a RNF-009 |

## Orden de desarrollo sugerido

El orden respeta dependencias: primero lo que no depende de nada y lo que más riesgo técnico tiene.

| Fase | Qué construir | Por qué en este punto | Requisitos |
|---|---|---|---|
| 0 | Repositorio, `.env`, entorno Python 3.12, clave de YouTube | Base para todo | RNF-022, RNF-031, RNF-035 |
| **1** | **`catalog/providers` (Abstract Factory)** — **ya hecho** | Es el mayor riesgo externo (cuota, API) y permite probar sin red | RNF-003, RNF-033 |
| 2 | `main.py`, `core/database.py`, migraciones, tablas base, Docker Compose con `/health` | Sin base de datos y servidor no se persiste nada | RNF-005, RNF-015 a RNF-019, RNF-025 |
| 3 | `catalog`: guardar canciones, géneros, importar playlists semilla, endpoint de búsqueda | Llena el catálogo y habilita todo lo demás | RF-010 a RF-012, RN-009, RN-012 |
| 4 | `frontend/player` + búsqueda en la interfaz (modo invitado) | Entrega el valor central: buscar y escuchar | RF-001 a RF-009, RF-019, RNF-004 |
| 5 | `auth` | Cuentas necesarias para persistir datos | RF-017, RF-018, RNF-026 a RNF-029 |
| 6 | `playlists` y favoritos, importar datos del invitado | Requiere cuentas y catálogo | RF-013 a RF-016, RF-020 |
| 7 | `listening` + onboarding | Alimenta las recomendaciones | RF-021, RF-023, RF-024 |
| 8 | `recommendations` | Necesita preferencias, historial y catálogo | RF-025 a RF-027 |
| 9 | `simulation` | Genera datos para probar y demostrar recomendaciones | RF-028 |
| 10 | Privacidad: exportar y eliminar cuenta | Cierra el ciclo de datos | RF-022, RNF-032 |
| 11 | Endurecimiento: seguridad, accesibilidad, rendimiento, cobertura >= 70 % | Verificación de no funcionales | RNF-001, 007, 010 a 014, 029 a 034 |
| 12 | Verificación final y trazabilidad | Criterio de cierre del SRS | SRS sección 4 y Apéndice A |

Las decisiones pendientes (TBD-01 a TBD-09) están en el Apéndice C del SRS; resuelve cada una antes de la fase que la necesita (por ejemplo, TBD-02 antes de la fase 2 y TBD-04 antes de la fase 5).

## Convenciones

- Identificadores: `RF-###` funcionales, `RNF-###` no funcionales, `RN-###` reglas de negocio. Cada archivo del esqueleto indica los que le corresponden.
- Los parámetros configurables (umbrales, límites) viven en configuración, no en el código.
- Las pruebas automatizadas no deben llamar a la API real de YouTube: usa `MUSIC_PROVIDER=simulated`.
- Nunca subas `.env` ni claves al repositorio.
