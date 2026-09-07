# -*- coding: utf-8 -*-
"""Utilidades de imagen (Streamlit UploadedFile -> archivo compatible con
ReportLab): normalización a PNG RGB, archivos temporales y el logo fijo de
la cuenta. Movido tal cual desde el antiguo `quotetrip/pdf.py` (Fase 0 del
sistema de plantillas) — sin cambios de comportamiento."""

import io
import os
import tempfile
from pathlib import Path

from PIL import Image
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Image as RLImage


def _a_png_rgb(raw_bytes: bytes) -> Image.Image:
    """Convierte bytes de imagen a un Image PIL en RGB con fondo blanco
    (si tenía transparencia)."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fondo.paste(img, (0, 0), img)
        return fondo.convert("RGB")
    return img.convert("RGB")


def preparar_imagen(raw_bytes: bytes, carpeta_tmp: str) -> str:
    """Guarda la imagen como PNG RGB en un archivo temporal y devuelve la ruta."""
    fd, ruta = tempfile.mkstemp(suffix=".png", dir=carpeta_tmp)
    os.close(fd)
    _a_png_rgb(raw_bytes).save(ruta, format="PNG")
    return ruta


def guardar_logo_cuenta(raw_bytes: bytes, destino: Path) -> str:
    """Guarda el logo de una cuenta en una ruta fija (se sobreescribe si ya
    existía). A diferencia de `preparar_imagen`, no es temporal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    _a_png_rgb(raw_bytes).save(destino, format="PNG")
    return str(destino)


def _imagen_flowable(ruta: str, ancho_max: float, alto_max: float = 19 * cm) -> RLImage:
    """Imagen ReportLab escalada proporcionalmente al ancho útil."""
    iw, ih = ImageReader(ruta).getSize()
    ratio = iw / ih if ih else 1
    ancho, alto = ancho_max, ancho_max / ratio
    if alto > alto_max:
        alto, ancho = alto_max, alto_max * ratio
    return RLImage(ruta, width=ancho, height=alto)
