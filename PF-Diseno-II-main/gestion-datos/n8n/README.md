# Flujo RAG en n8n para Consulta en Lenguaje Natural

Este directorio contiene el flujo de trabajo (`workflow_rag.json`) para cumplir con los requerimientos:
1. **Consulta en lenguaje natural utilizando n8n y aplicando RAG (12 pts)**
2. **Chat en donde se hace la pregunta y la respuesta se debe ver en la interfaz de n8n**
3. **Registro obligatorio de toda transacción en el log**, incluyendo las preguntas y respuestas en lenguaje natural.

---

## Cómo importar el flujo en n8n

### Opción 1: Desde la interfaz de n8n (Recomendada)
1. Abre tu navegador en `http://localhost:5678`.
2. Si es la primera vez, completa la configuración inicial básica de n8n.
3. Ve a **Workflows** -> haz clic en el menú de tres puntos `...` (arriba a la derecha) o presiona `Ctrl + O` / **Import from File**.
4. Selecciona el archivo `n8n/workflow_rag.json`.
5. Haz clic en **Save** y luego en **Active** (activar flujo).

### Opción 2: Mediante la CLI de Docker
Puedes importar el flujo directamente al contenedor de n8n ejecutando:
```bash
docker compose exec n8n n8n import:workflow /backup/workflows/workflow_rag.json
```

---

## Cómo probar la consulta en lenguaje natural

1. En la interfaz de n8n (`http://localhost:5678`), abre el flujo importado **"Consulta RAG Datos Personales"**.
2. Haz clic en el botón **"Chat"** (o en el nodo `When chat message received` -> **"Test step"** / **"Open Chat"**).
3. Escribe la pregunta del enunciado:
   > **"¿Cual es el empleado más joven que se ha registrado?"**
4. Observa la respuesta inmediata:
   > **"Pedro Pérez"**
5. Ve a la interfaz de la aplicación (`http://localhost:8080`) en la pestaña **"Consultar logs"**:
   - Verás la transacción registrada con tipo `RAG`, documento `1001`, usuario `n8n_chat` y el detalle con la pregunta y respuesta exacta.

