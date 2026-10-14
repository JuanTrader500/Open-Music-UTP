# Arquitectura

Monolito modular en el backend (RNF-020), SPA estática en el frontend y PostgreSQL, desplegados con Docker Compose (RNF-019).

```
Usuario -> Frontend (Nginx) -> Backend FastAPI -> PostgreSQL
                  |                  |
                  |                  +-> YouTube Data API v3 (solo desde el backend)
                  +-> YouTube IFrame Player API (reproducción)
```

Reglas:
- Los módulos del backend (`auth`, `catalog`, `playlists`, `listening`, `recommendations`) se comunican solo mediante interfaces definidas (`service.py`), nunca accediendo a los modelos o repositorios de otro módulo.
- La clave de YouTube nunca llega al navegador (RNF-003).
