# Implementación del Singleton para Configuración Global (ESC-05)

Este módulo implementa el patrón **Singleton** para garantizar que la configuración del sistema y el estado del runtime sean únicos y consistentes en todo el proceso de ejecución.

## 🏗️ Arquitectura: Singleton

El sistema implementa el Singleton de dos maneras complementarias para cubrir diferentes necesidades:

1. **Metaclase Singleton (`SingletonMeta`)**: Proporciona un control total sobre la instanciación de clases. Cualquier clase que use esta metaclase garantiza que `Clase()` siempre devuelva la misma instancia.
2. **Singleton Funcional (`lru_cache`)**: Utiliza el decorador `@lru_cache` de Python en la función `get_settings()`, lo que provoca que la lectura del archivo `.env` se realice una sola vez y el resultado se cachee para siempre.

### Beneficios de este enfoque:
- **Eficiencia de Recursos**: Evita leer el archivo `.env` y parsear variables de entorno cada vez que se necesita un dato de configuración.
- **Consistencia**: Evita que diferentes módulos tengan visiones distintas de la configuración (ej. que un módulo crea que el proveedor es "youtube" y otro "simulated").
- **Punto de Acceso Único**: `get_runtime()` ofrece una puerta de entrada global al estado de la aplicación.

---

## 📂 Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/core/singleton.py` | **Infraestructura** | Implementa la `SingletonMeta` que controla la creación de instancias únicas. |
| `app/core/config.py` | **Aplicación** | Define `Settings` y `AppRuntime`, utilizando el singleton para gestionar el estado global. |

---

## 🚀 Flujo de Funcionamiento

1. **Primera Llamada**: El módulo `A` llama a `get_settings()`. El sistema lee el `.env` y crea el objeto `Settings`.
2. **Cacheo**: El resultado se guarda en el cache de `lru_cache`.
3. **Llamadas Posteriores**: El módulo `B` llama a `get_settings()`. El sistema devuelve inmediatamente la instancia cacheada sin volver a leer el disco.
4. **Runtime Global**: `AppRuntime` utiliza la metaclase para asegurar que, aunque se instancie en varios lugares, siempre sea el mismo objeto gestionando la configuración.

### 🛠️ Trazabilidad de Reglas de Negocio
- **RNF-031 (Configuración por entorno)**: Asegura que todas las variables del `.env` se carguen en un único lugar centralizado.
- **RNF-015/017 (Configuración única)**: Garantiza que no haya divergencias de configuración durante la ejecución del backend.
