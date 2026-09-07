# -*- coding: utf-8 -*-
"""Resuelve el `tema` de una `TemplateDefinition` (colores, fuente, tamaño
base) más los overrides de `estilo` por sección a los `ParagraphStyle` que
usan los renderers de sección (`quotetrip.pdf.engine.registry`).

Los tamaños/colores/pesos por defecto de cada sección están calibrados para
que, con el tema por defecto (`tamano_base_pt=10.5`, `fuente_id="helvetica"`,
colores heredados de la cuenta), el resultado sea visualmente idéntico al
antiguo motor `quotetrip/pdf/legacy.py` — eso es lo que exige el preset
"Clásica"."""

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import TableStyle

from .fonts import nombre_fuente

_ALINEACION_A_TA = {
    "izquierda": TA_LEFT,
    "centro": TA_CENTER,
    "derecha": TA_RIGHT,
}

GRIS_TEXTO = colors.HexColor("#555555")
GRIS_OSCURO = colors.HexColor("#333333")
GRIS_PIE = colors.HexColor("#444444")

# Un ParagraphStyle "primario" por tipo de sección (SECCION_TIPOS). Cuando
# una sección necesita más de un estilo visual (p.ej. "precios" con el
# total del grupo en un tono distinto, o "anexos" con título + captions),
# el renderer de esa sección deriva las variantes con `.clone(...)` a
# partir de este estilo primario — así el override del usuario (tamaño,
# color, alineación, peso) se propaga automáticamente a toda la sección en
# vez de tener que exponer un control independiente por cada matiz.
#
# offset:    puntos a sumar a tema.tamano_base_pt (calibrado sobre el
#            tamaño legado de cada sección con base=10.5, ver legacy.py).
# peso:      "normal" | "bold" — fuente a usar por defecto.
# color:     "primario" | "secundario" | "gris_texto" | None (negro).
# alineacion:"izquierda"|"centro"|"derecha"|"justificado"|None (usa
#            tema.alineacion_titulos).
# espacio_*: en puntos (igual unidad que ReportLab usa nativamente en
#            ParagraphStyle.spaceBefore/spaceAfter).
# leading_extra: puntos añadidos al leading por defecto (tamaño*1.2).
_DEFAULTS = {
    "fecha": dict(
        offset=0.5,
        peso="normal",
        color=None,
        alineacion="izquierda",
        espacio_antes=0,
        espacio_despues=6,
        leading_extra=0,
    ),
    "titulo": dict(
        offset=4.5,
        peso="bold",
        color="secundario",
        alineacion=None,
        espacio_antes=0,
        espacio_despues=4,
        leading_extra=3,
    ),
    "etiqueta_opcion": dict(
        offset=1.5,
        peso="bold",
        color="secundario",
        alineacion=None,
        espacio_antes=0,
        espacio_despues=4,
        leading_extra=0,
    ),
    "pasajeros": dict(
        offset=0.0,
        peso="normal",
        color="gris_texto",
        alineacion="centro",
        espacio_antes=0,
        espacio_despues=2,
        leading_extra=0,
    ),
    "hotel_fechas": dict(
        offset=0.0,
        peso="normal",
        color="gris_texto",
        alineacion="centro",
        espacio_antes=0,
        espacio_despues=2,
        leading_extra=0,
    ),
    "precios": dict(
        offset=2.5,
        peso="bold",
        color=None,
        alineacion="centro",
        espacio_antes=8,
        espacio_despues=4,
        leading_extra=0,
    ),
    "servicios": dict(
        offset=0.5,
        peso="normal",
        color=None,
        alineacion="centro",
        espacio_antes=0,
        espacio_despues=10,
        leading_extra=4,
    ),
    "nota_legal": dict(
        offset=-1.0,
        peso="normal",
        color=None,
        alineacion="justificado",
        espacio_antes=0,
        espacio_despues=14,
        leading_extra=4.5,
    ),
    "firma": dict(
        offset=0.5,
        peso="normal",
        color=None,
        alineacion="izquierda",
        espacio_antes=0,
        espacio_despues=0,
        leading_extra=4,
    ),
    "anexos": dict(
        offset=0.5,
        peso="bold",
        color="secundario",
        alineacion="centro",
        espacio_antes=6,
        espacio_despues=8,
        leading_extra=0,
    ),
}


def _color_de(clave, color_primario_hex, color_secundario_hex):
    if clave == "primario":
        return colors.HexColor(color_primario_hex)
    if clave == "secundario":
        return colors.HexColor(color_secundario_hex)
    if clave == "gris_texto":
        return GRIS_TEXTO
    return colors.black


