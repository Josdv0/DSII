from __future__ import annotations
import os
from contextlib import contextmanager
from typing import Generator, Any

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    try:
        import psycopg as psycopg2
        from psycopg.rows import dict_row as RealDictCursor
    except ImportError:
        psycopg2 = None
        RealDictCursor = None


@contextmanager
def cursor() -> Generator[Any, None, None]:
    """Conexión + cursor con commit/rollback automático (la transacción incluye el log)."""
    if psycopg2 is None:
        raise RuntimeError("No se encontró el controlador de base de datos (psycopg2 o psycopg)")

    conn = psycopg2.connect(
        host=os.getenv("DB_HOST", "db"),
        port=os.getenv("DB_PORT", "5432"),
        dbname=os.getenv("DB_NAME", "personas_db"),
        user=os.getenv("DB_USER", "app"),
        password=os.getenv("DB_PASSWORD", "app_pass"),
    )
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def registrar_log(cur: Any, tipo: str, documento: str, usuario: str, detalle: str = "") -> None:
    cur.execute(
        "INSERT INTO logs (tipo_transaccion, documento, usuario, detalle) VALUES (%s,%s,%s,%s)",
        (tipo, documento, usuario, detalle),
    )
