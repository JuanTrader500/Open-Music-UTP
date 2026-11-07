# 02 · Importar la colección y el environment

## 1. Archivos

```text
backend/postman/
├── OpenMusicUTP.postman_collection.json
├── local.postman_environment.json
└── README.md
```

## 2. Importar en Postman

1. Abrir Postman.
2. `Import` → `File` → seleccionar
   `backend/postman/OpenMusicUTP.postman_collection.json`.
3. Repetir con
   `backend/postman/local.postman_environment.json`.
4. En la esquina superior derecha, seleccionar el environment
   **Open Music UTP - Local**.

## 3. Variables

### Environment

| Variable | Valor inicial | Uso |
|---|---|---|
| `base_url` | `http://localhost:8010` | URL del backend |
| `run_password` | `Clave-segura-123` | Contraseña de la demo |

### Colección

| Variable | Se llena en | Uso |
|---|---|---|
| `run_email` | Pre-request de `Register` | Correo único por ejecución |
| `user_id` | Test de `Register` | Identificador del usuario |
| `access_token` | Test de `Login` | Cabecera Bearer |
| `track_id` | Test de `Search` | Detalle y C-03 |
| `rate_email` | Pre-request de `Rate limit 1/6` | Correo aislado para el 429 |

## 4. Orden de ejecución

La colección está pensada para ejecutarse de arriba abajo:

1. `00 Health`
2. `01 Auth`
3. `02 Catalog`
4. `08 Negative/Errors`
5. `07 Privacy`

Las pruebas destructivas están al final. `Delete account` elimina el usuario de
la demo; después de eso, cualquier request autenticada con ese token devolverá
`401`.

## 5. Ejecución manual

1. Abrir cada request.
2. Verificar la pestaña `Tests` y los scripts de pre-request.
3. Enviar.
4. Revisar `Test Results` en la parte inferior.

## 6. Ejecución con el Collection Runner

1. Clic derecho sobre la colección → `Run collection`.
2. Mantener el orden de carpetas.
3. Activar `Save responses` solo si se necesitan evidencias.
4. Ejecutar.

> El rate limit y el borrado de cuenta dependen del estado. Si repites la
> ejecución, reinicia `uvicorn` para limpiar el rate limiter y vuelve a correr
> las semillas para restaurar el catálogo.

## 7. Ejecución con Newman

```bash
cd backend
npx newman run postman/OpenMusicUTP.postman_collection.json \
  -e postman/local.postman_environment.json
```

Si Newman no está instalado:

```bash
npm install -g newman
```

## 8. Pruebas automáticas incluidas

La colección valida:

- Códigos HTTP esperados.
- `Content-Type` JSON.
- Cabeceras de seguridad.
- Presencia de `X-Request-ID`.
- Ausencia de `password_hash`.
- Estructura de las respuestas de auth y catálogo.
- Envelope `{code, message}` en errores.
- Encadenamiento de token, usuario y track.
- Rate limit con `Retry-After`.
