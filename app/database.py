import os
import ssl
from contextlib import contextmanager
from pathlib import Path

import certifi
import pymysql
from dotenv import load_dotenv
from pymysql.cursors import DictCursor

load_dotenv()

RAIZ_DO_PROJETO = Path(__file__).resolve().parent.parent


def contexto_ssl():
    """SSL é obrigatório em bancos na nuvem (Aiven, TiDB...). Localmente fica desligado.

    DB_SSL=true             -> liga o SSL usando os certificados públicos (certifi)
    DB_SSL_CA=certs/ca.pem  -> usa o certificado do provedor (caminho a partir da raiz do projeto)
    """
    ca = os.getenv("DB_SSL_CA")
    if ca:
        return ssl.create_default_context(cafile=str(RAIZ_DO_PROJETO / ca))
    if os.getenv("DB_SSL", "").lower() in ("1", "true", "sim"):
        return ssl.create_default_context(cafile=certifi.where())
    return None


def get_connection():
    return pymysql.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME"),
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=False,
        ssl=contexto_ssl(),
        connect_timeout=10,
    )


@contextmanager
def get_cursor(commit: bool = False):
    """Abre conexão, entrega um cursor e garante commit/rollback/fechamento."""
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
