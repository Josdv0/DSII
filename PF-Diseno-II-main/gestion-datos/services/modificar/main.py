from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

try:
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import leer_foto, validar_documento, validar_persona
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import leer_foto, validar_documento, validar_persona

app = FastAPI(title="Microservicio Modificar Datos Personales")

COLS = (
    "tipo_documento, nro_documento, primer_nombre, segundo_nombre, apellidos, "
    "fecha_nacimiento, genero, correo, celular, (foto IS NOT NULL) AS tiene_foto"
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/personas/{documento}")
def cargar(documento: str):
    """Carga los datos actuales para precargar el formulario (no genera log de consulta)."""
    validar_documento(documento)
    with cursor() as cur:
        cur.execute(f"SELECT {COLS} FROM personas WHERE nro_documento=%s", (documento,))
        row = cur.fetchone()
    if not row:
        raise HTTPException(404, ["Persona no encontrada"])
    return row


@app.put("/personas/{documento}")
def modificar(
    documento: str,
    tipo_documento: Optional[str] = Form(None),
    primer_nombre: Optional[str] = Form(None),
    segundo_nombre: Optional[str] = Form(None),
    apellidos: Optional[str] = Form(None),
    fecha_nacimiento: Optional[str] = Form(None),
    genero: Optional[str] = Form(None),
    correo: Optional[str] = Form(None),
    celular: Optional[str] = Form(None),
    foto: Optional[UploadFile] = File(None),
    usuario: str = Depends(get_user),
):
    validar_documento(documento)  # el documento es la llave: no se modifica
    cambios = validar_persona(
        dict(
            tipo_documento=tipo_documento,
            primer_nombre=primer_nombre,
            segundo_nombre=segundo_nombre,
            apellidos=apellidos,
            fecha_nacimiento=fecha_nacimiento,
            genero=genero,
            correo=correo,
            celular=celular,
        ),
        parcial=True,
    )
    foto_bytes, foto_tipo = leer_foto(foto)
    if foto_bytes:
        cambios.update(foto=foto_bytes, foto_tipo=foto_tipo)
    if not cambios:
        raise HTTPException(422, ["No se envió ningún campo para modificar"])

    sets = ", ".join(f"{k}=%({k})s" for k in cambios) + ", actualizado_en=now()"
    with cursor() as cur:
        cur.execute(
            f"UPDATE personas SET {sets} WHERE nro_documento=%(_doc)s",
            {**cambios, "_doc": documento},
        )
        if cur.rowcount == 0:
            raise HTTPException(404, ["Persona no encontrada"])
        campos = ", ".join(k for k in cambios if k not in ("foto", "foto_tipo")) + (
            ", foto" if foto_bytes else ""
        )
        registrar_log(cur, "MODIFICAR", documento, usuario, f"Campos: {campos}")
    return {"mensaje": "Persona actualizada", "nro_documento": documento}
