from __future__ import annotations
import re
from datetime import date
from typing import Optional, Union, List, Dict
from fastapi import HTTPException, UploadFile

# Tipo de documento: lista con dos valores (Tarjeta de identidad, Cédula), compatible con T.I y C.C
TIPOS_DOC_VALIDOS = {
    "tarjeta de identidad": "Tarjeta de identidad",
    "t.i": "Tarjeta de identidad",
    "ti": "Tarjeta de identidad",
    "cédula": "Cédula",
    "cedula": "Cédula",
    "c.c": "Cédula",
    "cc": "Cédula",
}

# Género: debe ser una lista con 4 valores (Masculino, femenino, No binario, Prefiero no reportar)
GENEROS_VALIDOS = {
    "masculino": "Masculino",
    "femenino": "Femenino",
    "no binario": "No binario",
    "prefiero no reportar": "Prefiero no reportar",
}

REQUERIDOS = [
    "tipo_documento", "nro_documento", "primer_nombre", "apellidos",
    "fecha_nacimiento", "genero", "correo", "celular"
]

L = "A-Za-zÁÉÍÓÚÜÑáéíóúüñ"
NOMBRE_LETRAS_RE = re.compile(rf"^[{L}\s'\-]+$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MESES = {
    "ene": 1, "feb": 2, "mar": 3, "abr": 4, "may": 5, "jun": 6,
    "jul": 7, "ago": 8, "sep": 9, "set": 9, "oct": 10, "nov": 11, "dic": 12,
    "jan": 1, "apr": 4, "aug": 8, "dec": 12
}
MAX_FOTO = 2 * 1024 * 1024  # Máximo 2 MB
TIPOS_FOTO = {"image/png", "image/jpeg", "image/jpg", "image/pjpeg", "image/webp"}


def parse_fecha(valor: Optional[str]) -> Optional[date]:
    """Acepta yyyy-mm-dd (calendario) o dd-mmm-yyyy (texto, ej. 05-mar-2001)."""
    if not valor:
        return None
    valor = str(valor).strip()
    try:
        return date.fromisoformat(valor)
    except ValueError:
        pass
    m = re.fullmatch(r"(\d{1,2})-([A-Za-z]{3})-(\d{4})", valor)
    if m and m.group(2).lower() in MESES:
        try:
            return date(int(m.group(3)), MESES[m.group(2).lower()], int(m.group(1)))
        except ValueError:
            return None
    return None


def validar_documento(valor: Optional[str], permitir_asterisco: bool = False) -> str:
    if permitir_asterisco and valor == "*":
        return "*"
    if not re.fullmatch(r"[0-9]{1,10}", valor or ""):
        raise HTTPException(422, ["nro_documento: debe ser numérico y de máximo 10 dígitos"])
    return valor or ""


def validar_campo_nombre(campo: str, valor: Optional[str], maximo: int, obligatorio: bool = True) -> list[str]:
    errores = []
    if not valor:
        if obligatorio:
            errores.append(f"{campo}: es obligatorio")
        return errores

    if re.search(r"\d", valor):
        errores.append(f"{campo}: no debe contener números")
    if len(valor) > maximo:
        errores.append(f"{campo}: no debe superar {maximo} caracteres")
    if not NOMBRE_LETRAS_RE.fullmatch(valor):
        errores.append(f"{campo}: solo debe contener letras, espacios o guiones")
    return errores


def validar_persona(datos: dict, parcial: bool = False) -> dict:
    """Valida y normaliza según requerimientos de la prueba."""
    e, out = [], {}
    d = {k: (v.strip() if isinstance(v, str) else v) for k, v in datos.items()}

    if not parcial:
        e += [f"{k}: es obligatorio" for k in REQUERIDOS if not d.get(k)]

    # 1. Tipo de documento
    if v := d.get("tipo_documento"):
        v_norm = TIPOS_DOC_VALIDOS.get(str(v).lower())
        if not v_norm:
            e.append("tipo_documento: debe ser 'Tarjeta de identidad' o 'Cédula'")
        else:
            out["tipo_documento"] = v_norm

    # 2. Nro. Documento
    if v := d.get("nro_documento"):
        if not re.fullmatch(r"[0-9]{1,10}", str(v)):
            e.append("nro_documento: debe ser numérico y no mayor de 10 caracteres")
        out["nro_documento"] = str(v)

    # 3. Primer Nombre
    if "primer_nombre" in d or not parcial:
        errs = validar_campo_nombre("primer_nombre", d.get("primer_nombre"), 30, obligatorio=not parcial)
        e.extend(errs)
        if not errs and d.get("primer_nombre"):
            out["primer_nombre"] = d["primer_nombre"]

    # 4. Segundo Nombre (opcional)
    if d.get("segundo_nombre") is not None:
        v = d["segundo_nombre"]
        if v:
            errs = validar_campo_nombre("segundo_nombre", v, 30, obligatorio=False)
            e.extend(errs)
            out["segundo_nombre"] = v if not errs else None
        else:
            out["segundo_nombre"] = None

    # 5. Apellidos
    if "apellidos" in d or not parcial:
        errs = validar_campo_nombre("apellidos", d.get("apellidos"), 60, obligatorio=not parcial)
        e.extend(errs)
        if not errs and d.get("apellidos"):
            out["apellidos"] = d["apellidos"]

    # 6. Fecha de Nacimiento
    if v := d.get("fecha_nacimiento"):
        f = parse_fecha(str(v))
        if not f:
            e.append("fecha_nacimiento: use el calendario o el formato dd-mmm-yyyy")
        elif f > date.today():
            e.append("fecha_nacimiento: no puede ser una fecha futura")
        out["fecha_nacimiento"] = f

    # 7. Género
    if v := d.get("genero"):
        v_norm = GENEROS_VALIDOS.get(str(v).lower())
        if not v_norm:
            e.append("genero: debe ser uno de: Masculino, femenino, No binario, Prefiero no reportar")
        else:
            out["genero"] = v_norm

    # 8. Correo electrónico
    if v := d.get("correo"):
        v_str = str(v)
        if len(v_str) > 254 or not EMAIL_RE.fullmatch(v_str):
            e.append("correo: formato de correo electrónico inválido")
        out["correo"] = v_str

    # 9. Celular
    if v := d.get("celular"):
        v_str = str(v)
        if not re.fullmatch(r"[0-9]{10}", v_str):
            e.append("celular: debe ser numérico y de exactamente 10 caracteres")
        out["celular"] = v_str

    if e:
        raise HTTPException(422, e)
    return out


def leer_foto(foto: Optional[UploadFile]):
    """Devuelve (bytes, content_type) o (None, None). Máx. 2 MB."""
    if foto is None or not foto.filename:
        return None, None
    if foto.content_type and foto.content_type.lower() not in TIPOS_FOTO:
        raise HTTPException(422, ["foto: el formato debe ser PNG, JPG o WEBP"])
    contenido = foto.file.read(MAX_FOTO + 1)
    if len(contenido) > MAX_FOTO:
        raise HTTPException(422, ["foto: el tamaño del archivo no puede superar los 2 MB"])
    return contenido, foto.content_type or "image/jpeg"
