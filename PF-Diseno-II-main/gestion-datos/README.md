# APLICACIÓN DE GESTIÓN DE DATOS PERSONALES
**Trabajo Final - Diseño de Software II**

Sistema modular basado en microservicios, desplegado en contenedores Docker, con persistencia en PostgreSQL (pgvector), autenticación SSO, trazabilidad completa mediante logs de auditoría y módulo de consulta en lenguaje natural aplicando el patrón RAG con n8n.

---

## 📋 Matriz de Cumplimiento de Requerimientos

| Requerimiento / Actividad | Puntos | Estado | Detalle de Implementación |
| :--- | :---: | :---: | :--- |
| **CRUD y registro de transacciones en log** (Llave de búsqueda: documento) | **15** | ✅ Cumplido | Microservicios independientes para Crear, Modificar, Consultar y Borrar. Toda operación se registra en la tabla `logs` usando el documento como identificador. |
| **Consulta en lenguaje natural utilizando n8n y aplicando RAG** | **12** | ✅ Cumplido | Implementado en n8n mediante flujo con Chat Trigger, recuperación de contexto desde PostgreSQL y respuesta en lenguaje natural. Chat disponible en n8n (`http://localhost:5678`) y en la aplicación. Preguntas y respuestas se registran en `logs` (`tipo_transaccion='RAG'`). |
| **Microservicio por cada opción del menú** | **5** | ✅ Cumplido | `crear`, `modificar`, `consultar`, `borrar`, `logs` y `lenguaje_natural` (n8n). |
| **Sistema de autenticación SSO** | **4** | ✅ Cumplido | Soporte para SSO con OpenID Connect / OAuth2 (Keycloak preconfigurado, compatible con Microsoft Entra / Roble). Valida tokens JWT con JWKS. |
| **Validaciones requeridas** | **4** | ✅ Cumplido | Verificación estricta en frontend y backend para todos los campos (tipo de doc, documento, nombres sin números, fechas, géneros, correo, celular de 10 dígitos y foto máx 2 MB). |
| **Contenedor independiente de "Consultar" habilitable/deshabilitable** | **3** | ✅ Cumplido | El servicio `consultar` se gestiona con profile `consulta`. Al deshabilitarlo con `docker compose stop consultar`, la UI responde informando no disponibilidad sin afectar al resto del sistema. |
| **Consulta de log por tipo, documento y fecha** | **3** | ✅ Cumplido | Filtros combinables en UI y API para buscar por tipo (`CREAR`, `MODIFICAR`, `CONSULTAR`, `BORRAR`, `RAG`), por documento y por fecha (exacta o rango). |
| **Campos capturados en pantalla principal y foto** | **2** | ✅ Cumplido | Tipo doc, Nro doc, Primer nombre, Segundo nombre, Apellidos, Fecha nacimiento, Género, Correo, Celular y Foto con avatar interactivo. |
| **Base de datos en contenedor independiente** | **2** | ✅ Cumplido | Servicio `db` en contenedor Docker dedicado con PostgreSQL 16 y extensión pgvector. |

---

## 🚀 Despliegue Rápido con Docker

### 1. Variables de Entorno
Copia el archivo de ejemplo para generar tu configuración `.env`:
```bash
cp .env.example .env
```

### 2. Iniciar la Aplicación (con servicio de Consulta activado)
```bash
docker compose --profile consulta up -d --build
```

**Accesos del sistema:**
- 🌐 **Interfaz Web Principal:** [http://localhost:8080](http://localhost:8080)
- 🤖 **Interfaz de Chat n8n:** [http://localhost:5678](http://localhost:5678)
- 🔐 **Servidor SSO (Keycloak - opcional):** [http://localhost:8081](http://localhost:8081)

---

## 🔍 Prueba de Alta Disponibilidad: Habilitar / Deshabilitar "Consultar"

El requerimiento exige que la opción de "Consultar" esté en un contenedor independiente y se pueda habilitar/deshabilitar según demanda:

```bash
# 1. Deshabilitar el contenedor de consulta
docker compose stop consultar

# Al intentar consultar en http://localhost:8080 se mostrará:
# "El servicio no está disponible en este momento"
# El resto de microservicios (Crear, Modificar, Borrar, Logs) sigue funcionando al 100%.

# 2. Habilitar nuevamente la consulta
docker compose --profile consulta up -d consultar
```

---

## 🤖 Consulta en Lenguaje Natural con n8n y RAG

### Caso de Prueba del Enunciado:
- **Pregunta:** *"¿Cual es el empleado más joven que se ha registrado?"*
- **Respuesta generada:** **Pedro Pérez** (nacido el 05-mar-2001)

### Pasos para probar en n8n:
1. Accede a `http://localhost:5678`.
2. En la sección **Workflows**, importa el archivo `n8n/workflow_rag.json` (o ejecuta: `docker compose exec n8n n8n import:workflow /backup/workflows/workflow_rag.json`).
3. Activa el flujo y abre la ventana de **Chat**.
4. Envía la pregunta: `¿Cual es el empleado más joven que se ha registrado?`.
5. Recibirás la respuesta: `Pedro Pérez`.
6. Abre la pestaña **Consultar log** en la web (`http://localhost:8080`): verás la pregunta y respuesta registradas con `tipo_transaccion: RAG`.

---

## 🔐 Autenticación SSO (Keycloak / Microsoft Entra)

Para activar el entorno con SSO habilitado:
1. Cambia en tu `.env`:
   ```ini
   AUTH_ENABLED=true
   ```
2. Inicia los contenedores agregando el perfil `auth`:
   ```bash
   docker compose --profile consulta --profile auth up -d
   ```
3. Keycloak se iniciará en `http://localhost:8081` con el Realm `gestion` y usuarios precargados:
   - **Usuario Docente:** `docente` / Clave: `docente123`
   - **Usuario Admin:** `admin` / Clave: `admin123`
   - **Usuario Estudiante:** `estudiante` / Clave: `estudiante123`

---

## 🧪 Pruebas Rápidas con `curl`

```bash
# 1. Crear persona con validaciones (Tipo de documento, celular de 10 dígitos, etc.)
curl -F "tipo_documento=Cédula" \
     -F "nro_documento=1001" \
     -F "primer_nombre=Pedro" \
     -F "apellidos=Pérez" \
     -F "fecha_nacimiento=05-mar-2001" \
     -F "genero=Masculino" \
     -F "correo=pedro.perez@example.com" \
     -F "celular=3001234567" \
     http://localhost:8080/api/crear/personas

# 2. Consultar persona por documento (llave de búsqueda)
curl http://localhost:8080/api/consultar/personas/1001

# 3. Consulta RAG en Lenguaje Natural
curl -X POST http://localhost:8080/api/consultar/personas/preguntar-rag \
     -H "Content-Type: application/json" \
     -d '{"pregunta": "¿Cual es el empleado más joven que se ha registrado?"}'

# 4. Consultar logs de auditoría (por tipo RAG o CREAR, documento o fecha)
curl "http://localhost:8080/api/logs/logs?tipo=RAG"
curl "http://localhost:8080/api/logs/logs?documento=1001"

# 5. Modificar datos personales
curl -X PUT -F "celular=3009998877" \
     http://localhost:8080/api/modificar/personas/1001

# 6. Borrar persona
curl -X DELETE http://localhost:8080/api/borrar/personas/1001
```