def construir_estilos(template, glob: dict) -> dict[str, ParagraphStyle]:
    """Devuelve {tipo_de_seccion: ParagraphStyle} — un estilo "primario"
    por cada tipo en SECCION_TIPOS, ya resuelto con el tema de `template` y
    los colores de `glob` (heredados si el tema de la plantilla no fija los
    suyos propios, p.ej. el preset "Premium" sí trae paleta fija)."""
    tema = template.tema
    color_primario = tema.color_primario or glob["color_primario"]
    color_secundario = tema.color_secundario or glob["color_secundario"]
    overrides = {s.tipo: s.estilo for s in template.secciones}

    estilos: dict[str, ParagraphStyle] = {}
    for tipo, cfg in _DEFAULTS.items():
        tamano = tema.tamano_base_pt + cfg["offset"]
        peso = cfg["peso"]
        alineacion_txt = cfg["alineacion"] or tema.alineacion_titulos
        color = (
            _color_de(cfg["color"], color_primario, color_secundario)
            if cfg["color"]
            else colors.black
        )
        espacio_antes = cfg["espacio_antes"]
        espacio_despues = cfg["espacio_despues"]

        override = overrides.get(tipo)
        if override:
            if override.tamano_pt is not None:
                tamano = override.tamano_pt
            if override.alineacion is not None:
                alineacion_txt = override.alineacion
            if override.color is not None:
                color = colors.HexColor(override.color)
            if override.peso is not None:
                peso = override.peso
            if override.espacio_antes_cm is not None:
                espacio_antes = override.espacio_antes_cm * cm
            if override.espacio_despues_cm is not None:
                espacio_despues = override.espacio_despues_cm * cm

        alineacion = _ALINEACION_A_TA.get(
            alineacion_txt, TA_JUSTIFY if alineacion_txt == "justificado" else TA_CENTER
        )
        fuente = nombre_fuente(tema.fuente_id, "bold" if peso == "bold" else "normal")

        estilos[tipo] = ParagraphStyle(
            f"qt_{tipo}",
            fontName=fuente,
            fontSize=tamano,
            leading=tamano * 1.2 + cfg["leading_extra"],
            alignment=alineacion,
            textColor=color,
            spaceBefore=espacio_antes,
            spaceAfter=espacio_despues,
        )

    # Estilo itálico auxiliar (captions de anexos) — se deriva del de
    # "anexos" pero en la fuente itálica del catálogo, más pequeño y gris,
    # igual que el `est_caption` del motor legado.
    anexos = estilos["anexos"]
    estilos["anexos_caption"] = anexos.clone(
        "qt_anexos_caption",
        fontName=nombre_fuente(tema.fuente_id, "italica"),
        fontSize=max(tema.tamano_base_pt - 1.0, 6.0),
        textColor=GRIS_TEXTO,
        spaceBefore=6,
        spaceAfter=4,
    )

    # Estilo auxiliar para el total del grupo (varios pasajeros), dentro de
    # la sección "precios" — equivalente al `est_valor2` del motor legado.
    # No es una entrada de SECCION_TIPOS propia (no tiene sentido ocultarla
    # por separado de "precios"), así que no tiene su propio override —
    # pero SÍ hereda la alineación ya resuelta de "precios" (incluyendo su
    # override, si lo hay), para no quedar centrado por accidente en un
    # tema/plantilla que alinea todo a la izquierda o la derecha.
    tamano_grupo = tema.tamano_base_pt + 0.5
    estilos["precios_grupo"] = estilos["precios"].clone(
        "qt_precios_grupo",
        fontSize=tamano_grupo,
        leading=tamano_grupo * 1.2,
        textColor=colors.HexColor(color_secundario),
        spaceBefore=0,
        spaceAfter=4,
    )

    return estilos


def construir_tabla_servicios_style(color_primario_hex: str) -> TableStyle:
    """Estilo de tabla para la sección "servicios" en modo `layout: "table"`
    (usado por presets como "Profesional"): encabezado con el color
    primario, líneas finas, alineación de precios a la derecha."""
    c_prim = colors.HexColor(color_primario_hex)
    return TableStyle(
        [
            ("BACKGROUND", (0, 0), (-1, 0), c_prim),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 9.5),
            ("ALIGN", (-1, 0), (-1, -1), "RIGHT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#DDDDDD")),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ]
    )
