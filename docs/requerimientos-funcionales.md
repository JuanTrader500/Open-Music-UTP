# Requerimientos funcionales — creación de objetos

Base: SRS **SRS-RMW-001 v0.4** y `README.md` (trazabilidad `RF-###`, `RN-###`, `RNF-###`).
Solo se detallan los RF que implican creación de objetos y el patrón creacional
con el que se resuelven. Cada escenario usa formato `Given/When/Then`
(Dado/Cuando/Entonces) y sirve como prueba de que la implementación cumple el RF.

## ESC-01 · RF-010 Buscar canciones + RF-011 Importar playlist semilla
**Módulo:** `catalog/providers` · **RN:** RN-009 (género), RN-012 (solo embebibles)
**RNF:** RNF-003 (clave solo backend), RNF-023/024 (tolerancia a fallos y cuota), RNF-033 (pruebas sin cuota)

Crea objetos `TrackMetadata` (`video_id`, título, artista, duración, vistas, embebible)
a partir de una familia de clientes del proveedor.

**Escenario 1.1 — búsqueda exitosa (happy path)**
```gherkin
Given un usuario invitado en la pantalla de búsqueda
  And el proveedor configurado es "simulated"
When busca "cafeteros" con máximo 20 resultados
Then recibe la lista ordenada ["sim_rock_01", "sim_rock_02"]
  And cada item tiene título, artista y duración >= 0
  And no se consume cuota de YouTube
```

**Escenario 1.2 — consulta inválida no gasta cuota**
```gherkin
Given un usuario en la pantalla de búsqueda
When busca "a" (menos de 2 caracteres)
Then el sistema lanza InvalidQueryError
  And no se llama a search.list del proveedor
```

**Escenario 1.3 — se filtran no reproducibles**
```gherkin
Given la playlist semilla "PL_SIM_SALSA" con 3 videos (1 no embebible)
When se importa la playlist
Then solo se devuelven ["sim_salsa_01", "sim_salsa_02"]
  And se conserva el orden de origen
```

**Patrón:** Abstract Factory (`MusicProviderFactory`). Ver `docs/abstract-factory.md`.
**Por qué:** familia coherente (búsqueda + detalles + playlists) del mismo proveedor;
el cliente `MusicProvider` no conoce clases concretas (abierto/cerrado, R-02).

## ESC-02 · RF-013 Crear playlist
**Módulo:** `playlists` · **RN:** RN-002 (límites por usuario), RN-003 (orden propio),
RN-010 (máximo de pistas)
**RNF:** RNF-015/016 (persistencia posterior, TBD-02)

Crea objetos `Playlist` con construcción por pasos: nombre → descripción →
agregar pistas → reordenar → marcar favorita.

**Escenario 2.1 — crear playlist válida**
```gherkin
Given un usuario registrado sin playlists
When crea la playlist "Salsa clásica" con descripción "Para el fin de semana"
  And agrega las pistas ["sim_salsa_01", "sim_salsa_02"]
Then la playlist queda con 2 pistas en ese orden
  And queda marcada como no favorita por defecto
```

**Escenario 2.2 — nombre inválido**
```gherkin
Given un usuario registrado
When intenta crear una playlist con nombre vacío
Then el sistema rechaza la creación con ValueError
  And no se crea ningún objeto Playlist
```

**Escenario 2.3 — reordenar**
```gherkin
Given una playlist con pistas ["A", "B", "C"]
When mueve "C" a la posición 0
Then el orden queda ["C", "A", "B"]
```

**Patrón:** Builder (`PlaylistBuilder`). Ver `docs/design-patterns.md` y
`backend/app/playlists/builder.py`.
**Por qué:** objeto con muchas partes opcionales y validación incremental;
evita constructor telescópico y permite `build()` solo si es válido.

## ESC-03 · RF-017 Registrar cuenta (+ RF-018 iniciar sesión)
**Módulo:** `auth` · **RN:** RN-004 (cuenta única por correo), RN-015 (privacidad)
**RNF:** RNF-026 (hash Argon2/bcrypt), RNF-027 (sesión con caducidad), RNF-029 (rate limit)

Crea objetos `User`: invitado, registrado y administrador, con reglas distintas
de validación y permisos.

