# -*- coding: utf-8 -*-
"""Acceso a la BD SQLite local: historial de cotizaciones + cuenta (una sola
fila por instalación) con las credenciales de acceso hasheadas."""

import hashlib
import re
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime

from .config import DB_PATH

_ITERACIONES_HASH = 200_000


@contextmanager
def _conectar():
    """Conexión SQLite que además de manejar commit/rollback, se CIERRA al salir.
    `with sqlite3.connect(...) as con:` por sí solo NO cierra la conexión (el
    context manager nativo de sqlite3 solo gestiona la transacción), así que
    cada llamada dejaba un handle de archivo abierto hasta que el GC lo
    recogiera. En Windows eso puede derivar en bloqueos tipo "database is
    locked" si hay varias conexiones sueltas."""
    con = sqlite3.connect(DB_PATH)
    try:
        with con:
            yield con
    finally:
        con.close()


# ----------------------------------------------------------------------
# Esquema
# ----------------------------------------------------------------------
def init_db():
    with _conectar() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cotizaciones (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente       TEXT,
                fecha_cotiz   TEXT,
                num_opciones  INTEGER,
                hoteles       TEXT,
                valor_desde   INTEGER,
                creado_en     TEXT
            )
            """
        )
    _asegurar_columnas()
    _asegurar_tabla_cuenta()


def _asegurar_columnas():
    """Migración: agrega columnas nuevas si la BD ya existía con otro esquema."""
    nuevas = [
        ("num_opciones", "INTEGER"),
        ("hoteles", "TEXT"),
        ("valor_desde", "INTEGER"),
        # Snapshot completo (JSON) de la cotización, para poder recargarla y
        # editarla/recotizar desde el historial. Las filas guardadas antes de
        # esto quedan en NULL — se muestran como "no editables" en la UI.
        ("datos_json", "TEXT"),
    ]
    with _conectar() as con:
        existentes = {r[1] for r in con.execute("PRAGMA table_info(cotizaciones)")}
        for col, tipo in nuevas:
            if col not in existentes:
                con.execute(f"ALTER TABLE cotizaciones ADD COLUMN {col} {tipo}")


def _asegurar_tabla_cuenta():
    with _conectar() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cuenta (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                razon_social        TEXT,
                nit                 TEXT,
                rnt                 TEXT,
                ciudad              TEXT,
                telefonos           TEXT,
                contacto            TEXT,
                logo_path           TEXT,
                color_primario      TEXT,
                color_secundario    TEXT,
                firma_nombre        TEXT,
                firma_cargo         TEXT,
                usuario             TEXT,
                hash_password       TEXT,
                salt_password       TEXT,
                pregunta_seguridad  TEXT,
                hash_respuesta      TEXT,
                salt_respuesta      TEXT,
                hash_codigo_recup   TEXT,
                salt_codigo_recup   TEXT,
                tutorial_visto      INTEGER DEFAULT 0,
                sesion_recordada    INTEGER DEFAULT 0,
                creado_en           TEXT
            )
            """
        )
    _asegurar_columnas_cuenta()


def _asegurar_columnas_cuenta():
    """Migración: agrega columnas nuevas a `cuenta` si ya existía sin ellas
    (mismo patrón que `_asegurar_columnas` para `cotizaciones`)."""
    nuevas = [("sesion_recordada", "INTEGER DEFAULT 0")]
    with _conectar() as con:
        existentes = {r[1] for r in con.execute("PRAGMA table_info(cuenta)")}
        for col, tipo in nuevas:
            if col not in existentes:
                con.execute(f"ALTER TABLE cuenta ADD COLUMN {col} {tipo}")


