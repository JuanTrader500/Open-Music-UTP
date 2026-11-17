# Open Music UTP

[![Tests](https://github.com/JuanTrader500/Open-Music-UTP/actions/workflows/test.yml/badge.svg)](https://github.com/JuanTrader500/Open-Music-UTP/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.146-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Vue 3](https://img.shields.io/badge/Vue-3-42B883?logo=vue.js&logoColor=white)](https://vuejs.org/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)

**Open Music UTP** es una aplicación web de código abierto para buscar canciones
en YouTube, explorar sus metadatos y reproducirlas desde una interfaz moderna,
sin salir de la página.

Es un proyecto académico de la **Universidad Tecnológica de Pereira (UTP)**,
construido como una aplicación full stack real: API REST, base de datos
PostgreSQL, frontend Vue, pruebas automatizadas, contenedores y despliegue
reproducible. Está basado en el SRS **SRS-RMW-001 v0.4** y se distribuye bajo
licencia **MIT**.

> La interfaz actual se concentra en el flujo de descubrimiento y reproducción.
> El backend ya incluye autenticación y playlists; la exposición completa de
> esas funciones en la interfaz forma parte del roadmap.

---

## Tabla de contenido

- [Propuesta](#propuesta)
- [Características](#características)
- [Stack](#stack)
- [Arquitectura](#arquitectura)
- [Patrones de diseño](#patrones-de-diseño)
- [Inicio rápido](#inicio-rápido)
- [Configuración](#configuración)
- [Cómo funciona la búsqueda y la reproducción](#cómo-funciona-la-búsqueda-y-la-reproducción)
- [Desarrollo local](#desarrollo-local)
- [Pruebas y calidad](#pruebas-y-calidad)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Roadmap](#roadmap)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## Propuesta

La mayoría de los proyectos académicos se quedan en una demo que solo funciona
en la máquina de quien la creó. Open Music UTP busca lo contrario: una base
mantenible, documentada y ejecutable con un solo comando.

El proyecto pone énfasis en:

- **Separación de responsabilidades:** routers, servicios, repositorios y
  proveedores externos tienen límites claros.
- **Patrones de diseño aplicados con propósito:** no como decoración, sino para
  resolver integración, caché, transacciones y coordinación de subsistemas.
- **Pruebas sin depender de YouTube:** el proveedor simulado permite validar el
  flujo completo sin consumir cuota.
- **Reproducibilidad:** Docker Compose, migraciones Alembic y variables de
  entorno documentadas.
- **Código abierto:** cualquiera puede ejecutarlo, revisarlo, mejorarlo o
  desplegarlo.

---

## Características

- 🔎 **Búsqueda de canciones en YouTube** con metadatos, miniaturas y duración.
- ▶️ **Reproducción embebida** con la YouTube IFrame Player API.
- 🎧 **Reproductor integrado** con play/pausa, progreso, búsqueda de tiempo y
  enlace al video original.
- 🎨 **Interfaz responsive** inspirada en reproductores modernos, con búsquedas
  rápidas y secciones de descubrimiento.
- 🧩 **Proveedor de música desacoplado**: YouTube real o catálogo simulado.
- 🗄️ **Persistencia de catálogo** en PostgreSQL con migraciones Alembic.
- 🛡️ **Manejo tolerante de resultados incompletos** de YouTube.
- ⚡ **Caché de búsquedas** con TTL, LRU y protección de cuota.
- 🔐 **Autenticación JWT, rate limiting y hash de contraseñas** en el backend.
- 📚 **Playlists, favoritos y reordenamiento** disponibles en la API.
- 🐳 **Docker Compose** con `db`, `backend`, `frontend` y `pgadmin`.
- ✅ **Pruebas automatizadas** de backend y frontend, más workflow de CI.

---

## Stack

| Capa | Tecnología |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn, Pydantic, SQLAlchemy 2.0 |
| Base de datos | PostgreSQL 16, Alembic, psycopg 3 |
| Frontend | Vue 3, Vite, nginx |
| API externa | YouTube Data API v3 + YouTube IFrame Player API |
| Pruebas | pytest, Vitest, jsdom, Vue Test Utils |
| Infraestructura | Docker Compose, volúmenes persistentes, healthchecks |
| Calidad | Ruff, GitHub Actions, cobertura mínima del 70 % |

---

## Arquitectura

```text
Usuario
  │
  ▼
Frontend Vue + nginx
  │  /api/*
  ▼
FastAPI
  ├── auth              cuentas, JWT, rate limit
  ├── catalog           búsqueda, persistencia, géneros, artistas
  │     └── providers   Abstract Factory: YouTube / simulado
  ├── playlists         CRUD, favoritos, reordenamiento
  ├── listening         registro de escucha
  └── recommendations   onboarding y recomendaciones
        │
        ▼
PostgreSQL
```

La API sigue un monolito modular. Cada módulo expone su `service.py` como única
puerta de entrada; los routers no acceden directamente a modelos ni
repositorios de otros módulos.

### Módulos principales

| Módulo | Responsabilidad | Estado |
|---|---|---|
| `core` | Configuración, excepciones, base de datos, seguridad, logging | Implementado |
| `catalog` | Búsqueda, catálogo, géneros, artistas, semillas | Implementado |
| `catalog/providers` | Proveedores YouTube y simulado | Implementado |
| `auth` | Registro, login, JWT, privacidad | Implementado |
| `playlists` | Playlists, favoritos, reordenamiento | Implementado |
| `frontend` | Búsqueda, tarjetas, reproductor y estados de UI | Implementado |
| `listening` | Registro de escucha e historial | En progreso |
| `recommendations` | Onboarding y recomendaciones | En progreso |
| `simulation` | Generación de datos simulados | En progreso |

---

## Patrones de diseño

El proyecto aplica patrones creacionales, estructurales y de comportamiento de
forma incremental, documentando el problema que resuelve cada uno.

| Tipo | Patrón | Dónde |
|---|---|---|
| Creacional | **Abstract Factory** | `catalog/providers/` |
| Creacional | **Builder** | `playlists/builder.py` |
| Creacional | **Factory Method** | `auth/factory.py` |
| Creacional | **Prototype** | `listening/prototype.py` |
| Creacional | **Singleton** | `core/config.py` |
| Estructural | **Adapter** | `youtube/adapter.py`, `api/client.js`, `playerController.js` |
| Estructural | **Proxy** | `catalog/providers/cached_provider.py` |
| Estructural | **Decorator** | `core/transactions.py` |
| Estructural | **Facade** | `playlists/service.py`, `catalog/service.py` |

Documentación relacionada:

- [`docs/design-patterns.md`](docs/design-patterns.md)
- [`docs/abstract-factory.md`](docs/abstract-factory.md)
- [`docs/requerimientos-funcionales.md`](docs/requerimientos-funcionales.md)

> El documento detallado de la entrega de patrones estructurales, con escenarios
> Given/When/Then y trazabilidad al código, se conserva en
> `.opencode/documentacion_patrones_estructurales.md` como material de trabajo
> local.

---

## Inicio rápido

### Requisitos

- Docker Engine o Docker Desktop.
- Docker Compose v2.
- Una clave de **YouTube Data API v3** si se quiere buscar en YouTube real.
- Internet para descargar imágenes y cargar el reproductor.

### 1. Clonar y configurar

```bash
git clone https://github.com/JuanTrader500/Open-Music-UTP.git
cd Open-Music-UTP
cp .env.example .env
```

Edita `.env` y define al menos:

```env
MUSIC_PROVIDER=youtube
YOUTUBE_API_KEY=tu_clave_de_youtube_data_api_v3
JWT_SECRET=un_secreto_de_al_menos_32_caracteres
```

Genera el secreto con:

```bash
openssl rand -hex 32
```

### 2. Levantar los servicios

```bash
docker compose up -d --build
docker compose ps
```

### 3. Abrir la aplicación

| Servicio | URL |
|---|---|
| Frontend | <http://localhost:8956> |
| API / Swagger | <http://localhost:7845/api/docs> |
| pgAdmin | <http://localhost:8081> |
| PostgreSQL | `127.0.0.1:5433` |

La primera vez, el backend aplica migraciones, asegura el catálogo base y
arranca. Si el volumen ya existía con el esquema anterior, lo detecta y lo
conserva.

### 4. Detener sin borrar datos

```bash
docker compose down
```

> `docker compose down -v` elimina la base de datos y la configuración de
> pgAdmin. Úsalo solo si realmente quieres reiniciar desde cero.

---

## Configuración

Las variables se leen desde `.env`. Las principales son:

| Variable | Descripción | Ejemplo |
|---|---|---|
| `MUSIC_PROVIDER` | Proveedor de música: `youtube` o `simulated` | `youtube` |
| `YOUTUBE_API_KEY` | Clave de YouTube Data API v3, solo backend | `AIza...` |
| `YOUTUBE_MAX_RESULTS` | Máximo de resultados por búsqueda | `20` |
| `SEED_CATALOG` | Importa playlists simuladas al arrancar | `false` |
| `POSTGRES_USER` | Usuario de PostgreSQL | `postgres` |
| `POSTGRES_PASSWORD` | Contraseña de PostgreSQL | `cambiar_en_produccion` |
| `POSTGRES_DB` | Nombre de la base | `openmusic` |
| `JWT_SECRET` | Secreto de firma de tokens | `openssl rand -hex 32` |
| `CORS_ORIGINS` | Orígenes permitidos | `http://localhost:8956` |
| `CATALOG_CACHE_TTL_S` | TTL de caché de búsquedas | `300` |
| `CATALOG_CACHE_MAX_ENTRIES` | Entradas máximas de caché | `256` |

**Importante:** `YOUTUBE_API_KEY` es la única clave de YouTube del proyecto. La
IFrame Player API se ejecuta en el navegador y no requiere clave. Nunca expongas
`YOUTUBE_API_KEY` en el frontend.

La guía completa de ejecución, con pgAdmin, solución de problemas y despliegue
local, está en [`docs/guia_ejecucion/README.md`](docs/guia_ejecucion/README.md).

---

## Cómo funciona la búsqueda y la reproducción

```text
Frontend
  │  GET /api/catalog/search?q=...
  ▼
Backend FastAPI
  │  YouTube Data API v3 (YOUTUBE_API_KEY)
  ▼
PostgreSQL
  │  canciones, artistas, géneros
  ▼
Frontend
  │  track_id
  ▼
YouTube IFrame Player API (sin API key)
```

1. El usuario busca una canción desde la interfaz.
2. El backend consulta YouTube y persiste los resultados.
3. El frontend recibe `track_id`, título, artista, género y miniatura.
4. Al seleccionar una tarjeta, el navegador carga el video con la IFrame API.

La búsqueda es **global**: no requiere iniciar sesión ni tener una playlist. Las
playlists solo se usan para guardar y organizar canciones.

Si se usa `MUSIC_PROVIDER=simulated`, la interfaz funciona con un catálogo de
demostración, pero los IDs no son videos reales de YouTube.

---

## Desarrollo local

### Backend

```bash
docker compose up -d db

cd backend
python3.12 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

alembic upgrade head
python -m app.catalog.seed_importer --base-only
uvicorn app.main:app --reload --port 7845
```

API: <http://localhost:7845/api/docs>

### Frontend

```bash
cd frontend
npm ci
npm run dev
```

Vite: <http://127.0.0.1:5173>

El proxy de desarrollo redirige `/api` al backend en `7845`.

---

## Pruebas y calidad

```bash
make test            # backend + frontend
make test-backend    # pytest
make test-frontend   # Vitest
make lint            # ruff format + ruff check
make build-frontend  # build de producción
```

El backend usa una base de pruebas separada. Ejemplo:

```bash
TEST_DATABASE_URL=postgresql+psycopg://usuario:password@127.0.0.1:5433/openmusic_test \
  pytest backend -q
```

Las pruebas no llaman a la API real de YouTube: usan `MUSIC_PROVIDER=simulated`
y dobles de prueba. El workflow de GitHub Actions ejecuta:

- Formato y lint con Ruff.
- Pruebas de backend con cobertura mínima del 70 %.
- Verificación de migraciones Alembic.
- Pruebas de frontend con Vitest.
- Auditoría de dependencias de producción.
- Build de Vite.

---

## Estructura del proyecto

```text
open-music-utp/
├── backend/
│   ├── app/
│   │   ├── core/              configuración, base de datos, seguridad, logging
│   │   ├── auth/              cuentas y sesión
│   │   ├── catalog/           búsqueda, catálogo y proveedores
│   │   ├── playlists/         playlists y favoritos
│   │   ├── listening/         registro de escucha
│   │   ├── recommendations/   onboarding y recomendaciones
│   │   └── simulation/        datos simulados
│   ├── migrations/            migraciones Alembic
│   └── tests/                 unitarias, integración y aceptación
├── frontend/
│   ├── src/
│   │   ├── api/               cliente REST
│   │   ├── components/        tarjetas de canción
│   │   ├── player/            adaptador de IFrame API
│   │   └── utils/             utilidades de formato
│   └── vite.config.js
├── docs/                      arquitectura, patrones, guías y Postman
├── docker-compose.yml
├── Makefile
├── .env.example
└── README.md
```

---

## Roadmap

- [x] Catálogo base y búsqueda en YouTube.
- [x] Proveedor simulado para pruebas sin cuota.
- [x] Autenticación JWT y gestión de cuentas.
- [x] Playlists y favoritos en la API.
- [x] Frontend de búsqueda y reproducción.
- [x] Interfaz responsive con reproductor integrado.
- [x] Patrones creacionales y estructurales documentados.
- [ ] Exponer login, playlists y favoritos en la interfaz.
- [ ] Registro de escucha e historial en la UI.
- [ ] Recomendaciones y onboarding completos.
- [ ] Simulación de usuarios y escuchas.
- [ ] Cobertura y accesibilidad como criterios de cierre.

---

## Contribuir

Las contribuciones son bienvenidas. Para proponer un cambio:

1. Haz un fork del repositorio.
2. Crea una rama descriptiva:
   ```bash
   git checkout -b feat/mi-aporte
   ```
3. Mantén el estilo del proyecto y agrega pruebas cuando corresponda.
4. Ejecuta las verificaciones:
   ```bash
   make test
   make lint
   make build-frontend
   ```
5. Abre un pull request explicando el problema y la solución.

Para reportar un bug, incluye:

- Pasos para reproducirlo.
- Resultado esperado y resultado actual.
- Logs relevantes.
- Versión de Docker, Python o Node si aplica.

---

## Licencia

Este proyecto se distribuye bajo la licencia **MIT**. Consulta [`LICENSE`](LICENSE)
para más detalles.

---

## Créditos

Desarrollado como proyecto académico de la **Universidad Tecnológica de Pereira
(UTP)**, basado en el SRS **SRS-RMW-001 v0.4** y en prácticas de ingeniería de
software, arquitectura modular y patrones de diseño.

Si este proyecto te resulta útil, considera darle una estrella ⭐ al repositorio.