**Escenario 3.1 — registro válido**
```gherkin
Given un visitante sin cuenta
When se registra con correo "est@utp.edu.co" y clave de 8+ caracteres
Then se crea un RegisteredUser con correo normalizado
  And la clave queda marcada como hasheada (no en claro)
```

**Escenario 3.2 — correo duplicado**
```gherkin
Given un usuario ya registrado con "est@utp.edu.co"
When otro visitante intenta registrarse con el mismo correo
Then el sistema rechaza con ValueError (RN-004)
```

**Escenario 3.3 — sesión de invitado**
```gherkin
Given un visitante sin registro
When continúa como invitado
Then se crea un GuestUser con permisos limitados
  And no requiere correo ni clave
```

**Patrón:** Factory Method (`UserCreator.create_user()`).
Ver `backend/app/auth/factory.py`.
**Por qué:** la creación varía por tipo pero el cliente pide "un usuario"
sin acoplar `if/elif` de clases concretas; agregar un rol nuevo = una creadora nueva.

## ESC-04 · RF-023 Registrar escucha (+ RF-024 historial)
**Módulo:** `listening` · **RN:** RN-005 (omitida si < 30 s), RN-006 (agregación por género/artista)

Crea objetos `ListeningRecord` (usuario, pista, segundos, género) a alto volumen,
incluido el generador de simulación (RF-028).

**Escenario 4.1 — escucha completa**
```gherkin
Given el usuario escuchó 187 s de "sim_rock_01" (rock)
When se registra la escucha
Then el registro queda con skipped = false
  And aporta 187 s al resumen de rock
```

**Escenario 4.2 — pista omitida**
```gherkin
Given el usuario escuchó 12 s de "sim_rock_02"
When se registra la escucha
Then el registro queda con skipped = true (RN-005)
```

**Escenario 4.3 — clonación para simulación**
```gherkin
Given una escucha prototipo de 180 s de rock
When se clona cambiando solo el usuario y la pista
Then el clon conserva duración y género pero con nuevo usuario/pista
  And modificar el clon no afecta al prototipo
```

**Patrón:** Prototype (`ListeningRecord.clone()`).
Ver `backend/app/listening/prototype.py`.
**Por qué:** miles de registros/simulaciones con la misma forma; clonar es más
barato y seguro que reconstruir y evita compartir estado mutable.

## ESC-05 · Configuración global (transversal, RNF-031)
**Módulo:** `core/config` · **RNF:** RNF-031 (todo por variables de entorno),
RNF-015/017 (config única)

Una sola instancia de configuración en todo el proceso.

```gherkin
Given dos módulos que piden la configuración
When ambos llaman a get_runtime() / get_settings()
Then reciben la misma instancia
  And cambiar MUSIC_PROVIDER en un punto es visible en todos
```

**Patrón:** Singleton (`SingletonMeta` + `get_settings()` con `lru_cache`).
Ver `backend/app/core/singleton.py` y `backend/app/core/config.py:40-42`.
**Por qué:** la configuración debe ser única y perezosa; `lru_cache` + metaclase
evitan múltiples lecturas de `.env` y divergencias.

## Trazabilidad (RF → patrón → código → test)

| Escenario | RF | Crea | Patrón | Evidencia código | Evidencia test |
|---|---|---|---|---|---|
| ESC-01 | RF-010/011 | `TrackMetadata` (familia) | Abstract Factory | `catalog/providers/base.py`, `music_provider.py`, `registry.py` | `tests/catalog/test_providers.py`, `tests/acceptance/test_creational_acceptance.py::test_esc01_*` |
| ESC-02 | RF-013 | `Playlist` | Builder | `playlists/builder.py` | `test_creational_patterns.py::TestPlaylistBuilder` + `test_esc02_*` |
| ESC-03 | RF-017/018 | `User` | Factory Method | `auth/factory.py` | `TestUserFactory` + `test_esc03_*` |
| ESC-04 | RF-023/024 | `ListeningRecord` | Prototype | `listening/prototype.py` | `TestListeningPrototype` + `test_esc04_*` |
| ESC-05 | — (RNF-031) | Config única | Singleton | `core/singleton.py`, `core/config.py` | `TestSingleton` + `test_esc05_*` |
