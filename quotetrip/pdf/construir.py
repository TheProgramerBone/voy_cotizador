# -*- coding: utf-8 -*-
"""Punto de entrada público para generar el PDF de una cotización.

`construir_pdf(glob, opciones, template=None)` mantiene la firma histórica:
sin `template` (como lo llama todo el código anterior a la Fase 5 del
sistema de plantillas) se usa el preset "Clásica", que reproduce
fielmente el diseño original de QuoteTrip — verificado en la Fase 2 del
plan de plantillas comparando texto extraído + número de páginas contra el
antiguo motor `legacy.py` (ya retirado) para varios fixtures representativos
(1 opción, varias opciones, tarifa de menor diferenciada, con imágenes)."""

from .engine.renderer import renderizar_plantilla
from .presets import obtener_preset


def construir_pdf(glob: dict, opciones: list, template=None) -> bytes:
    """Genera el PDF de la cotización.

    `template`: instancia de `TemplateDefinition` (ver
    `quotetrip.pdf.models.template`), ya validada con
    `quotetrip.pdf.models.validar_plantilla`, o `None` para el preset
    "Clásica" por defecto."""
    if template is None:
        template = obtener_preset("clasica")
    return renderizar_plantilla(template, glob, opciones)
