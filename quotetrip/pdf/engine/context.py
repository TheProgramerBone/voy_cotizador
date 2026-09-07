# -*- coding: utf-8 -*-
"""`RenderContext`: agrupa los datos que necesita cada función de sección
del catálogo de componentes (`quotetrip.pdf.engine.registry`), para no
repetir media docena de parámetros en cada firma."""

from dataclasses import dataclass


@dataclass
class RenderContext:
    glob: dict
    op: dict
    estilos: dict  # {tipo_de_sección: ParagraphStyle}, ver engine/styles.py
    fuente_id: str
    color_primario: str
    color_secundario: str
    ancho_util: float
    varias: bool  # True si la cotización tiene más de una opción
    indice: int  # índice de `op` dentro de la lista de opciones
    tmpdir: str  # carpeta temporal compartida para las imágenes de anexos
