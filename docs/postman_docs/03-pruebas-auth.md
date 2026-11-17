# 03 · Pruebas de autenticación

Carpetas de Postman: `01 Auth`, `07 Privacy` y `08 Negative/Errors`.

## 1. Registro

```http
POST {{base_url}}/api/auth/register
Content-Type: application/json

{
  "email": "{{run_email}}",
  "password": "{{run_password}}",
  "accept_privacy": true
}
```

Pre-request:

```js
pm.collectionVariables.set("run_email", `demo+${Date.now()}@utp.edu.co`);
pm.collectionVariables.set("run_password", "Clave-segura-123");
```

Pruebas:

```js
const body = pm.response.json();
pm.test("201", () => pm.response.to.have.status(201));
pm.test("correo normalizado", () => pm.expect(body.email).to.eql(body.email.toLowerCase()));
pm.test("UUID", () => pm.expect(body.id).to.match(/^[0-9a-f-]{36}$/i));
pm.test("sin datos sensibles", () => {
  pm.expect(body).to.not.have.property("password");
  pm.expect(body).to.not.have.property("password_hash");
});
pm.collectionVariables.set("user_id", body.id);
```

## 2. Login

```http
POST {{base_url}}/api/auth/login
Content-Type: application/json

{
  "email": "{{run_email}}",
  "password": "{{run_password}}"
}
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("bearer", () => pm.expect(body.token_type).to.eql("bearer"));
pm.test("expira en una hora", () => pm.expect(body.expires_in).to.eql(3600));
pm.collectionVariables.set("access_token", body.access_token);

const part = body.access_token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
const payload = JSON.parse(atob(part));
pm.test("JWT con sub, iat y exp", () => {
  pm.expect(payload.sub).to.be.a("string");
  pm.expect(payload.exp - payload.iat).to.eql(3600);
});
```

## 3. Perfil

```http
GET {{base_url}}/api/auth/me
Authorization: Bearer {{access_token}}
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("mismo usuario", () =>
  pm.expect(body.id).to.eql(pm.collectionVariables.get("user_id"))
);
pm.test("sin password_hash", () => pm.expect(body).to.not.have.property("password_hash"));
```

## 4. Logout

```http
POST {{base_url}}/api/auth/logout
Authorization: Bearer {{access_token}}
```

Pruebas:

```js
pm.test("204", () => pm.response.to.have.status(204));
pm.test("sin cuerpo", () => pm.expect(pm.response.text()).to.eql(""));
```

> El JWT es sin estado (decisión D-02). Después del logout el token sigue
> funcionando hasta que expire; es el comportamiento esperado.

## 5. Exportación

```http
GET {{base_url}}/api/auth/export
Authorization: Bearer {{access_token}}
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("claves de privacidad", () => {
  pm.expect(body).to.have.property("user");
  pm.expect(body).to.have.property("playlists");
  pm.expect(body).to.have.property("favorites");
  pm.expect(body).to.have.property("listening_events");
  pm.expect(body).to.have.property("preferences");
});
pm.test("colecciones vacías en Fase 1", () => {
  pm.expect(body.playlists).to.eql([]);
  pm.expect(body.favorites).to.eql([]);
  pm.expect(body.listening_events).to.eql([]);
});
```

En Fase 5 estas colecciones se llenarán con los datos de los demás módulos.

## 6. Eliminación de cuenta

```http
DELETE {{base_url}}/api/auth/account
Authorization: Bearer {{access_token}}
```

Pruebas:

```js
pm.test("204", () => pm.response.to.have.status(204));
pm.test("sin cuerpo", () => pm.expect(pm.response.text()).to.eql(""));
```

Después de eliminar:

- `POST /api/auth/login` con las mismas credenciales → `401`.
- `GET /api/auth/me` con el token anterior → `401`.

## 7. Casos negativos de auth

| Request | Esperado |
|---|---|
| Registro con el mismo correo | `409 EMAIL_TAKEN` |
| Registro con `accept_privacy=false` | `422 VALIDATION_ERROR` |
| Registro con contraseña de menos de 8 caracteres | `422 VALIDATION_ERROR` |
| Login con contraseña incorrecta | `401 INVALID_CREDENTIALS` |
| `GET /me` sin token | `401 UNAUTHORIZED` |
| `GET /me` con token inválido | `401 UNAUTHORIZED` |
| `GET /api/auth/login` (método incorrecto) | `405 METHOD_NOT_ALLOWED` |
| Ruta inexistente | `404 NOT_FOUND` |
| Sexto login fallido | `429 RATE_LIMITED` + `Retry-After` |

## 8. Variables que deben quedar al terminar

- `run_email`
- `user_id`
- `access_token`

Si `access_token` queda vacío, revisa que `Login` se ejecutó antes que `Me` y
que el test de login guardó la variable.
