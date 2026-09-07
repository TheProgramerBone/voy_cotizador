# -*- coding: utf-8 -*-
"""Resuelve qué `TemplateDefinition` usar al exportar una cotización:
plantilla elegida explícitamente para esta exportación > predeterminada de
la cuenta > preset "Clásica". Punto único de esta lógica de fallback,
usado por el selector de la pestaña Cotización (`quotetrip/cotizacion_ui.py`)."""

from ..db import obtener_plantilla, obtener_plantillas
from .models import TemplateDefinition, validar_plantilla
from .presets import PRESET_POR_DEFECTO, es_preset, listar_presets, obtener_preset


def resolver_plantilla(cuenta: dict, id_elegido: str | None = None) -> TemplateDefinition:
    """`id_elegido`: id explícito (de un preset o de una plantilla
    personalizada) elegido en la UI para esta exportación, o `None` para
    usar la predeterminada de la cuenta. Nunca falla: si el id elegido o
    la predeterminada ya no existen (p.ej. una plantilla personalizada fue
    borrada en otra pestaña), cae al preset "Clásica" — degradación
    elegante en vez de romper la exportación."""
    id_ = id_elegido or (cuenta or {}).get("plantilla_predeterminada_id") or PRESET_POR_DEFECTO
    definicion = _cargar(id_)
    validar_plantilla(definicion)
    return definicion


def _cargar(id_: str) -> TemplateDefinition:
    if es_preset(id_):
        return obtener_preset(id_)
    fila = obtener_plantilla(id_)
    if fila:
        return TemplateDefinition.from_json(fila["definicion_json"])
    return obtener_preset(PRESET_POR_DEFECTO)


def listar_plantillas_disponibles(cuenta: dict) -> list[TemplateDefinition]:
    """Todas las plantillas que se pueden elegir para exportar: las
    preestablecidas + las personalizadas de la cuenta — usado para
    construir el selector en la pestaña Cotización. `cuenta` no se usa hoy
    (aislamiento es implícito, un archivo SQLite por instalación) pero se
    deja en la firma para que el llamador no tenga que cambiar si el
    filtrado alguna vez necesita depender de la cuenta."""
    definiciones = listar_presets()
    for fila in obtener_plantillas():
        definiciones.append(TemplateDefinition.from_json(fila["definicion_json"]))
    return definiciones
