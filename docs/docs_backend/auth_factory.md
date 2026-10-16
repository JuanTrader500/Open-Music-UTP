# Implementación del Factory Method para Usuarios (ESC-03)

Este módulo implementa la creación de usuarios utilizando el patrón **Factory Method**. El objetivo es desacoplar la lógica de creación de usuarios de sus clases concretas, permitiendo que el sistema cree diferentes tipos de usuarios (Invitado, Registrado, Administrador) sin conocer los detalles de su instanciación.

## 🏗️ Arquitectura: Factory Method

El sistema utiliza una clase creadora abstracta (`UserCreator`) que define el método fábrica `create_user()`. Cada tipo de usuario tiene su propia clase creadora concreta que implementa la lógica de validación y creación específica.

### Beneficios de este enfoque:
- **Cápsula de Validación**: Las reglas de negocio (RN) como la longitud de la contraseña o la normalización del correo se ejecutan dentro del creador, asegurando que nunca se instancie un usuario inválido.
- **Extensibilidad**: Para añadir un nuevo rol (ej. Moderador), solo es necesario crear una nueva clase `ModeratorCreator` sin modificar el código que solicita la creación del usuario.
- **Simplificación del Cliente**: El cliente utiliza la función `creator_for()`, que actúa como un selector simple, eliminando la necesidad de múltiples bloques `if/elif` en la lógica de negocio.

---

## 📂 Mapa de Archivos y Responsabilidades

| Archivo | Responsabilidad | Descripción |
| :--- | :--- | :--- |
| `app/auth/factory.py` | **Lógica de Creación** | Contiene la clase abstracta `UserCreator`, las implementaciones concretas (`GuestCreator`, `RegisteredCreator`, `AdminCreator`) y los modelos de usuario. |

---

## 🚀 Flujo de Funcionamiento

1. **Solicitud**: El sistema recibe una petición para crear un usuario de tipo `"registered"`.
2. **Selección**: La función `creator_for("registered", ...)` devuelve una instancia de `RegisteredCreator`.
3. **Ejecución**: Se llama al método `create_user()`.
4. **Validación**: El creador normaliza el correo, verifica la longitud de la contraseña y comprueba la unicidad del correo electrónico.
5. **Resultado**: Se devuelve un objeto `RegisteredUser` validado y listo para ser persistido.

### 🛠️ Trazabilidad de Reglas de Negocio
- **RN-004 (Correo Único)**: Validada en `RegisteredCreator.create_user()`.
- **RN-015 (Privacidad)**: Garantizada mediante el atributo `password_hashed` en el modelo `User`.
- **RNF-026 (Seguridad)**: Validación de longitud mínima de contraseña en los creadores de usuarios registrados y admins.
