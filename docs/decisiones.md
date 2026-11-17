# Decisiones de desarrollo

Registro de decisiones que afectan el contrato, la base de datos o la forma de
trabajo. Cada decisión se mantiene aunque cambie la implementación.

| ID | Decisión | Justificación | Impacto |
|---|---|---|---|
| D-01 | La base de datos existente manda; Alembic replica el esquema v6 | Evitar recrear la base y perder datos | `stamp head` en bases existentes; `upgrade head` en bases limpias |
| D-02 | El logout es JWT sin estado | El SRS no exige revocación en servidor | El token sigue válido hasta `exp`; el cliente lo descarta |
| D-03 | JWT firmado con HS256 y `JWT_SECRET` | Simplicidad académica y configuración única | El secreto debe tener 32+ caracteres |
| D-04 | Hash de contraseñas con Argon2id | RNF-026 y buena práctica actual | Dependencia `argon2-cffi` |
| D-05 | `get_current_user` y `get_optional_user` viven en `auth/dependencies.py` | Evitar que `core` dependa de un módulo funcional | `core/security.py` solo concentra el mecanismo |
| D-06 | Rate limit de login en memoria por proceso | Suficiente para desarrollo y demo | No se comparte entre workers; reiniciar limpia el estado |
| D-07 | El registro solo exige `accept_privacy=true` | Evita agregar una columna no prevista en el esquema | No existe `users.privacy_accepted_at` |
| D-08 | Los IDs de canción son `track_id` | El esquema v6 renombró `video_id` | Todo el código y los contratos usan `track_id` |
| D-09 | Favoritos es un módulo propio (`app/favorites/`) | Separar responsabilidades y permitir su evolución | Prefijo `/api/favorites` en Fase 3 |
| D-10 | La demo usa `MUSIC_PROVIDER=simulated` | Evitar cuota de YouTube y dependencia de red | El catálogo se llena con `PL_SIM_*` |
| D-11 | El importador de semillas es idempotente | Permite repetir la demo y reparar el catálogo | Upsert por `track_id` y `playlist_id` |
| D-12 | Prioridad de género: semilla > artista > categoría > sin clasificar | RF-011 y RN-009 | `genre_source` refleja la fuente usada |
| D-13 | Una canción marcada no reproducible no se rehabilita en búsquedas | RN-012 | El importador de semillas puede restaurarla explícitamente |
| D-14 | El límite de búsqueda sale de `youtube_max_results` | Evitar constantes de negocio en código | `limit` mayor al configurado devuelve 422 |
| D-15 | El catálogo no devuelve modelos ORM ni JSON crudo del proveedor | Mantener el contrato estable | Se usan schemas Pydantic con artista y género anidados |
| D-16 | `sin_clasificar` no entra en recomendaciones por género | RN-009 | Se excluye en las consultas de recomendaciones de Fase 4 |
| D-17 | Las pruebas de integración usan una base terminada en `_test` | Evitar borrar datos de desarrollo | `conftest.py` valida el nombre de la base |
| D-18 | CI levanta PostgreSQL 16 como servicio | Probar migraciones y endpoints reales | `.github/workflows/test.yml` |
| D-19 | El catálogo se prueba siempre con el proveedor simulado | RNF-033 y reproducibilidad | No se llama a YouTube en pruebas ni en Newman |
| D-20 | Los errores usan `{"code","message"}` | Contrato uniforme para el frontend | Todos los handlers respetan el envelope |
