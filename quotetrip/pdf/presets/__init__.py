# -*- coding: utf-8 -*-
"""Carga las plantillas preestablecidas ("presets") de QuoteTrip: viven
como JSON en este mismo paquete (`quotetrip/pdf/presets/*.json`), viajan
empaquetadas junto con el resto de `quotetrip/` sin necesitar ninguna
entrada extra en `QuoteTrip.spec`, y nunca se guardan como fila en la
tabla `plantillas` — son de solo lectura, iguales para toda instalación."""

import json
from pathlib import Path

from ..models.template import TemplateDefinition, validar_plantilla

_DIR = Path(__file__).parent
_IDS = ("clasica", "profesional", "minimalista", "premium", "travel")
PRESET_POR_DEFECTO = "clasica"

_cache: dict[str, TemplateDefinition] = {}


def _cargar(id_: str) -> TemplateDefinition:
    ruta = _DIR / f"{id_}.json"
    data = json.loads(ruta.read_text(encoding="utf-8"))
    template = TemplateDefinition.from_dict(data)
    validar_plantilla(template)
    return template


def obtener_preset(id_: str) -> TemplateDefinition:
    """Devuelve una COPIA de la plantilla preestablecida `id_` — nunca la
    instancia cacheada directamente, así el llamador puede mutarla (p.ej.
    al duplicarla) sin afectar al preset original ni a otras llamadas. Si
    `id_` no existe, cae al preset por defecto ("Clásica") en vez de
    fallar — degradación elegante."""
    real_id = id_ if id_ in _IDS else PRESET_POR_DEFECTO
    if real_id not in _cache:
        _cache[real_id] = _cargar(real_id)
    return TemplateDefinition.from_dict(_cache[real_id].to_dict())


def listar_presets() -> list[TemplateDefinition]:
    return [obtener_preset(id_) for id_ in _IDS]


def es_preset(id_: str) -> bool:
    return id_ in _IDS
