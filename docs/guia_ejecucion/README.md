# Guía de ejecución · Open Music UTP

Guía paso a paso para ejecutar el proyecto **como está actualmente** en este
repositorio: frontend Vue, API FastAPI, PostgreSQL, migraciones Alembic y
pgAdmin, todo con Docker Compose.

> La interfaz actual permite **buscar canciones, ver miniaturas y metadatos, y
> reproducir un video de YouTube**. El login, las playlists y las
> recomendaciones existen en la API, pero todavía no están expuestos en la
> pantalla del frontend.
>
> Todos los comandos se ejecutan desde la **raíz del proyecto** (la carpeta que
> contiene `docker-compose.yml`).

---

## 1. Qué se va a levantar

| Servicio | Contenedor | URL / puerto local | Función |
|---|---|---|---|
| Frontend | `open-music-frontend` | <http://localhost:8956> | Vue compilado y servido por nginx |
| Backend | `open-music-backend` | <http://localhost:7845/api/docs> | API FastAPI, migraciones y seed base |
| pgAdmin | `open-music-pgadmin` | <http://localhost:8081> | Administración de PostgreSQL |
| PostgreSQL | `open-music-db` | `127.0.0.1:5433` | Base de datos |

El frontend llama a la API por la ruta relativa `/api`; nginx la reenvía al
backend dentro de la red de Docker. Por eso el navegador solo necesita abrir el
puerto `8956`.

---

## 2. Requisitos previos

### Obligatorios

- **Docker Engine** o **Docker Desktop** instalado y funcionando.
- **Docker Compose v2** (el comando es `docker compose`, no `docker-compose`).
- Conexión a internet para descargar imágenes y, si se usa YouTube, para
  cargar el reproductor.
- Espacio libre suficiente para las imágenes (PostgreSQL, Python, Node, nginx y
  pgAdmin; varios cientos de MB).

Comprueba las versiones:

```bash
docker --version
docker compose version
```

En Linux, si Docker requiere permisos de administrador, configura el grupo
`docker` o ejecuta los comandos con `sudo`. En Windows/macOS, abre Docker
Desktop y espera a que termine de iniciar.

### Para desarrollo local o pruebas (opcional)

No son necesarios para levantar todo con Docker:

- Python **3.12**.
- Node.js **22** y npm.
- `make` (para los comandos centralizados del `Makefile`).

### APIs externas

| API | ¿Se necesita clave? | Cuándo se usa |
|---|---|---|
| **YouTube Data API v3** | Sí, si `MUSIC_PROVIDER=youtube` | El **backend** busca canciones y obtiene metadatos/miniaturas |
| **YouTube IFrame Player API** | No | El **navegador** reproduce el video seleccionado |
| Proveedor simulado | No | Búsquedas de demostración sin consumir cuota |

La clave de YouTube **nunca se coloca en el frontend**: solo la usa el backend.
El navegador carga el reproductor oficial de YouTube sin clave.

---

## 3. Obtener la clave de YouTube Data API v3 (opcional)

Sigue estos pasos si quieres miniaturas reales y reproducción real. Si solo
quieres probar la interfaz sin configurar Google, salta a la sección 4 y usa
`MUSIC_PROVIDER=simulated` (las miniaturas serán de ejemplo y la reproducción
no será de videos reales).

1. Entra a <https://console.cloud.google.com/> con una cuenta de Google.
2. Crea un proyecto o selecciona uno existente.
3. Habilita **YouTube Data API v3**:
   <https://console.cloud.google.com/apis/library/youtube.googleapis.com>
4. Ve a **Credenciales** → **Crear credenciales** → **Clave de API**:
   <https://console.cloud.google.com/apis/credentials>
5. Copia la clave generada.
6. Recomendado: restringe la clave a **YouTube Data API v3**. Si aplicas
   restricciones por IP, incluye la IP pública desde donde se ejecutará el
   backend.
7. Pega la clave en el archivo `.env`:

```env
MUSIC_PROVIDER=youtube
YOUTUBE_API_KEY=TU_CLAVE_AQUI
```

### Cuota de YouTube

La cuota predeterminada es de **10.000 unidades por día** por proyecto. Una
búsqueda (`search.list`) consume aproximadamente **100 unidades**, así que
alcanza para unas 100 búsquedas nuevas al día. Si la cuota se agota, cambia a
`MUSIC_PROVIDER=simulated` para seguir probando la interfaz o usa otra clave.

Documentación oficial:
<https://developers.google.com/youtube/v3/getting-started>

