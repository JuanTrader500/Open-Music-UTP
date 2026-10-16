# Implementación del Módulo de Proveedores de Música (Abstract Factory)

Este módulo implementa la capa de acceso a datos para el catálogo de música, utilizando el patrón de diseño **Abstract Factory**. El objetivo principal es desacoplar la lógica de negocio del sistema de la API específica del proveedor de música (en este caso, YouTube), permitiendo cambiar de proveedor sin afectar el resto de la aplicación.

##  Justificación del uso de Abstract Factory

Se ha seleccionado el patrón **Abstract Factory** debido a que el sistema requiere una **familia de productos relacionados** (Búsqueda, Detalles y Playlists) que deben ser coherentes entre sí. 

Si el sistema utilizara clases concretas, correríamos el riesgo de mezclar, por ejemplo, un cliente de búsqueda de YouTube con un cliente de detalles de Spotify, lo que rompería la aplicación. La Fábrica Abstracta garantiza que:
1. **Consistencia**: Si se elige el proveedor de YouTube, todos los clientes creados pertenecerán a la familia de YouTube.
2. **Desacoplamiento Total**: El código de negocio (`MusicProvider`) no sabe qué proveedor está usando; solo sabe que tiene un objeto que cumple con la interfaz de búsqueda y otro con la de detalles.
3. **Escalabilidad**: Agregar un nuevo proveedor (ej. Spotify, SoundCloud) solo requiere implementar una nueva fábrica y sus productos, sin modificar una sola línea de la lógica de negocio.

###  Ejemplo de Extensibilidad: Enriquecimiento con Spotify

Para demostrar la potencia de esta arquitectura, consideremos un caso de uso futuro: **Recolección de Metadatos Profesionales**.

Si el sistema necesita guardar en la base de datos información más detallada (como el álbum oficial, el sello discográfico o el género exacto) que YouTube no proporciona con precisión, podemos implementar un flujo híbrido:

1. **Búsqueda (YouTube)**: Se utiliza la `YouTubeProviderFactory` para encontrar la canción y obtener el ID del video.
2. **Enriquecimiento (Spotify)**: El sistema instancia una `SpotifyProviderFactory` y utiliza su `VideoDetailsClient` para buscar la misma canción por nombre y traer metadatos de alta calidad desde la API de Spotify.
3. **Persistencia**: Se guarda la data de Spotify en la base de datos, manteniendo la capacidad de reproducir el video de YouTube.

Esto es posible gracias a que el sistema depende de la **interfaz abstracta** `VideoDetailsClient` y no de una clase concreta. Así, podemos intercambiar el origen de los metadatos sin modificar la lógica de guardado en la base de datos.

##  Flujo de Funcionamiento Actual

El flujo de datos desde que se solicita una canción hasta que se obtienen los resultados es el siguiente:

1. **Carga de Configuración**: El sistema lee la variable `MUSIC_PROVIDER` del archivo `.env` a través de `config.py`.
2. **Selección de la Fábrica**: `registry.py` actúa como un despachador que, basándose en el nombre del proveedor, instancia la fábrica concreta correspondiente (ej. `YouTubeProviderFactory`).
3. **Creación de Clientes**: La fábrica concreta crea los tres productos especializados:
    - `SearchClient` $\rightarrow$ para obtener IDs de videos.
    - `VideoDetailsClient` $\rightarrow$ para obtener metadatos (título, duración).
    - `PlaylistClient` $\rightarrow$ para leer listas de reproducción.
4. **Orquestación de Lógica (`MusicProvider`)**: 
    - Llama al `SearchClient` para obtener una lista de IDs.
    - Pasa esos IDs al `VideoDetailsClient` para "hidratar" los resultados con información real.
    - Filtra los resultados para asegurar que los videos sean **embebibles** (reproducibles en la app).
5. **Acceso Externo**: Finalmente, los clientes concretos ejecutan las peticiones HTTP a la API de YouTube v3 y devuelven la respuesta procesada.

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



## Ejemplos para la demostracion:

Busqueda con nombre exato:
    - python -m scripts.demo_youtube --provider youtube search "romantika brutalismus 3000"

Test del youtube engine serch 

    - python -m scripts.demo_youtube --provider youtube search "brutalismus 3000 romanticas"
