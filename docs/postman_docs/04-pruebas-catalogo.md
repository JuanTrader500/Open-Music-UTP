# 04 · Pruebas de catálogo

Carpeta de Postman: `02 Catalog`.

Antes de ejecutar, confirma que las semillas están cargadas:

```bash
cd backend
python -m app.catalog.seed_importer --all
```

## 1. Géneros

```http
GET {{base_url}}/api/catalog/genres
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("lista de géneros", () => {
  pm.expect(body).to.be.an("array");
  pm.expect(body.length).to.be.above(40);
});
pm.test("incluye sin clasificar", () => {
  pm.expect(body.some((genre) => genre.code === "sin_clasificar")).to.eql(true);
});
```

## 2. Artistas

```http
GET {{base_url}}/api/catalog/artists?limit=50
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("paginación", () => {
  pm.expect(body).to.have.property("items");
  pm.expect(body).to.have.property("total");
  pm.expect(body).to.have.property("limit");
  pm.expect(body).to.have.property("offset");
});
```

Filtros:

```http
GET {{base_url}}/api/catalog/artists?genre_ids=1&limit=50
GET {{base_url}}/api/catalog/artists?q=valentina
```

## 3. Búsqueda

```http
GET {{base_url}}/api/catalog/search?q=cafeteros&limit=10
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("resultados", () => {
  pm.expect(body).to.have.property("items");
  pm.expect(body).to.have.property("total");
  pm.expect(body.query).to.eql("cafeteros");
  pm.expect(body.items.length).to.be.above(0);
});
pm.test("solo embebibles", () => {
  body.items.forEach((track) => pm.expect(track.is_embeddable).to.eql(true));
});
pm.test("artista y género", () => {
  const track = body.items[0];
  pm.expect(track.artist).to.have.property("name");
  pm.expect(track.genre).to.have.property("code");
});
pm.collectionVariables.set("track_id", body.items[0].track_id);
```

La búsqueda no solo responde: **persiste artistas y canciones** en PostgreSQL.
Por eso el detalle funciona inmediatamente después.

Consulta alternativa para la demo:

```http
GET {{base_url}}/api/catalog/search?q=rock&limit=10
GET {{base_url}}/api/catalog/search?q=de&limit=10
```

## 4. Detalle de canción

```http
GET {{base_url}}/api/catalog/tracks/{{track_id}}
```

Pruebas:

```js
const body = pm.response.json();
pm.test("200", () => pm.response.to.have.status(200));
pm.test("mismo track", () =>
  pm.expect(body.track_id).to.eql(pm.collectionVariables.get("track_id"))
);
pm.test("tiene duración y thumbnail", () => {
  pm.expect(body.duration_s).to.be.a("number");
  pm.expect(body.thumbnail_url).to.be.a("string");
});
```

## 5. Marcar como no reproducible

```http
POST {{base_url}}/api/catalog/tracks/{{track_id}}/unplayable
```

Pruebas:

```js
pm.test("204", () => pm.response.to.have.status(204));
pm.test("sin cuerpo", () => pm.expect(pm.response.text()).to.eql(""));
```

Después de marcarla:

1. Repetir `GET /api/catalog/search?q=cafeteros&limit=10`.
2. La canción marcada ya no debe aparecer.
3. `GET /api/catalog/tracks/{{track_id}}` debe devolver `is_embeddable=false`.

Para restaurar el catálogo antes de otra demo:

```bash
python -m app.catalog.seed_importer --all
```

## 6. Casos negativos de catálogo

| Request | Esperado |
|---|---|
| `GET /api/catalog/search?q=a` | `422 INVALID_QUERY` |
| `GET /api/catalog/search?q=rock&limit=999` | `422 VALIDATION_ERROR` |
| `GET /api/catalog/tracks/no-existe` | `404 TRACK_NOT_FOUND` |
| `GET /api/catalog/artists?genre_ids=1,abc` | `422 VALIDATION_ERROR` |
| `POST /api/catalog/tracks/no-existe/unplayable` | `404 TRACK_NOT_FOUND` |

## 7. Qué demuestra cada request

| Request | Regla |
|---|---|
| `GET /genres` | Lista cerrada de géneros (RF-011) |
| `GET /artists` | Artistas y filtro por género (RF-021) |
| `GET /search` | Búsqueda, persistencia y solo embebibles (RF-010, RN-012) |
| `GET /tracks/{id}` | Detalle persistido (RF-010) |
| `POST /unplayable` | Exclusión de no reproducibles (RF-009, RN-012) |
| `q=a` | Validación de longitud mínima (RF-010) |
| `no-existe` | Manejo de recurso inexistente |

## 8. Variables que deben quedar

- `track_id`

Si `track_id` queda vacío, revisa que la búsqueda devolvió al menos un
resultado y que el test guardó la variable.
