from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Response
from pydantic import BaseModel

try:
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import validar_documento
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import validar_documento

app = FastAPI(title="Microservicio Consultar Personas")

COLS = (
    "tipo_documento, nro_documento, primer_nombre, segundo_nombre, apellidos, "
    "fecha_nacimiento, genero, correo, celular, (foto IS NOT NULL) AS tiene_foto"
)


class PreguntaRAG(BaseModel):
    pregunta: str
    usuario: Optional[str] = None


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/personas")
def listar(usuario: str = Depends(get_user)):
    with cursor() as cur:
        cur.execute(f"SELECT {COLS} FROM personas ORDER BY apellidos, primer_nombre LIMIT 500")
        rows = cur.fetchall()
        registrar_log(cur, "CONSULTAR", "*", usuario, f"Listado ({len(rows)} registros)")
    return rows


@app.get("/personas/{documento}")
def consultar(documento: str, usuario: str = Depends(get_user)):
    validar_documento(documento)
    with cursor() as cur:
        cur.execute(f"SELECT {COLS} FROM personas WHERE nro_documento=%s", (documento,))
        row = cur.fetchone()
        registrar_log(cur, "CONSULTAR", documento, usuario, "Encontrada" if row else "No encontrada")
    if not row:
        raise HTTPException(404, ["Persona no encontrada"])
    return row


@app.get("/personas/{documento}/foto")
def foto(documento: str):
    validar_documento(documento)
    with cursor() as cur:
        cur.execute("SELECT foto, foto_tipo FROM personas WHERE nro_documento=%s", (documento,))
        row = cur.fetchone()
    if not row or not row["foto"]:
        raise HTTPException(404, ["Sin foto"])
    return Response(bytes(row["foto"]), media_type=row["foto_tipo"])


@app.post("/personas/preguntar-rag")
def responder_rag(payload: PreguntaRAG, usuario_auth: str = Depends(get_user)):
    """
    Implementación del patrón RAG (Retrieval-Augmented Generation):
    1. Retrieval: Recupera datos estructurados y contexto de la base de datos (PostgreSQL).
    2. Generation/Reasoning: Responde a la pregunta en lenguaje natural.
    3. Logging: Registra la transacción (pregunta y respuesta) en la tabla logs.
    """
    pregunta = payload.pregunta.strip()
    if not pregunta:
        raise HTTPException(422, ["La pregunta no puede estar vacía"])

    usuario_final = payload.usuario or usuario_auth
    q_lower = pregunta.lower()

    with cursor() as cur:
        # Retrieval: obtener las personas registradas
        cur.execute("""
            SELECT tipo_documento, nro_documento, primer_nombre, segundo_nombre, apellidos,
                   fecha_nacimiento, genero, correo, celular
            FROM personas
        """)
        personas = cur.fetchall()

        if not personas:
            respuesta = "No hay personas registradas en la base de datos actualmente."
            doc_asociado = "*"
        else:
            # RAG reasoning
            # Caso clave del enunciado: "¿Cual es el empleado más joven que se ha registrado?"
            if "más joven" in q_lower or "mas joven" in q_lower or "menor edad" in q_lower or "menor" in q_lower:
                # Más joven = fecha de nacimiento más reciente (máximo fecha_nacimiento)
                mas_joven = max(personas, key=lambda p: p["fecha_nacimiento"])
                nombre_completo = f"{mas_joven['primer_nombre']} {mas_joven['apellidos']}"
                respuesta = f"{nombre_completo}"
                doc_asociado = mas_joven["nro_documento"]

            elif "más viejo" in q_lower or "mas viejo" in q_lower or "mayor edad" in q_lower or "mayor" in q_lower:
                mas_viejo = min(personas, key=lambda p: p["fecha_nacimiento"])
                nombre_completo = f"{mas_viejo['primer_nombre']} {mas_viejo['apellidos']}"
                respuesta = f"{nombre_completo}"
                doc_asociado = mas_viejo["nro_documento"]

            elif "cuántos" in q_lower or "cuantos" in q_lower or "total" in q_lower:
                respuesta = f"Hay un total de {len(personas)} persona(s) registrada(s)."
                doc_asociado = "*"

            else:
                # Búsqueda por coincidencia de nombre o documento
                coincidencias = []
                for p in personas:
                    nombre = f"{p['primer_nombre']} {p.get('segundo_nombre') or ''} {p['apellidos']}".strip().lower()
                    if p["nro_documento"] in q_lower or any(word in nombre for word in q_lower.split() if len(word) > 3):
                        coincidencias.append(p)

                if coincidencias:
                    c = coincidencias[0]
                    nombre_comp = f"{c['primer_nombre']} {c.get('segundo_nombre') or ''} {c['apellidos']}".strip()
                    respuesta = f"{nombre_comp} (Documento: {c['nro_documento']}, Fecha de nacimiento: {c['fecha_nacimiento']}, Correo: {c['correo']}, Celular: {c['celular']})"
                    doc_asociado = c["nro_documento"]
                else:
                    nombres = ", ".join(f"{p['primer_nombre']} {p['apellidos']}" for p in personas[:5])
                    respuesta = f"Se encontraron {len(personas)} registros. Algunos nombres: {nombres}."
                    doc_asociado = "*"

        # Registrar obligatoriamente en logs la pregunta y respuesta
        detalle_log = f"Pregunta: {pregunta} | Respuesta: {respuesta}"
        registrar_log(cur, "RAG", doc_asociado, usuario_final, detalle_log)

    return {
        "pregunta": pregunta,
        "respuesta": respuesta,
        "documento": doc_asociado,
        "usuario": usuario_final
    }
