# Implementación del Singleton para Configuración Global (ESC-05)

Este módulo implementa el patrón **Singleton** para garantizar que la configuración del sistema y el estado del runtime sean únicos y consistentes en todo el proceso de ejecución.

##  Arquitectura: Singleton

El sistema separa **el acceso real a la configuración** de **la demostración académica del patrón** (RNF-021):

1. **Acceso real — Singleton Funcional (`lru_cache`)**: `get_settings()` lee el `.env` una sola vez y devuelve siempre la misma instancia de `Settings`. Es la **única** vía de acceso a la configuración; se inyecta con `Depends(get_settings)` y las pruebas que la cambian llaman a `get_settings.cache_clear()`.
2. **Demostración del patrón — Metaclase Singleton (`SingletonMeta`)**: `AppRuntime` y `get_runtime()` existen solo para mostrar el patrón de forma explícita (RNF-021). **Ningún service ni router puede importarlos**; hay una prueba que lo verifica (`tests/unit/test_architecture.py`).

### Beneficios de este enfoque:
- **Eficiencia de Recursos**: Evita leer el archivo `.env` y parsear variables de entorno cada vez que se necesita un dato de configuración.
- **Consistencia**: Evita que diferentes módulos tengan visiones distintas de la configuración (ej. que un módulo crea que el proveedor es "youtube" y otro "simulated").
- **Frontera clara**: una sola puerta (`get_settings`) para el código de producción; el patrón clásico queda aislado y documentado para la sustentación.

---

##  Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/core/singleton.py` | **Infraestructura (demostración)** | Implementa la `SingletonMeta` que controla la creación de instancias únicas. |
| `app/core/config.py` | **Aplicación** | Define `Settings`, `get_settings()` (acceso real) y `AppRuntime` (demostración del patrón). |

---

##  Flujo de Funcionamiento

1. **Primera Llamada**: el módulo `A` llama a `get_settings()`. El sistema lee el `.env` y crea el objeto `Settings`.
2. **Cacheo**: el resultado se guarda en el cache de `lru_cache`.
3. **Llamadas Posteriores**: el módulo `B` llama a `get_settings()`. El sistema devuelve inmediatamente la instancia cacheada sin volver a leer el disco.
4. **Runtime (solo demostración)**: `AppRuntime` usa la metaclase para asegurar que, aunque se instancie en varios lugares, siempre sea el mismo objeto. No se usa en el código de producción.

###  Trazabilidad de Reglas de Negocio
- **RNF-031 (Configuración por entorno)**: Asegura que todas las variables del `.env` se carguen en un único lugar centralizado.
- **RNF-015/017 (Configuración única)**: Garantiza que no haya divergencias de configuración durante la ejecución del backend.
