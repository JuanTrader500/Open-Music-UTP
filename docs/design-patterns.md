# Patrones de diseño (RNF-021)

Registro vivo de los patrones aplicados. Cómo se implementa cada uno:
`docs/requerimientos-funcionales.md` (ESC-01 a ESC-05) y `docs/abstract-factory.md`.

| Tipo | Patrón | Dónde | Estado |
|---|---|---|---|
| Creacional | Abstract Factory | `catalog/providers/` (familia YouTube/simulada, ESC-01 RF-010/011) | Implementado |
| Creacional | Builder | `playlists/builder.py` (ESC-02 RF-013) | Implementado |
| Creacional | Factory Method | `auth/factory.py` (ESC-03 RF-017/018) | Implementado |
| Creacional | Prototype | `listening/prototype.py` (ESC-04 RF-023/024) | Implementado |
| Creacional | Singleton | `core/config.py:get_settings` (acceso real, `lru_cache`; ESC-05 RNF-031); `core/singleton.py` + `AppRuntime` como demostración de RNF-021 | Implementado |
| Estructural | Adapter | `catalog/providers/youtube/adapter.py`; `frontend/src/api/client.js`; `frontend/src/player/playerController.js` | Implementado |
| Estructural | Proxy | `catalog/providers/cached_provider.py` (caché y cuota) | Implementado |
| Estructural | Decorator | `core/transactions.py` (`@transactional`) | Implementado |
| Estructural | Facade | `playlists/service.py`; `catalog/service.py` | Implementado |
| Comportamiento | (por definir, p. ej. Strategy para recomendaciones, Observer para el reproductor) | | Pendiente |

La sustentación detallada de los patrones estructurales, sus escenarios
Given/When/Then y su trazabilidad están en
`.opencode/documentacion_patrones_estructurales.md`.
