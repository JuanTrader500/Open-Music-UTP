# Docker Compose de Open Music UTP: explicación y cheat sheet

Servicios actuales: **PostgreSQL 16** (`db`) y **pgAdmin 4** (`pgadmin`). Cuando agregues el backend y el frontend, se suman al mismo archivo.

---

## 1. Qué levanta

| Servicio | Imagen | Contenedor | Puerto en tu equipo | Para qué sirve |
|---|---|---|---|---|
| `db` | `postgres:16-alpine` | `open-music-db` | `127.0.0.1:5433` | Base de datos del proyecto |
| `pgadmin` | `dpage/pgadmin4` | `open-music-pgadmin` | `http://localhost:8081` | Administrar la base desde el navegador |

El puerto interno de PostgreSQL es 5432. El 5433 solo existe en tu equipo para que no choque con un PostgreSQL local.

## 2. Dónde va cada archivo

```
open-music-utp/
├── .env                 ← tus claves reales 
├── .env.example         ← plantilla sin claves 
├── docker-compose.yml   ← este archivo
├── dataBase/
│   └── schema.sql       ← se carga la primera vez que se crea la base de datos 
├── backend/
├── frontend/
└── docs/
```


## 3. Cómo funciona la persistencia

### Dónde viven los datos

| Qué | Volumen | Ruta en el contenedor |
|---|---|---|
| Datos de PostgreSQL | `open-music-postgres-data` | `/var/lib/postgresql/data` |
| Sesiones, servidores guardados y configuración de pgAdmin | `open-music-pgadmin-data` | `/var/lib/pgadmin` |

Son **volúmenes con nombre**: los administra Docker y viven fuera de los contenedores.

### Qué los conserva y qué los borra

| Acción | ¿Se conservan los datos? |
|---|---|
| `docker compose stop` / `start` / `restart` | Sí |
| `docker compose down` | Sí |
| Reiniciar el equipo o Docker | Sí |
| `docker compose pull` + `up -d` (actualizar la imagen) | Sí |
| Borrar y recrear el contenedor | Sí |
| `docker compose down -v` | **No: borra los volúmenes** |
| `docker volume rm ...` | **No** |
| `docker volume prune` | **Cuidado: con los contenedores eliminados (`down`) los volúmenes quedan «sin uso» y se pueden borrar** |

### El `schema.sql` se ejecuta una sola vez

PostgreSQL ejecuta los scripts de `/docker-entrypoint-initdb.d/` **solo si el volumen de datos está vacío**. Esto tiene consecuencias:

- Si modificas `schema.sql` después, **no se vuelve a aplicar** al reiniciar. Para probar el schema desde cero: `docker compose down -v && docker compose up -d` (borra todos los datos).
- Para cambiar una base que ya tiene datos, aplica un script de migración con `psql` (ver el cheat sheet).
- Si el `schema.sql` tiene un error en el primer arranque, la base queda vacía y los siguientes arranques ya no vuelven a ejecutarlo. Revisa `docker compose logs db`, corrige el archivo y repite con `docker compose down -v && docker compose up -d`.

### Qué guarda pgAdmin

La documentación oficial indica que `/var/lib/pgadmin` guarda los datos de sesión y los archivos de configuración; los servidores guardados y las preferencias también viven ahí. Con el volumen, un `down` y un `up` no te obligan a registrar de nuevo la base. La sesión del navegador sigue caducando según la configuración de pgAdmin; cuando eso pase, solo tendrás que iniciar sesión otra vez y tus servidores seguirán guardados.

pgAdmin se ejecuta con el usuario 5050 dentro del contenedor. Con un volumen con nombre, los permisos se ajustan solos. Si algún día cambias a una carpeta de tu equipo (*bind mount*), necesitarás `sudo chown -R 5050:5050 <carpeta>`.

---

## 4. Conectar pgAdmin a la base (primera vez)

1. Abre http://localhost:8081 e inicia sesión con `PGADMIN_DEFAULT_EMAIL` y `PGADMIN_DEFAULT_PASSWORD`.
2. Clic derecho en **Servers**, luego **Register → Server**.
3. Pestaña **General**: Name = `Open Music`.
4. Pestaña **Connection**:

| Campo | Valor |
|---|---|
| Host name/address | **`db`** |
| Port | **`5432`** |
| Maintenance database | el valor de `POSTGRES_DB` |
| Username | el valor de `POSTGRES_USER` |
| Password | el valor de `POSTGRES_PASSWORD` |

5. Marca **Save password** si quieres que lo recuerde.

**Error común:** dentro de la red de Docker el host es `db` y el puerto es `5432`. El `5433` es solo para conectarte desde tu equipo (con `psql`, DBeaver, etc.), no desde pgAdmin.