---

## 4. Preparar el archivo `.env`

Docker Compose lee las variables desde `.env`, en la raíz del proyecto. El
archivo **no se sube a Git**.

Si todavía no existe:

```bash
cp .env.example .env
```

Si ya existe, no lo sobrescribas; edítalo con cuidado.

Abre `.env` y revisa como mínimo estas variables:

```env
# Proveedor: simulated | youtube
MUSIC_PROVIDER=simulated

# Solo si usas YouTube
YOUTUBE_API_KEY=

# Base de datos
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=openmusic
DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5433/openmusic

# Seguridad
JWT_SECRET=
ACCESS_TOKEN_EXPIRE_MINUTES=60
CORS_ORIGINS=http://localhost:8956,http://127.0.0.1:8956

# pgAdmin
PGADMIN_DEFAULT_EMAIL=admin@admin.com
PGADMIN_DEFAULT_PASSWORD=admin
```

### Generar `JWT_SECRET`

El backend exige un secreto de al menos 32 caracteres. Genera uno propio:

```bash
openssl rand -hex 32
```

Copia el resultado en `.env`:

```env
JWT_SECRET=el_valor_generado
```

Si no tienes `openssl`, también puedes usar Python:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Elegir el proveedor

**Opción A · Simulada (sin clave, para probar la interfaz):**

```env
MUSIC_PROVIDER=simulated
YOUTUBE_API_KEY=
SEED_CATALOG=true
```

- No consume cuota.
- `SEED_CATALOG=true` carga playlists de demostración al arrancar.
- Las miniaturas del catálogo simulado usan `example.com`, por lo que el
  frontend mostrará su placeholder local.
- Los identificadores simulados no son videos reales de YouTube; la
  reproducción no funcionará con ellos.

**Opción B · YouTube real (para miniaturas y reproducción):**

```env
MUSIC_PROVIDER=youtube
YOUTUBE_API_KEY=TU_CLAVE_AQUI
SEED_CATALOG=false
```

- El backend consulta YouTube y persiste los resultados en PostgreSQL.
- El navegador reproduce con la IFrame API.
- El video debe permitir inserción; si el dueño la desactiva, el reproductor
  mostrará un aviso.

### Notas sobre las variables

- `DATABASE_URL` del `.env` se usa para desarrollo local. **Docker Compose la
  reemplaza automáticamente** por una URL que apunta al host `db` y al puerto
  interno `5432`.
- Usa una contraseña de PostgreSQL sin caracteres problemáticos para una URL
  (`@`, `:`, `/`) o codifícala. Para evitar problemas, una cadena hexadecimal es
  una buena opción.
- `PGADMIN_DEFAULT_EMAIL` debe tener un dominio de correo válido; pgAdmin puede
  rechazar dominios reservados como `.local`.
- No cambies los volúmenes ni ejecutes `docker compose down -v` si quieres
  conservar los datos.
- `.env` debe permanecer fuera de Git. Ya está en `.gitignore`.

---

## 5. Levantar los servicios

Valida primero la configuración (no muestra secretos):

```bash
docker compose config --quiet
```

Si no hay errores, construye y levanta todo:

```bash
docker compose up -d --build
```

La primera vez puede tardar varios minutos porque descarga imágenes, instala
dependencias y compila el frontend.

Comprueba el estado:

```bash
docker compose ps
```

Debes ver `db`, `backend` y `frontend` en estado `healthy`. pgAdmin puede tardar
un poco más en quedar listo, pero su salud no bloquea a los demás servicios.

Sigue el arranque del backend:

```bash
docker compose logs -f backend
```

En el primer arranque el backend:

1. Detecta si la base ya tiene tablas pero no `alembic_version` (volumen creado
   con `dataBase/schema.sql`) y ejecuta `alembic stamp head`.
2. Aplica las migraciones pendientes con `alembic upgrade head`.
3. Asegura los géneros y artistas base.
4. Si `SEED_CATALOG=true` y el proveedor es simulado, importa las playlists de
   demostración.
5. Inicia Uvicorn en el puerto interno `8000`.

---

## 6. Abrir la aplicación

| Qué | URL |
|---|---|
| Frontend | <http://localhost:8956> |
| Swagger / API docs | <http://localhost:7845/api/docs> |
| OpenAPI JSON | <http://localhost:7845/api/openapi.json> |
| Salud del backend | <http://localhost:7845/api/health> |
| Salud con base de datos | <http://localhost:7845/api/health/ready> |
| Salud a través de nginx | <http://localhost:8956/api/health/ready> |
| pgAdmin | <http://localhost:8081> |

