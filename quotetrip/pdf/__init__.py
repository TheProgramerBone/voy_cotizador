# -*- coding: utf-8 -*-
"""Generación del PDF de la cotización — paquete del motor de plantillas de
QuoteTrip.

- `construir.py`  — punto de entrada público (`construir_pdf`).
- `legacy.py`      — motor de render original (diseño "Clásica"), de baja
                      hasta que el motor de plantillas (Fase 2) lo sustituya.
- `images.py`      — utilidades de imagen compartidas (logo, adjuntos).

El resto de QuoteTrip solo debe importar desde este paquete
(`from quotetrip.pdf import construir_pdf, guardar_logo_cuenta`), nunca de
sus submódulos internos."""

from .construir import construir_pdf
from .images import guardar_logo_cuenta

__all__ = ["construir_pdf", "guardar_logo_cuenta"]
