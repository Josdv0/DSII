from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field

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

app = FastAPI(title="Microservicio Consulta y Registro de Logs")
TIPOS = {"CREAR", "MODIFICAR", "CONSULTAR", "BORRAR", "RAG", "CONSULTA_NL"}


class LogEntrada(BaseModel):
    tipo_transaccion: str
    documento: str = Field(default="*")
    usuario: Optional[str] = None
    detalle: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/logs")
def consultar_logs(
    tipo: Optional[str] = None,
    documento: Optional[str] = None,
    fecha: Optional[date] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None,
    usuario: str = Depends(get_user)
):
    """
    Filtros combinables:
    - tipo de transacción (CREAR, MODIFICAR, CONSULTAR, BORRAR, RAG)
    - documento (o '*' para consultas generales)
    - fecha de transacción (exacta con 'fecha', o rango con 'desde' y 'hasta')
    """
    where, params = [], []
    if tipo:
        t_upper = tipo.strip().upper()
        if t_upper not in TIPOS:
            raise HTTPException(422, [f"tipo: debe ser uno de {sorted(TIPOS)}"])
        where.append("tipo_transaccion=%s")
        params.append(t_upper)

    if documento:
        doc = documento.strip()
        doc_validado = validar_documento(doc, permitir_asterisco=True)
        where.append("documento=%s")
        params.append(doc_validado)

    if fecha:
        where.append("fecha::date = %s")
        params.append(fecha)
    else:
        if desde:
            where.append("fecha::date >= %s")
            params.append(desde)
        if hasta:
            where.append("fecha::date <= %s")
            params.append(hasta)

    sql = "SELECT id, tipo_transaccion, documento, usuario, detalle, fecha FROM logs"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY fecha DESC LIMIT 500"

    with cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


@app.post("/logs", status_code=201)
def crear_log(entrada: LogEntrada, usuario_auth: str = Depends(get_user)):
    """Permite a n8n o servicios externos registrar logs de transacciones (ej. consultas en lenguaje natural)."""
    t_upper = entrada.tipo_transaccion.strip().upper()
    if t_upper not in TIPOS:
        raise HTTPException(422, [f"tipo_transaccion: debe ser uno de {sorted(TIPOS)}"])

    doc = entrada.documento.strip()
    doc_validado = validar_documento(doc, permitir_asterisco=True)
    usuario_final = entrada.usuario or usuario_auth

    with cursor() as cur:
        registrar_log(cur, t_upper, doc_validado, usuario_final, entrada.detalle)

    return {"mensaje": "Log registrado exitosamente"}
