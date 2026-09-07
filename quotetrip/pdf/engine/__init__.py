# -*- coding: utf-8 -*-
"""Motor de render: interpreta una `TemplateDefinition`
(`quotetrip.pdf.models`) sobre los datos de una cotización (`glob` +
`opciones`, igual forma que siempre) y produce el PDF final con ReportLab
Platypus. Punto de entrada: `renderizar_plantilla` en `renderer.py`."""

from .renderer import renderizar_plantilla

__all__ = ["renderizar_plantilla"]
