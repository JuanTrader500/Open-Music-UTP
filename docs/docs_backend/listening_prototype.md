# Implementación del Prototype para Registros de Escucha (ESC-04)

Este módulo implementa el patrón **Prototype** para gestionar los registros de escucha. Dado que el sistema genera miles de registros con estructuras idénticas (especialmente durante la simulación), clonar un objeto existente es más eficiente que crear uno desde cero.

##  Arquitectura: Prototype

El sistema define una clase `ListeningRecord` que incluye un método `clone()`. Este método crea una copia profunda del objeto actual, permitiendo modificar solo los campos necesarios (como el usuario o el track) mientras se mantienen los demás atributos.

### Beneficios de este enfoque:
- **Rendimiento**: Reduce el costo de instanciación repetitiva de objetos complejos.
- **Evita el Aliasing**: Al realizar una copia profunda, se asegura que modificar un clon no afecte al objeto original (prototipo).
- **Simplificación de Simulaciones**: Permite crear "plantillas" de escucha (ej. un registro de 180s de Rock) y clonarlas rápidamente para miles de usuarios simulados.

---

##  Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/listening/prototype.py` | **Modelo y Clonación** | Define la clase `ListeningRecord` y la lógica de clonación con sobrescritura de atributos. |

---

##  Flujo de Funcionamiento

1. **Creación del Prototipo**: Se crea un `ListeningRecord` base con datos comunes (ej. género "Jazz", duración "200s").
2. **Clonación**: Se llama al método `.clone(user_id="u2", track_id="t2")`.
3. **Sobrescritura**: El método `clone` toma los datos del original y aplica los cambios solicitados en los argumentos `**overrides`.
4. **Resultado**: Se obtiene un nuevo objeto independiente con la misma estructura que el original.

###  Trazabilidad de Reglas de Negocio
- **RN-005 (Pista omitida)**: Implementado en `is_skipped(threshold_s)`, que marca el registro como omitido si los segundos escuchados son menores que el umbral configurable.
- **RF-028 (Simulación)**: El patrón Prototype es la base técnica para generar datos sintéticos de escucha de forma masiva.