# ----------------------------------------------------------------------
# Historial de cotizaciones
# ----------------------------------------------------------------------
def guardar_cotizacion(cliente, fecha_txt, num_opciones, hoteles, valor_desde, datos_json=None):
    with _conectar() as con:
        con.execute(
            """INSERT INTO cotizaciones
                   (cliente, fecha_cotiz, num_opciones, hoteles, valor_desde, creado_en, datos_json)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                cliente,
                fecha_txt,
                int(num_opciones),
                hoteles,
                int(valor_desde),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                datos_json,
            ),
        )


def obtener_historial():
    with _conectar() as con:
        con.row_factory = sqlite3.Row
        filas = con.execute("SELECT * FROM cotizaciones ORDER BY id DESC").fetchall()
    return [dict(f) for f in filas]


def borrar_historial():
    with _conectar() as con:
        con.execute("DELETE FROM cotizaciones")


# ----------------------------------------------------------------------
# Hash de contraseña / respuesta de seguridad / código de recuperación
# ----------------------------------------------------------------------
def hash_secreto(texto: str, salt: bytes | None = None) -> tuple[str, str]:
    """PBKDF2-HMAC-SHA256 con sal aleatoria. Devuelve (hash_hex, salt_hex)."""
    if salt is None:
        salt = secrets.token_bytes(16)
    texto_norm = (texto or "").strip()
    h = hashlib.pbkdf2_hmac("sha256", texto_norm.encode("utf-8"), salt, _ITERACIONES_HASH)
    return h.hex(), salt.hex()


def _verificar(hash_guardado, salt_guardado, intento) -> bool:
    if not hash_guardado or not salt_guardado:
        return False
    h, _ = hash_secreto(intento, salt=bytes.fromhex(salt_guardado))
    return secrets.compare_digest(h, hash_guardado)


def generar_codigo_recuperacion() -> str:
    """Código legible de una sola vez, tipo 'A1B2-C3D4-E5F6'."""
    crudo = secrets.token_hex(6).upper()  # 12 caracteres hex
    return "-".join(crudo[i : i + 4] for i in range(0, 12, 4))


def verificar_password(cuenta: dict, intento: str) -> bool:
    return _verificar(cuenta.get("hash_password"), cuenta.get("salt_password"), intento)


def verificar_respuesta_seguridad(cuenta: dict, intento: str) -> bool:
    return _verificar(
        cuenta.get("hash_respuesta"), cuenta.get("salt_respuesta"), (intento or "").strip().lower()
    )


def verificar_codigo_recuperacion(cuenta: dict, intento: str) -> bool:
    limpio = re.sub(r"[\s-]", "", (intento or "")).upper()
    return _verificar(cuenta.get("hash_codigo_recup"), cuenta.get("salt_codigo_recup"), limpio)


# ----------------------------------------------------------------------
# Cuenta (una sola fila por instalación)
# ----------------------------------------------------------------------
def obtener_cuenta() -> dict | None:
    with _conectar() as con:
        con.row_factory = sqlite3.Row
        fila = con.execute("SELECT * FROM cuenta ORDER BY id LIMIT 1").fetchone()
    return dict(fila) if fila else None


def crear_cuenta(datos: dict):
    """`datos` ya trae los campos hasheados listos para guardar."""
    with _conectar() as con:
        con.execute(
            """INSERT INTO cuenta (
                   razon_social, nit, rnt, ciudad, telefonos, contacto, logo_path,
                   color_primario, color_secundario, firma_nombre, firma_cargo,
                   usuario, hash_password, salt_password, pregunta_seguridad,
                   hash_respuesta, salt_respuesta, hash_codigo_recup, salt_codigo_recup,
                   tutorial_visto, creado_en
               ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                datos["razon_social"],
                datos["nit"],
                datos.get("rnt", ""),
                datos["ciudad"],
                datos["telefonos"],
                datos["contacto"],
                datos.get("logo_path"),
                datos["color_primario"],
                datos["color_secundario"],
                datos["firma_nombre"],
                datos["firma_cargo"],
                datos["usuario"],
                datos["hash_password"],
                datos["salt_password"],
                datos["pregunta_seguridad"],
                datos["hash_respuesta"],
                datos["salt_respuesta"],
                datos["hash_codigo_recup"],
                datos["salt_codigo_recup"],
                0,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )


def actualizar_cuenta(campos: dict):
    """Actualiza solo las columnas presentes en `campos` de la única fila de
    cuenta. Las claves de `campos` siempre vienen de nuestro propio código
    (nunca de texto libre del usuario), así que el nombre de columna
    interpolado es seguro."""
    if not campos:
        return
    columnas = ", ".join(f"{c} = ?" for c in campos)
    with _conectar() as con:
        con.execute(
            f"UPDATE cuenta SET {columnas} WHERE id = (SELECT id FROM cuenta ORDER BY id LIMIT 1)",
            list(campos.values()),
        )
