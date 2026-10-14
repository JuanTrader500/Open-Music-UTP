# Implementación del Módulo de Proveedores de Música (Abstract Factory)

Este módulo implementa la capa de acceso a datos para el catálogo de música, utilizando el patrón de diseño **Abstract Factory**. El objetivo principal es desacoplar la lógica de negocio del sistema de la API específica del proveedor de música (en este caso, YouTube), permitiendo cambiar de proveedor sin afectar el resto de la aplicación.

##  Arquitectura: Abstract Factory

El sistema define una "familia" de productos relacionados (clientes de búsqueda, detalles y playlists). En lugar de instanciar clases concretas de YouTube directamente en el código, el sistema utiliza una **Fábrica Abstracta** que garantiza que todos los productos creados sean compatibles entre sí.

### Beneficios de este enfoque:
- **Intercambiabilidad**: Podemos cambiar entre `youtube` y `simulated` mediante una variable de entorno.
- **Mantenibilidad**: Si YouTube cambia su API, solo se modifican los archivos en la carpeta `youtube/`, sin tocar la lógica de negocio.
- **Testabilidad**: Permite usar el proveedor `simulated` para pruebas unitarias sin gastar cuotas de la API de YouTube.

---

##  Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/catalog/providers/base.py` | **Contratos (Interfaces)** | Define las clases abstractas (`SearchClient`, `VideoDetailsClient`, `PlaylistClient`) y la `MusicProviderFactory`. Es el "manual de instrucciones" que todo proveedor debe seguir. |
| `app/catalog/providers/registry.py` | **Selector de Fábrica** | Contiene la función `build_provider_factory()` que lee la configuración y decide qué fábrica concreta instanciar. |
| `app/catalog/providers/youtube/factory.py` | **Fábrica Concreta de YouTube** | Implementa la creación de los clientes de YouTube. Gestiona la conexión inicial y la API Key de Google. |
| `app/catalog/providers/youtube/clients.py` | **Implementación Real (Productos)** | Contiene la lógica técnica para comunicarse con la API v3 de YouTube (peticiones HTTP, manejo de cuotas y errores). |
| `app/core/config.py` | **Configuración** | Define las variables de entorno necesarias (`YOUTUBE_API_KEY`, `MUSIC_PROVIDER`) para que el sistema sepa cómo configurarse. |

---

##  Guía de Ejecución y Demostración

Para testear la implementación y realizar una demostración de funcionamiento, el proyecto incluye un script especializado.

### 1. Configuración Previa
Asegúrate de tener un archivo `.env` en la raíz con las siguientes variables:
```env
MUSIC_PROVIDER=youtube
YOUTUBE_API_KEY=TU_API_KEY_AQUÍ
```

### 2. Ejecución de la Demo
Desde la carpeta `backend/`, ejecuta los siguientes comandos según lo que desees demostrar:

#### A. Búsqueda Real en YouTube
Busca canciones reales utilizando la API de YouTube:
```bash
python -m scripts.demo_youtube --provider youtube search "Salsa Clasica"
```

#### B. Búsqueda Simulada
Demuestra la flexibilidad del patrón cambiando al proveedor simulado (no requiere API Key):
```bash
python -m scripts.demo_youtube --provider simulated search "Rock"
```

#### C. Importación de Playlist
Carga los videos de una playlist específica de YouTube:
```bash
python -m scripts.demo_youtube --provider youtube playlist <ID_DE_LA_PLAYLIST>
```

###  Flujo de Llamada en la Demo
`demo_youtube.py` $\rightarrow$ `build_provider_factory()` $\rightarrow$ `YouTubeProviderFactory` $\rightarrow$ `YouTubeSearchClient` $\rightarrow$ **API YouTube**