### Opcional: que el servidor aparezca registrado solo

pgAdmin permite precargar servidores con un archivo `servers.json`. Crea `pgadmin/servers.json`:

```json
{
  "Servers": {
    "1": {
      "Name": "Open Music",
      "Group": "Servers",
      "Host": "db",
      "Port": 5432,
      "MaintenanceDB": "openmusic",
      "Username": "openmusic",
      "SSLMode": "prefer"
    }
  }
}
```

y agrégalo a los volúmenes de `pgadmin`:

```yaml
      - ./pgadmin/servers.json:/pgadmin4/servers.json:ro
```

Se importa en el primer arranque, con el volumen de pgAdmin vacío. La contraseña no va en el archivo: pgAdmin te la pedirá la primera vez.

---

## 8. Primer arranque, paso a paso

```bash
cd /home/juan500/Documents/Universidad/patronesDiseño/open-music-utp
cp .env.example .env              # y edita las claves
docker compose config             # valida el archivo y muestra las variables ya resueltas
docker compose up -d              # levanta todo en segundo plano
docker compose ps                 # esperas ver "healthy" en db
docker compose logs db | grep -i "01-schema"   # confirma que se ejecutó el schema
```

Después abre http://localhost:8081.

---

## 9. Cheat sheet de comandos

Todos se ejecutan desde la carpeta del proyecto (donde está el `docker-compose.yml`).

### Ciclo de vida

```bash
docker compose up -d                 # crear y arrancar en segundo plano
docker compose up -d db              # arrancar solo la base de datos
docker compose stop                  # detener (conserva contenedores y datos)
docker compose start                 # volver a arrancar lo detenido
docker compose restart db            # reiniciar un servicio
docker compose down                  # detener y eliminar contenedores y red (conserva los volúmenes)
docker compose down -v               # ¡BORRA también los volúmenes y todos los datos!
docker compose config                # validar el archivo y ver las variables resueltas
```

### Estado y logs

```bash
docker compose ps                                   # estado y salud de cada servicio
docker compose logs -f db                           # seguir los logs de la base
docker compose logs --tail 100 pgadmin              # últimas 100 líneas de pgAdmin
docker inspect --format '{{.State.Health.Status}}' open-music-db   # healthy / unhealthy / starting
docker compose top                                  # procesos de cada contenedor
docker stats                                        # CPU y memoria en vivo
```

### Entrar a la base de datos con `psql`

Los comandos leen el usuario y la base desde las variables del contenedor, así que no tienes que escribirlos:

```bash
# consola interactiva
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"'

# una consulta suelta
docker compose exec db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT count(*) FROM artists;"'

# ejecutar un archivo SQL (por ejemplo, una migración)
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < dataBase/migracion.sql

# desde tu equipo, con psql instalado
psql -h 127.0.0.1 -p 5433 -U openmusic -d openmusic
```

Dentro de `psql`:

```text
\dt              listar tablas
\d tracks        describir una tabla
\di              listar índices
\l               listar bases de datos
\x               alternar vista expandida
\q               salir
```

### Copias de seguridad y restauración

```bash
# copia en SQL (texto plano)
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' > backup_$(date +%F).sql

# copia en formato comprimido (permite restaurar tablas sueltas)
docker compose exec -T db sh -c 'pg_dump -Fc -U "$POSTGRES_USER" -d "$POSTGRES_DB"' > backup_$(date +%F).dump

# restaurar un .sql en una base vacía
docker compose exec -T db sh -c 'psql -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup_2026-10-16.sql

# restaurar un .dump (reemplaza lo existente)
docker compose exec -T db sh -c 'pg_restore --clean --if-exists -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < backup_2026-10-16.dump
```

Guarda las copias fuera de la carpeta del repositorio, o agrega `*.sql` y `*.dump` de respaldo a `.gitignore`.

### Volúmenes

```bash
docker volume ls                                       # listar volúmenes
docker volume inspect open-music-postgres-data         # ruta, fecha de creación, etc.
docker system df -v                                    # tamaño de cada volumen

# copia de seguridad del volumen completo (detén la base antes)
docker compose stop db
docker run --rm -v open-music-postgres-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/postgres_data_$(date +%F).tar.gz -C /data .
docker compose start db
```

### Reiniciar desde cero

```bash
# todo: base de datos y pgAdmin
docker compose down -v && docker compose up -d

# solo la base (conserva lo guardado en pgAdmin)
docker compose stop db
docker compose rm -f db
docker volume rm open-music-postgres-data
docker compose up -d db
```

### Actualizar imágenes

