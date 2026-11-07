# 05 · Guion de demostración en vivo

Duración objetivo: **10–12 minutos**.

## Antes de empezar

- [ ] Proyector y Postman abiertos.
- [ ] `uvicorn` corriendo en el puerto `8010`.
- [ ] `base_url` del environment apunta a ese puerto.
- [ ] Semillas cargadas: `python -m app.catalog.seed_importer --all`.
- [ ] Pestaña `Test Results` visible.
- [ ] `curl http://localhost:8010/api/health` responde `{"status":"ok"}`.

## Guion minuto a minuto

| Min | Acción | Request | Resultado esperado | Qué decir |
|---|---|---|---|---|
| 0:00 | Abrir Swagger | `GET /api/docs` | 13 rutas | “Este es el contrato HTTP de la API.” |
| 0:45 | Salud | `GET /api/health` | 200 `ok` | “El proceso está vivo.” |
| 1:00 | Disponibilidad | `GET /api/health/ready` | 200 `ready` | “La base de datos responde.” |
| 1:30 | Registro | `POST /api/auth/register` | 201 | “Cuenta creada y correo normalizado.” |
| 2:15 | Login | `POST /api/auth/login` | 200 + JWT | “Token firmado con expiración de una hora.” |
| 2:45 | Inspeccionar JWT | Test de `Login` | `sub`, `iat`, `exp` | “El cliente puede leer los claims, no la firma.” |
| 3:15 | Perfil | `GET /api/auth/me` | 200 | “Ruta protegida por Bearer.” |
| 3:45 | Exportación | `GET /api/auth/export` | 200 | “Datos personales del usuario.” |
| 4:15 | Géneros | `GET /api/catalog/genres` | 45 géneros | “Catálogo cerrado del SRS.” |
| 4:45 | Artistas | `GET /api/catalog/artists?limit=5` | 5 artistas | “Artistas semilla.” |
| 5:15 | Búsqueda | `GET /api/catalog/search?q=cafeteros&limit=10` | 2 tracks | “Buscamos sin consumir YouTube: proveedor simulado.” |
| 6:00 | Persistencia | `GET /api/catalog/tracks/{{track_id}}` | 200 | “La búsqueda guardó la canción y el artista.” |
| 6:30 | No reproducible | `POST /api/catalog/tracks/{{track_id}}/unplayable` | 204 | “El video ya no es reproducible.” |
| 7:00 | Verificar exclusión | Repetir búsqueda `cafeteros` | 1 track | “La canción marcada desapareció (RN-012).” |
| 7:30 | Query corta | `GET /api/catalog/search?q=a` | 422 `INVALID_QUERY` | “Validación antes de gastar cuota.” |
| 8:00 | Track inexistente | `GET /api/catalog/tracks/no-existe` | 404 `TRACK_NOT_FOUND` | “Errores con envelope uniforme.” |
| 8:30 | Duplicado | `POST /api/auth/register` con el mismo correo | 409 `EMAIL_TAKEN` | “Regla de correo único (RN-004).” |
| 8:50 | Sin token | `GET /api/auth/me` sin Authorization | 401 `UNAUTHORIZED` | “No hay acceso anónimo.” |
| 9:10 | Clave incorrecta | `POST /api/auth/login` con clave mala | 401 `INVALID_CREDENTIALS` | “No se filtra si el correo existe.” |
| 9:30 | Rate limit | Ejecutar `Rate limit 1/6` … `6/6` | 5×401 y luego 429 | “Cinco intentos por correo e IP.” |
| 10:15 | Privacidad | `DELETE /api/auth/account` | 204 | “Borrado en cascada.” |
| 10:35 | Login posterior | `POST /api/auth/login` | 401 | “La cuenta ya no existe.” |
| 11:00 | Cierre | Resumen | — | “13 rutas, datos reales, pruebas y documentación.” |

## Orden exacto en Postman

La colección está ordenada así:

1. `00 Health`
2. `01 Auth`
3. `02 Catalog`
4. `08 Negative/Errors`
5. `07 Privacy`

### Bloque auth

1. `01 Auth / Register` → guarda `user_id` y `run_email`
2. `01 Auth / Login` → guarda `access_token`
3. `01 Auth / Me`
4. `01 Auth / Export`

### Bloque catálogo

5. `02 Catalog / Genres`
6. `02 Catalog / Artists`
7. `02 Catalog / Search` → guarda `track_id`
8. `02 Catalog / Track detail`
9. `02 Catalog / Mark unplayable`
10. `02 Catalog / Search after unplayable`
11. `02 Catalog / Invalid query`
12. `02 Catalog / Unknown track`

### Bloque negativos

13. `08 Negative/Errors / Register duplicate`
14. `08 Negative/Errors / Me without token`
15. `08 Negative/Errors / Login wrong password`
16. `08 Negative/Errors / Rate limit 1/6` … `6/6`

### Cierre

17. `07 Privacy / Delete account`
18. `07 Privacy / Login after delete`

## Frases de apoyo

- **Auth:** “Registro con Argon2id, login con JWT HS256 y rutas protegidas por
  Bearer.”
- **Catálogo:** “El backend usa el patrón Abstract Factory; en la demo la fábrica
  concreta es la simulada, así que no gastamos cuota de YouTube.”
- **Persistencia:** “La búsqueda escribe en `artists` y `tracks`; el detalle sale
  de PostgreSQL, no de memoria.”
- **Género:** “La semilla manda; si no hay semilla, se infiere del artista; si
  no, se usa `sin_clasificar`.”
- **RN-012:** “Los videos no embebibles nunca se devuelven.”
- **Rate limit:** “Es un límite en memoria por proceso, adecuado para desarrollo
  y documentado como tal.”
- **Privacidad:** “Al borrar la cuenta, las FKs en cascada limpian sus datos.”

## Plan B

| Situación | Acción |
|---|---|
| El puerto no responde | Cambiar a `8011` y actualizar `base_url` |
| No hay canciones | `python -m app.catalog.seed_importer --all` |
| El track ya está no reproducible | Usar otro `track_id` o reejecutar semillas |
| El login devuelve 429 inesperado | Reiniciar `uvicorn` o usar otro `run_email` |
| Una request falla | Continuar con la siguiente; el guion no depende de una sola |
| Postman pierde variables | Reejecutar `Register` y `Login` |
| No hay internet | No importa: proveedor simulado |

## Cierre

Mencionar el estado real:

- 13 rutas funcionando con JWT y PostgreSQL.
- 120 pruebas automatizadas en verde.
- Catálogo persistente con proveedor simulado.
- Siguientes fases: playlists, favoritos, escucha y recomendaciones.
