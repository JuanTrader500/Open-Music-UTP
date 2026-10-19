# Mapa de reutilización de componentes

Guía de qué piezas ya implementadas debe consumir cada módulo del backend y
cómo. Base de la regla "no toques lo que no es tuyo" que permite trabajar en
paralelo (ver `.opencode/PLAN_FASES_SIGUIENTES.md`).

## 1. Componente → quién lo usa

| Componente implementado | Lo usan | Cómo |
|---|---|---|
| `core/config.get_settings()` | Todos los routers y services | `Depends(get_settings)`; leer umbrales/límites |
| `core/database.get_db()` | Módulos con persistencia | `Depends(get_db)` → `Session` |
| `core/exceptions` (`MusicAppError` + 15) | Todos los services | Lanzar excepción de dominio; handlers ya en `main.py` |
| `core/logging` (`getLogger`, `request_id_var`) | Todos | `logging.getLogger(__name__)`; **no** llamar `configure_logging` |
| `catalog/providers` (`MusicProvider`, `build_provider_factory`, `TrackMetadata`) | `catalog`, `simulation` | Buscar / importar catálogo |
| `playlists/builder` (`PlaylistBuilder`, `Playlist`) | `playlists` | Construcción validada |
| `listening/prototype` (`ListeningRecord`) | `listening`, `simulation` | Crear / clonar escuchas |
| `auth/factory` (`creator_for`, `RegisteredCreator`…) | `auth`, `simulation` | Crear usuarios |
| `core/singleton` (`AppRuntime`, `SingletonMeta`) | **Nadie** | Solo demostración (RNF-021) |
| `core/security` | — | **No existe aún** (trabajo de `auth`) |

## 2. Núcleo transversal (`core/*`) — lo reutilizan todos

- **`get_settings()`**: inyectar con `Depends(get_settings)`. Campos por módulo
  (no hardcodear): `playlists` → `max_playlists_per_user`,
  `max_tracks_per_playlist`, `playlist_name_max_length`; `listening` →
  `skipped_threshold_s`, `previous_track_threshold_s`; `recommendations` →
  `onboarding_min_genres/max`, `genre_initial_weight_min`,
  `artist_initial_weight_min`, `preference_halving_minutes`,
  `recency_half_life_days`, `recommendations_list_size`, `exploration_share`;
  `catalog` → `music_provider`, `search_min_chars`, `youtube_max_results`;
  `auth` → `password_min_length`, `jwt_secret`, `access_token_expire_minutes`,
  `login_attempts_per_minute`.
- **`get_db()`**: `get_db` no hace `commit`; **el service hace `db.commit()`**.
- **Excepciones por módulo**: `playlists` → `ValidationFailedError`
  (traduce el `ValueError` del Builder), `PlaylistLimitError`,
  `TrackLimitError`, `DuplicateTrackError`, `TrackNotFoundError`;
  `auth` → `EmailTakenError`, `InvalidCredentialsError`, `UnauthorizedError`,
  `RateLimitedError`; `catalog` → `InvalidQueryError`, `ProviderError`,
  `QuotaExceededError`, `TrackNotFoundError`; `recommendations` →
  `ValidationFailedError`, `NotFoundError`.
- **Logging**: `logging.getLogger(__name__)`; no loggear contraseñas ni tokens.
- **`core/singleton`**: prohibido en módulos (lo verifica
  `tests/unit/test_architecture.py`).

## 3. Uso puntual de los patrones ya implementados

- **`catalog/providers`**: `catalog/service.py` usa
  `build_provider_factory(settings)` → `MusicProvider` (`search_tracks`,
  `import_playlist`) y traduce `ProviderError`/`QuotaExceededError`;
  `catalog/seed_importer.py` importa playlists semilla; `catalog/genres.py`,
  `models.py`, `repository.py` persisten `TrackMetadata` (el JSON crudo de
  YouTube nunca sale de `youtube/mappers.py`). `recommendations/service.py`
  **no** habla con el provider: lee "populares" vía el **service** de `catalog`.
- **`playlists/builder`**: `playlists/service.py` construye con
  `PlaylistBuilder(owner_id, max_name_length=..., max_tracks=...)`, traduce
  `ValueError` → `ValidationFailedError` y usa `reordered()` (RF-015).
- **`listening/prototype`**: `listening/service.py` usa
  `is_skipped(settings.skipped_threshold_s)`; `simulation/generator.py` clona
  eventos y marca `is_simulated` (RN-014).
- **`auth/factory`**: `auth/service.py` usa `creator_for("guest")` /
  `RegisteredCreator(..., min_password_length=...)`; `simulation` lo usa para
  usuarios demo.

## 4. Fronteras (quién NO usa qué)

- **Routers**: solo validan (`schemas`) y llaman al **service**; nunca provider,
  ORM ni `Session` directa.
- **Entre módulos**: se llama al **service** ajeno, nunca a su `repository`.
- **ORM**: no sale del módulo; el router responde con `schemas`.
- **Prohibido**: `async def` con BD/YouTube, `print()` en `app`, constantes de
  negocio en el código.