```bash
docker compose pull                  # descarga imágenes nuevas
docker compose up -d                 # recrea los contenedores con las nuevas (los datos se conservan)
docker image prune                   # elimina imágenes viejas sin uso
```

Las actualizaciones menores de PostgreSQL 16 son seguras. Para pasar a otra versión mayor (por ejemplo la 17) hay que sacar una copia con `pg_dump` y restaurarla en una base nueva.

### Depuración

```bash
docker compose exec db sh                      # shell dentro del contenedor de la base
docker compose exec pgadmin sh                 # shell dentro de pgAdmin
ss -tulpn | grep -E '5433|8081'                # ¿hay otro programa usando esos puertos?
docker compose logs db | grep -iE "error|fatal"   # errores de la base
```

---

## 10. Solución de problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| `Define POSTGRES_PASSWORD en el archivo .env` | Falta una variable | Complétala en `.env` y repite el comando |
| `port is already allocated` | El 5433 o el 8081 están ocupados | Cambia el número de la izquierda en `ports` (por ejemplo `127.0.0.1:5434:5432`) |
| La base arranca pero no tiene tablas | El volumen ya tenía datos, o el `schema.sql` falló la primera vez | `docker compose logs db`, corrige y ejecuta `docker compose down -v && docker compose up -d` |
| `db` se queda en `starting` o pasa a `unhealthy` | El `schema.sql` tarda o falló | Revisa `docker compose logs db` |
| pgAdmin no se conecta a la base | Usaste `localhost` o `5433` | Host `db`, puerto `5432` |
| pgAdmin rechaza el correo al iniciar | Dominio reservado (por ejemplo `.local`) | Usa un correo con dominio válido en `PGADMIN_DEFAULT_EMAIL` y recrea el volumen de pgAdmin si ya se inicializó |
| Cambié la clave de pgAdmin en `.env` y sigue la anterior | La clave inicial solo se usa al crear el volumen | Cámbiala desde la interfaz de pgAdmin, o borra `open-music-pgadmin-data` (pierdes los servidores guardados) |
| Cambié `POSTGRES_PASSWORD` y no entra | La clave solo se aplica al crear el volumen | `ALTER USER ... PASSWORD '...'` desde `psql`, o recrea el volumen |
| Los datos «desaparecieron» al mover la carpeta | Antes el volumen se nombraba según la carpeta | Con los nombres fijos de este archivo ya no pasa |
| `permission denied` en `/var/lib/pgadmin` | Usas una carpeta de tu equipo en lugar del volumen | `sudo chown -R 5050:5050 <carpeta>` |

---

## 11. Buenas prácticas

1. **Nunca subas `.env` a git.** Sube solo `.env.example`.
2. **Cambia las claves de ejemplo** antes de compartir el entorno con el equipo.
3. **Mantén `127.0.0.1` en los puertos** mientras trabajes en local. Si el equipo necesita acceder a la base por la red, usa una VPN o un túnel SSH en lugar de abrirla a toda la red.
4. **Haz una copia con `pg_dump`** antes de cualquier migración o de un `down -v`.
5. **Fija la versión de pgAdmin** (`PGADMIN_TAG`) cuando el proyecto esté estable, para que todos usen la misma.
6. **Usa `docker compose down` y no `down -v`** salvo que quieras empezar de cero.

## 12. Cuando agregues el backend y el frontend

Se agregan como servicios nuevos en el mismo archivo, conectados a `open-music-net`. Desde el backend, la base se alcanza con el host `db` y el puerto `5432`, por ejemplo `postgresql+psycopg://USUARIO:CLAVE@db:5432/BASE`. Con `depends_on` y `condition: service_healthy` hacia `db`, el backend esperará a que la base esté lista.

## 13. Qué se verificó

- El YAML es válido; define los servicios `db` y `pgadmin`, los dos volúmenes con nombre fijo y la red, y todas las variables que usa están en `.env.example`.
- Se comprobó con un servidor PostgreSQL 16 de pruebas el comportamiento del healthcheck durante la inicialización: por socket responde, por TCP no, hasta que arranca el servidor definitivo.
- El `schema.sql` de la v6 se ejecutó antes completo y sin errores en PostgreSQL 16.15.
- **No se pudo ejecutar Docker en el entorno de trabajo**, así que el compose no se levantó de punta a punta. Valídalo en tu equipo con `docker compose config` y luego `docker compose up -d`. El healthcheck de pgAdmin (`/misc/ping` con `wget`) es el punto que más conviene mirar: si `docker compose ps` lo muestra como `unhealthy` aunque pgAdmin funcione, elimina ese bloque `healthcheck`: ningún otro servicio depende de él.