from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

try:
    from psycopg2 import errors
except ImportError:
    try:
        from psycopg import errors
    except ImportError:
        class _MockErrors:
            class UniqueViolation(Exception):
                pass
        errors = _MockErrors()

try:
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import leer_foto, validar_persona
except ImportError:
    BASE_DIR = Path(__file__).resolve().parent.parent.parent
    if str(BASE_DIR) not in sys.path:
        sys.path.insert(0, str(BASE_DIR))
    from common.auth import get_user
    from common.db import cursor, registrar_log
    from common.validators import leer_foto, validar_persona

app = FastAPI(title="Microservicio Crear Personas")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/personas", status_code=201)
def crear(
    tipo_documento: Optional[str] = Form(None),
    nro_documento: Optional[str] = Form(None),
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
    p = validar_persona(locals_form(tipo_documento, nro_documento, primer_nombre, segundo_nombre,
                                    apellidos, fecha_nacimiento, genero, correo, celular))
    foto_bytes, foto_tipo = leer_foto(foto)
    p.setdefault("segundo_nombre", None)
    with cursor() as cur:
        try:
            cur.execute(
                """INSERT INTO personas (tipo_documento, nro_documento, primer_nombre, segundo_nombre,
                   apellidos, fecha_nacimiento, genero, correo, celular, foto, foto_tipo)
                   VALUES (%(tipo_documento)s, %(nro_documento)s, %(primer_nombre)s, %(segundo_nombre)s,
                   %(apellidos)s, %(fecha_nacimiento)s, %(genero)s, %(correo)s, %(celular)s,
                   %(foto)s, %(foto_tipo)s)""",
                {**p, "foto": foto_bytes, "foto_tipo": foto_tipo},
            )
        except errors.UniqueViolation:
            raise HTTPException(409, ["nro_documento: ya existe una persona con ese documento"])
        registrar_log(cur, "CREAR", p["nro_documento"], usuario, "Persona creada")
    return {"mensaje": "Persona creada", "nro_documento": p["nro_documento"]}


def locals_form(*vals):
    keys = ["tipo_documento", "nro_documento", "primer_nombre", "segundo_nombre",
            "apellidos", "fecha_nacimiento", "genero", "correo", "celular"]
    return dict(zip(keys, vals))
