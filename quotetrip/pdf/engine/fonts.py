# -*- coding: utf-8 -*-
"""Resuelve el `fuente_id` de una plantilla (catálogo controlado, ver
`quotetrip.pdf.models.template.FUENTES_CATALOGO`) a los nombres de fuente
Base-14 que ReportLab entiende directamente sin registro previo.

Sin fuentes TTF personalizadas en v1 — cero riesgo de licencia/empaquetado
y hoy no hay ninguna fuente registrada en todo el proyecto
(`pdfmetrics.registerFont` no se usa en ningún sitio). Si en el futuro se
añaden fuentes propias, este es el punto de extensión: registrar cada
variante con `reportlab.pdfbase.pdfmetrics.registerFont(TTFont(...))` desde
un archivo empaquetado bajo `quotetrip/pdf/engine/fonts/` (así viaja con el
resto del paquete `quotetrip/` sin tocar `QuoteTrip.spec`) y añadir la
entrada correspondiente a `FUENTES_CATALOGO`."""

from ..models.template import FUENTE_POR_DEFECTO, FUENTES_CATALOGO


def nombre_fuente(fuente_id: str, variante: str = "normal") -> str:
    """`variante`: "normal" | "bold" | "italica". Si `fuente_id` no está en
    el catálogo (JSON corrupto/futuro), cae a la fuente por defecto en vez
    de fallar — `validar_plantilla()` ya debería haber corregido esto antes
    de llegar aquí, esta es la última red de seguridad."""
    catalogo = FUENTES_CATALOGO.get(fuente_id) or FUENTES_CATALOGO[FUENTE_POR_DEFECTO]
    return catalogo.get(variante, catalogo["normal"])
