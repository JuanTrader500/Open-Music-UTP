# 06 · Negativos y rate limit

## 1. Matriz de errores

| Caso | Request | HTTP | `code` |
|---|---|---|---|
| Registro duplicado | `POST /api/auth/register` con `run_email` existente | 409 | `EMAIL_TAKEN` |
| Privacidad no aceptada | `POST /api/auth/register` con `accept_privacy=false` | 422 | `VALIDATION_ERROR` |
| Contraseña corta | `POST /api/auth/register` con 7 caracteres | 422 | `VALIDATION_ERROR` |
| Correo inválido | `POST /api/auth/register` con `sin-arroba` | 422 | `VALIDATION_ERROR` |
| Login incorrecto | `POST /api/auth/login` con clave mala | 401 | `INVALID_CREDENTIALS` |
| Sin token | `GET /api/auth/me` sin Authorization | 401 | `UNAUTHORIZED` |
| Token inválido | `GET /api/auth/me` con `Bearer abc` | 401 | `UNAUTHORIZED` |
| Método incorrecto | `GET /api/auth/login` | 405 | `METHOD_NOT_ALLOWED` |
| Ruta inexistente | `GET /api/no-existe` | 404 | `NOT_FOUND` |
| Query corta | `GET /api/catalog/search?q=a` | 422 | `INVALID_QUERY` |
| Límite excesivo | `GET /api/catalog/search?q=rock&limit=999` | 422 | `VALIDATION_ERROR` |
| Track inexistente | `GET /api/catalog/tracks/no-existe` | 404 | `TRACK_NOT_FOUND` |
| `genre_ids` inválido | `GET /api/catalog/artists?genre_ids=1,abc` | 422 | `VALIDATION_ERROR` |
| Rate limit | Sexto login fallido del mismo correo | 429 | `RATE_LIMITED` |

## 2. Envelope de error

Todos los errores deben tener exactamente:

```json
{
  "code": "CODIGO",
  "message": "Mensaje en español"
}
```

Prueba de Postman:

```js
pm.test("envelope de error", () => {
  const body = pm.response.json();
  pm.expect(body).to.have.all.keys("code", "message");
  pm.expect(body.code).to.be.a("string");
  pm.expect(body.message).to.be.a("string");
});
```

## 3. Rate limit

### Configuración

- Límite: `LOGIN_ATTEMPTS_PER_MINUTE` (5 por defecto).
- Clave: correo normalizado + IP del cliente.
- Ventana: 60 segundos.
- Estado: memoria del proceso.

### Procedimiento en Postman

La colección incluye seis requests:

1. `Rate limit 1/6`
2. `Rate limit 2/6`
3. `Rate limit 3/6`
4. `Rate limit 4/6`
5. `Rate limit 5/6`
6. `Rate limit 6/6`

El pre-request del primero genera un correo aislado:

```js
pm.collectionVariables.set("rate_email", `rate+${Date.now()}@utp.edu.co`);
```

Los cinco primeros deben devolver `401 INVALID_CREDENTIALS`. El sexto:

```js
pm.test("429", () => pm.response.to.have.status(429));
pm.test("código", () => pm.expect(pm.response.json().code).to.eql("RATE_LIMITED"));
pm.test("Retry-After", () => {
  const retry = pm.response.headers.get("Retry-After");
  pm.expect(retry).to.exist;
  pm.expect(Number(retry)).to.be.above(0);
});
```

### Limpiar el estado

El rate limiter se reinicia al reiniciar `uvicorn`. También puedes usar un
correo distinto para cada demostración.

## 4. Pruebas de cabeceras

```js
pm.test("cabeceras de seguridad", () => {
  pm.expect(pm.response.headers.get("X-Content-Type-Options")).to.eql("nosniff");
  pm.expect(pm.response.headers.get("X-Frame-Options")).to.eql("DENY");
  pm.expect(pm.response.headers.get("Referrer-Policy")).to.eql("no-referrer");
  pm.expect(pm.response.headers.get("Cache-Control")).to.eql("no-store");
});

pm.test("request id", () => {
  pm.expect(pm.response.headers.get("X-Request-ID")).to.match(/^[A-Za-z0-9-]{8,64}$/);
});
```

## 5. Qué NO debe aparecer

La colección verifica en cada respuesta:

```js
pm.test("sin password_hash", () => {
  pm.expect(pm.response.text()).to.not.include("password_hash");
});
```

Si aparece `password_hash`, hay una fuga de datos y la prueba debe fallar.