### Conectar pgAdmin a PostgreSQL

1. Abre <http://localhost:8081>.
2. Inicia sesión con `PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD` del
   `.env`.
3. Crea un servidor nuevo con estos datos:

| Campo | Valor |
|---|---|
| Name | `Open Music UTP` |
| Host | `db` |
| Port | `5432` |
| Maintenance database | `openmusic` (o el valor de `POSTGRES_DB`) |
| Username | `postgres` (o `POSTGRES_USER`) |
| Password | La de `POSTGRES_PASSWORD` |

> Desde pgAdmin el host es `db` y el puerto es `5432`, porque pgAdmin está
> dentro de la red de Docker. El puerto `5433` es solo para conectarte desde tu
> equipo con `psql` u otro cliente.

### Conectar desde tu equipo con `psql`

```bash
psql -h 127.0.0.1 -p 5433 -U postgres -d openmusic
```

---

## 7. Probar la búsqueda y la reproducción

1. Abre <http://localhost:8956>.
2. Escribe una búsqueda, por ejemplo `rock`, `salsa` o `The Beatles`.
3. Pulsa **Buscar**.
4. Deberías ver tarjetas con miniatura, título, artista, género y duración.
5. Haz clic en una tarjeta para cargar el video en el reproductor.

Comprobaciones rápidas por consola:

```bash
# El backend está vivo
curl http://localhost:7845/api/health

# El backend puede hablar con PostgreSQL
curl http://localhost:7845/api/health/ready

# nginx reenvía /api correctamente
curl http://localhost:8956/api/health/ready

# Búsqueda directa en la API
curl "http://localhost:7845/api/catalog/search?q=rock&limit=5"
```

La búsqueda también se puede probar desde Swagger:
<http://localhost:7845/api/docs> → `GET /api/catalog/search`.

### Si usas `MUSIC_PROVIDER=simulated`

La pantalla funciona, pero las miniaturas serán de `example.com` y el
reproductor no encontrará un video real. Para ver imágenes y reproducción
reales, configura `MUSIC_PROVIDER=youtube` y `YOUTUBE_API_KEY`, y vuelve a
levantar el backend:

```bash
docker compose up -d --build backend
```

### Errores del reproductor

| Código de YouTube | Significado |
|---|---|
| `2` | Identificador de video inválido |
| `5` | El navegador no puede reproducir el video |
| `100` | El video no existe o es privado |
| `101` / `150` | El dueño no permite reproducirlo fuera de YouTube |

El backend filtra los videos no embebibles, pero algunos pueden fallar después.
En ese caso la interfaz muestra el aviso y conserva la búsqueda.

---

## 8. Comandos de operación

