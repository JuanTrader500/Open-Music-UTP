# Implementación del Builder para Playlists (ESC-02)

Este módulo utiliza el patrón **Builder** para la creación de playlists. Debido a que una playlist tiene múltiples atributos opcionales y requiere validaciones incrementales, el Builder permite construir el objeto paso a paso, asegurando que el resultado final sea siempre válido.

## 🏗️ Arquitectura: Builder

El sistema separa la representación del objeto (`Playlist`) de su construcción (`PlaylistBuilder`). El Builder ofrece una interfaz fluida (Fluent Interface) que permite encadenar métodos para configurar la playlist.

### Beneficios de este enfoque:
- **Prevención de Constructores Telescópicos**: Evita tener un constructor con 10 argumentos donde la mayoría son opcionales o nulos.
- **Validación en Tiempo Real**: Errores como nombres vacíos o longitud excesiva se detectan en el momento de llamar al método `with_name()`, no al final del proceso.
- **Inmutabilidad**: El objeto `Playlist` final es inmutable (`frozen=True`), lo que garantiza que una vez construida la playlist, no pueda ser alterada accidentalmente, solo reordenada mediante un método específico.

---

## 📂 Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/playlists/builder.py` | **Construcción y Modelo** | Define la clase `Playlist` (el producto) y la clase `PlaylistBuilder` (el constructor). |

---

## 🚀 Flujo de Funcionamiento

El proceso de creación sigue un orden lógico:

1. **Inicialización**: `PlaylistBuilder("user_123")` $\rightarrow$ Se define el dueño.
2. **Configuración**:
    - `.with_name("Mi Rock")` $\rightarrow$ Valida longitud y contenido.
    - `.with_description("Favoritas")` $\rightarrow$ Asigna descripción.
    - `.add_track("track_01")` $\rightarrow$ Valida que el ID no esté vacío y que no se supere el límite de 500 pistas (RN-010).
3. **Finalización**: `.build()` $\rightarrow$ Verifica que el nombre haya sido asignado y devuelve el objeto `Playlist` inmutable.

### 🛠️ Trazabilidad de Reglas de Negocio
- **RN-002 (Límites de nombre)**: Validada en `with_name()`.
- **RN-003 (Orden propio)**: Implementado en el método `Playlist.reordered()`.
- **RN-010 (Máximo de pistas)**: Validado en `add_track()`.
