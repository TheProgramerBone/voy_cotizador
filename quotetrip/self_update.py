# -*- coding: utf-8 -*-
"""
Actualización incremental ("parche"): descarga un .zip liviano con solo
app.py + quotetrip/ + assets/ (nada de Python/Streamlit/reportlab, que no
cambian entre versiones normales) y lo deja preparado para que desktop.py lo
aplique en el próximo arranque, sin pasar por el instalador completo.

Ver "README Actualizaciones.md" para el flujo completo y cómo generar el
.zip al publicar una versión.
"""

import hashlib
import io
import json
import shutil
import urllib.request
import zipfile

from .config import DATA_DIR, logger

STAGING_DIR = DATA_DIR / "update_staging"
STAGING_MARKER = DATA_DIR / "update_staging.json"
CAPABILITIES_MARKER = DATA_DIR / "desktop_capabilities.json"

# Debe coincidir con CAPACIDAD_PARCHE mínima que desktop.py necesita tener
# para saber aplicar el parche que describe version.json (ver desktop.py).
CAPACIDAD_PARCHE_REQUERIDA = 1


def desktop_soporta_parches() -> bool:
    """True si el desktop.py compilado en el .exe instalado ya sabe aplicar
    parches. desktop.py deja un marker con su CAPACIDAD_PARCHE justo antes de
    arrancar el servidor; un exe de antes de que existiera este mecanismo
    (o instalado directamente desde el instalador completo más reciente que
    subió esa capacidad) nunca lo escribe o lo escribe con un número menor,
    así que devolvemos False y quien llama debe ofrecer el instalador
    completo en vez de un parche que nunca se aplicaría. Nunca lanza
    excepción."""
    if not CAPABILITIES_MARKER.exists():
        return False
    try:
        info = json.loads(CAPABILITIES_MARKER.read_text(encoding="utf-8"))
        return int(info.get("capacidad_parche", 0)) >= CAPACIDAD_PARCHE_REQUERIDA
    except Exception:
        return False


def estado_parche_pendiente() -> dict | None:
    """Si ya hay un parche descargado y listo para aplicarse al reiniciar,
    devuelve su info ({"version": ...}); si no, None."""
    if not STAGING_MARKER.exists():
        return None
    try:
        info = json.loads(STAGING_MARKER.read_text(encoding="utf-8"))
        return info if info.get("listo") else None
    except Exception:
        return None


def preparar_parche(info_version: dict, timeout: int = 30) -> str | None:
    """Descarga el .zip de `info_version['url']`, verifica su sha256
    (`info_version['sha256']`, si viene) y lo deja extraído en la carpeta de
    staging. Devuelve None si quedó listo, o un mensaje de error si algo
    falló (nunca lanza excepción)."""
    url = info_version.get("url")
    if not url:
        return "El aviso de actualización no trae URL de descarga."

    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            contenido = r.read()
    except Exception as e:
        logger.info("Descarga de parche falló: %s", e)
        return f"No se pudo descargar la actualización: {e}"

    sha_esperado = str(info_version.get("sha256") or "").lower().strip()
    if sha_esperado:
        real = hashlib.sha256(contenido).hexdigest()
        if real != sha_esperado:
            logger.info("sha256 de parche no coincide: esperado=%s real=%s", sha_esperado, real)
            return "El archivo descargado no coincide con lo esperado; no se aplicó."

    try:
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR)
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(contenido)) as z:
            z.extractall(STAGING_DIR)
    except Exception as e:
        logger.info("No se pudo preparar el parche: %s", e)
        shutil.rmtree(STAGING_DIR, ignore_errors=True)
        return f"No se pudo preparar la actualización: {e}"

    STAGING_MARKER.write_text(
        json.dumps({"version": info_version.get("version"), "listo": True}),
        encoding="utf-8",
    )
    return None