### Ver logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
docker compose logs -f pgadmin
```

### Reiniciar un servicio

```bash
docker compose restart backend
docker compose restart frontend
```

Si cambiaste variables de `.env`, recrea el contenedor:

```bash
docker compose up -d backend
```

### Detener sin borrar datos

```bash
docker compose stop
```

Para volver a arrancar:

```bash
docker compose start
```

### Bajar los contenedores conservando volúmenes

```bash
docker compose down
```

Los datos de PostgreSQL y pgAdmin se conservan.

### Borrar TODO, incluidos los datos

> **Advertencia:** esto elimina la base de datos y la configuración de pgAdmin.
> No lo uses si quieres conservar los datos existentes.

```bash
docker compose down -v
```

### Actualizar el proyecto

Después de traer cambios nuevos:

```bash
git pull
docker compose up -d --build
```

Las migraciones se aplican automáticamente al arrancar el backend.

---

## 9. Persistencia y migraciones

Los volúmenes con nombre fijo son:

- `open-music-postgres-data`: datos de PostgreSQL.
- `open-music-pgadmin-data`: sesiones, servidores y preferencias de pgAdmin.

No se borran con `docker compose down`; solo con `docker compose down -v` o
`docker volume rm`.

El backend aplica las migraciones al arrancar. Si el volumen ya existía con el
esquema antiguo de `dataBase/schema.sql`, detecta que hay tablas pero no
`alembic_version`, marca esa revisión como base y continúa. Por eso **no hace
falta borrar el volumen** para actualizar el esquema.

---

## 10. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `env file ... .env not found` | No existe `.env` | `cp .env.example .env` y edita las claves |
| `Define POSTGRES_PASSWORD en el archivo .env` | Falta una variable obligatoria | Complétala en `.env` y repite `docker compose up -d --build` |
| `JWT_SECRET (mínimo 32 caracteres)` | El secreto está vacío o es corto | Genera uno con `openssl rand -hex 32` y actualízalo |
| `port is already allocated` | Otro programa usa `5433`, `7845`, `8956` u `8081` | Libera el puerto o cambia el número de la izquierda en `docker-compose.yml` |
| `backend` queda en `starting` | Migraciones o base aún inicializando | `docker compose logs -f backend` y espera |
| `backend` queda en `unhealthy` | Falla la conexión a la base o falta una variable | Revisa logs y `DATABASE_URL`, `JWT_SECRET` y credenciales |
| El frontend abre pero la búsqueda da 502 | El backend no está saludable o nginx no lo encuentra | `docker compose ps` y `docker compose logs backend frontend` |
| La búsqueda responde vacía | Consulta sin coincidencias o cuota/key de YouTube | Prueba `rock`; revisa logs y la clave si usas YouTube |
| Las miniaturas no cargan | Proveedor simulado (`example.com`) o URL inválida | Usa `MUSIC_PROVIDER=youtube` con una clave válida |
| El video no reproduce | Video privado, no embebible o error de red | Prueba otra canción; revisa el aviso del reproductor |
| pgAdmin no conecta | Se usó `localhost` o `5433` | Host `db`, puerto `5432`, credenciales del `.env` |
| Cambié una contraseña y no entra | PostgreSQL solo aplica la clave al crear el volumen | Cambia la clave dentro de PostgreSQL o recrea el volumen (pierdes datos) |

Para una revisión completa del estado:

```bash
docker compose ps
docker compose logs --tail=100 backend
docker compose logs --tail=100 frontend
```

---

## 11. Desarrollo local (opcional)

Si quieres modificar el código sin reconstruir las imágenes, puedes levantar la
base con Docker y ejecutar backend y frontend en tu equipo.

### Backend

```bash
# Base de datos en Docker
docker compose up -d db

cd backend
python3.12 -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

alembic upgrade head
python -m app.catalog.seed_importer --base-only
python -m app.catalog.seed_importer --all     # opcional, solo simulado

uvicorn app.main:app --reload --port 7845
```

La API queda en <http://localhost:7845/api/docs>.

### Frontend

En otra terminal, desde la raíz:

```bash
cd frontend
npm ci
npm run dev
```

Vite queda en <http://127.0.0.1:5173> y redirige `/api` al backend en `7845`.

### Pruebas y lint

```bash
make test-frontend
make lint
```

Para el backend, `make test-backend` necesita una base de pruebas separada. No
uses la base de desarrollo. Ejemplo:

```bash
TEST_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:5433/openmusic_test \
  make test-backend
```

La base `openmusic_test` debe existir y ser distinta de `openmusic`.

---

## 12. Checklist rápido

- [ ] Docker y Docker Compose funcionando.
- [ ] `.env` creado y con `JWT_SECRET`.
- [ ] `MUSIC_PROVIDER` elegido (`simulated` o `youtube`).
- [ ] `YOUTUBE_API_KEY` configurada si se usa YouTube.
- [ ] `docker compose config --quiet` sin errores.
- [ ] `docker compose up -d --build` ejecutado.
- [ ] `docker compose ps` muestra `db`, `backend` y `frontend` saludables.
- [ ] <http://localhost:8956> abre y permite buscar.
- [ ] <http://localhost:7845/api/docs> responde.
- [ ] <http://localhost:8081> abre pgAdmin.
- [ ] La búsqueda devuelve tarjetas con miniatura y metadatos.
- [ ] Al hacer clic en una canción se carga el reproductor (con YouTube real).
- [ ] No se ejecutó `docker compose down -v` sobre datos que se quieren conservar.

---

## 13. Enlaces útiles

- Frontend: <http://localhost:8956>
- Swagger: <http://localhost:7845/api/docs>
- OpenAPI: <http://localhost:7845/api/openapi.json>
- pgAdmin: <http://localhost:8081>
- Documentación de Docker del proyecto: [`docs/docker-compose.md`](../docker-compose.md)
- Colección Postman: [`backend/postman/README.md`](../../backend/postman/README.md)
- Guías de Postman: [`docs/postman_docs/README.md`](../postman_docs/README.md)
- YouTube Data API v3: <https://developers.google.com/youtube/v3/getting-started>
- Consola de Google Cloud: <https://console.cloud.google.com/>
