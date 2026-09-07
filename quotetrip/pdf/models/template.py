# -*- coding: utf-8 -*-
"""Modelo de datos declarativo para las plantillas de PDF de QuoteTrip.

Una `TemplateDefinition` es 100% serializable a JSON y nunca contiene
código ejecutable (ni `eval`/`exec` en ningún punto del sistema de
plantillas). El motor de render (`quotetrip.pdf.engine`) la interpreta
para producir el PDF; el editor visual (`quotetrip.plantillas_ui`) la
construye y valida antes de guardar.

Las plantillas preestablecidas ("presets") viven como JSON en
`quotetrip/pdf/presets/*.json` y se cargan con `tipo="preset"`; las
plantillas personalizadas de una cuenta se guardan en la tabla SQLite
`plantillas` (ver `quotetrip/db.py`) con `tipo="custom"`.
"""

import dataclasses
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime

SCHEMA_VERSION = 1

# ----------------------------------------------------------------------
# Catálogos controlados — nunca se aceptan valores fuera de estas listas.
# ----------------------------------------------------------------------
SECCION_TIPOS = (
    "fecha",
    "titulo",
    "etiqueta_opcion",
    "pasajeros",
    "hotel_fechas",
    "precios",
    "servicios",
    "nota_legal",
    "firma",
    "anexos",
)

# Secciones que nunca pueden guardarse/renderizarse como ocultas: quitarlas
# produciría una cotización incompleta o, en el caso de `nota_legal`, un
# documento sin la cláusula exigida por la ley 679/2001 (Colombia). Esto es
# una constante de código a propósito — nunca un flag dentro del JSON de la
# plantilla, así un JSON manipulado a mano no puede desactivarlas.
SECCIONES_BLOQUEADAS = frozenset({"titulo", "precios", "servicios", "nota_legal"})

# Catálogo de fuentes: solo Base-14 de ReportLab en v1 (cero riesgo de
# licencia/empaquetado — ver notas de la Fase 2 del plan). Punto de
# extensión documentado para fuentes TTF empaquetadas en el futuro.
FUENTES_CATALOGO = {
    "helvetica": {
        "normal": "Helvetica",
        "bold": "Helvetica-Bold",
        "italica": "Helvetica-Oblique",
        "etiqueta": "Sans (Helvetica)",
    },
    "times": {
        "normal": "Times-Roman",
        "bold": "Times-Bold",
        "italica": "Times-Italic",
        "etiqueta": "Serif (Times)",
    },
    "courier": {
        "normal": "Courier",
        "bold": "Courier-Bold",
        "italica": "Courier-Oblique",
        "etiqueta": "Monoespaciada (Courier)",
    },
}
FUENTE_POR_DEFECTO = "helvetica"

TAMANOS_PAGINA = ("A4", "Carta")
ORIENTACIONES = ("vertical", "horizontal")
POSICIONES_LOGO = ("izquierda", "centro", "derecha")
ALINEACIONES = ("izquierda", "centro", "derecha")
PESOS = ("normal", "bold")
LAYOUTS_SERVICIOS = ("text", "table")

# Rangos seguros para validar_plantilla().
MARGEN_MIN_CM, MARGEN_MAX_CM = 1.0, 5.0
TAMANO_FUENTE_MIN_PT, TAMANO_FUENTE_MAX_PT = 6.0, 24.0
LOGO_ALTO_MIN_CM, LOGO_ALTO_MAX_CM = 0.8, 5.0


def _hex_valido(valor) -> bool:
    if not isinstance(valor, str):
        return False
    s = valor.strip()
    if not s.startswith("#") or len(s) != 7:
        return False
    try:
        int(s[1:], 16)
        return True
    except ValueError:
        return False


def _construir(cls, data: dict | None):
    """Instancia `cls` (un dataclass) a partir de `data`, ignorando
    silenciosamente claves desconocidas — así un JSON de una versión
    futura/antigua del esquema no revienta al deserializar."""
    campos = {f.name for f in dataclasses.fields(cls)}
    return cls(**{k: v for k, v in (data or {}).items() if k in campos})


# ----------------------------------------------------------------------
# Dataclasses
# ----------------------------------------------------------------------
@dataclass
class PaginaConfig:
    tamano: str = "A4"
    orientacion: str = "vertical"
    margen_sup_cm: float = 3.1
    margen_inf_cm: float = 2.9
    margen_izq_cm: float = 2.2
    margen_der_cm: float = 2.2


@dataclass
class TemaConfig:
    color_primario: str | None = None  # None = heredar el de la cuenta
    color_secundario: str | None = None  # None = heredar el de la cuenta
    fuente_id: str = FUENTE_POR_DEFECTO
    tamano_base_pt: float = 10.5
    peso_titulos: str = "bold"
    alineacion_titulos: str = "centro"


@dataclass
class EncabezadoConfig:
    mostrar_logo: bool = True
    logo_alto_cm: float = 2.0
    logo_posicion: str = "izquierda"
    lineas_derecha: list[str] = field(default_factory=lambda: ["razon_social", "nit", "rnt"])
    mostrar_linea_separadora: bool = True


@dataclass
class PieConfig:
    lineas: list[str] = field(default_factory=lambda: ["ciudad", "telefonos", "contacto"])
    mostrar_linea_separadora: bool = True


@dataclass
class EstiloSeccion:
    """Override opcional de estilo para una sección concreta. Todos los
    campos `None` significan "heredar del tema"."""

    tamano_pt: float | None = None
    alineacion: str | None = None
    color: str | None = None
    peso: str | None = None
    espacio_antes_cm: float | None = None
    espacio_despues_cm: float | None = None


@dataclass
class SeccionConfig:
    tipo: str
    visible: bool = True
    estilo: EstiloSeccion = field(default_factory=EstiloSeccion)
    # Configuración específica del tipo de sección (p.ej. para "servicios":
    # {"layout": "text"|"table", "mostrar_comision": bool, "mostrar_base": bool}).
    opciones: dict = field(default_factory=dict)


@dataclass
class TemplateDefinition:
    id: str
    nombre: str
    tipo: str  # "preset" | "custom"
    base_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    pagina: PaginaConfig = field(default_factory=PaginaConfig)
    tema: TemaConfig = field(default_factory=TemaConfig)
    encabezado: EncabezadoConfig = field(default_factory=EncabezadoConfig)
    pie: PieConfig = field(default_factory=PieConfig)
    secciones: list[SeccionConfig] = field(default_factory=list)
    creado_en: str | None = None
    actualizado_en: str | None = None

    # -- Serialización --
    def to_dict(self) -> dict:
        return dataclasses.asdict(self)

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: dict) -> "TemplateDefinition":
        data = migrar_definicion(dict(data))
        secciones = [
            SeccionConfig(
                tipo=s.get("tipo", ""),
                visible=bool(s.get("visible", True)),
                estilo=_construir(EstiloSeccion, s.get("estilo")),
                opciones=dict(s.get("opciones") or {}),
            )
            for s in data.get("secciones", [])
        ]
        return cls(
            id=data["id"],
            nombre=data.get("nombre", ""),
            tipo=data.get("tipo", "custom"),
            base_id=data.get("base_id"),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
            pagina=_construir(PaginaConfig, data.get("pagina")),
            tema=_construir(TemaConfig, data.get("tema")),
            encabezado=_construir(EncabezadoConfig, data.get("encabezado")),
            pie=_construir(PieConfig, data.get("pie")),
            secciones=secciones,
            creado_en=data.get("creado_en"),
            actualizado_en=data.get("actualizado_en"),
        )

    @classmethod
    def from_json(cls, texto: str) -> "TemplateDefinition":
        return cls.from_dict(json.loads(texto))

    # -- Duplicación --
    def clonar(self, nuevo_nombre: str) -> "TemplateDefinition":
        """Duplica esta plantilla como una nueva plantilla `custom`,
        completamente desacoplada del original: es una copia profunda de
        los datos, no una referencia. Si más adelante se actualiza el
        preset/plantilla original, esta copia NO cambia. `base_id` queda
        apuntando al id del original solo como dato informativo de
        procedencia (nunca una referencia viva/FK)."""
        data = self.to_dict()
        data["id"] = uuid.uuid4().hex
        data["nombre"] = nuevo_nombre
        data["tipo"] = "custom"
        data["base_id"] = self.id
        ahora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        data["creado_en"] = ahora
        data["actualizado_en"] = ahora
        return TemplateDefinition.from_dict(data)


# ----------------------------------------------------------------------
# Migración de esquema (del JSON, no de la BD — ver `_asegurar_columnas*`
# en quotetrip/db.py para la migración de columnas de la BD).
# ----------------------------------------------------------------------
def migrar_definicion(data: dict) -> dict:
    """Sube `data` (dict crudo, recién deserializado de JSON) a la versión
    de esquema actual. Cadena de migraciones incrementales: cada paso futuro
    sube en +1 `schema_version`. Hoy solo existe la v1, así que es un no-op,
    pero deja listo el punto de extensión para cuando cambie el esquema."""
    # version = data.get("schema_version", 1)
    # if version < 2:
    #     data = _migrar_v1_a_v2(data)
    data["schema_version"] = SCHEMA_VERSION
    return data


# ----------------------------------------------------------------------
# Validación — corrige con advertencia siempre que sea seguro; solo lanza
# excepción ante un caso realmente irrecuperable.
# ----------------------------------------------------------------------
def validar_plantilla(template: TemplateDefinition) -> list[str]:
    """Corrige `template` in-place (clamps/fallbacks) y devuelve la lista
    de advertencias generadas. Preferimos degradación elegante sobre un PDF
    roto: valores fuera de rango se ajustan silenciosamente con aviso, y
    solo el caso genuinamente irrecuperable (ninguna sección visible)
    lanza `ValueError` — no debería poder ocurrir dado el resto de esta
    función, pero es la última línea de defensa antes de renderizar."""
    avisos: list[str] = []

    # --- Página ---
    p = template.pagina
    if p.tamano not in TAMANOS_PAGINA:
        avisos.append(f"Tamaño de página «{p.tamano}» no reconocido; se usa A4.")
        p.tamano = "A4"
    if p.orientacion not in ORIENTACIONES:
        avisos.append(f"Orientación «{p.orientacion}» no reconocida; se usa vertical.")
        p.orientacion = "vertical"
    for campo in ("margen_sup_cm", "margen_inf_cm", "margen_izq_cm", "margen_der_cm"):
        valor = getattr(p, campo)
        if not isinstance(valor, (int, float)) or not (MARGEN_MIN_CM <= valor <= MARGEN_MAX_CM):
            base = valor if isinstance(valor, (int, float)) else 2.5
            setattr(p, campo, min(max(base, MARGEN_MIN_CM), MARGEN_MAX_CM))
            avisos.append(f"Margen «{campo}» fuera de rango; se ajustó a un valor seguro.")

    # --- Tema ---
    t = template.tema
    if t.color_primario is not None and not _hex_valido(t.color_primario):
        avisos.append("Color primario inválido; se hereda el de la cuenta.")
        t.color_primario = None
    if t.color_secundario is not None and not _hex_valido(t.color_secundario):
        avisos.append("Color secundario inválido; se hereda el de la cuenta.")
        t.color_secundario = None
    if t.fuente_id not in FUENTES_CATALOGO:
        avisos.append(f"Fuente «{t.fuente_id}» no disponible; se usa {FUENTE_POR_DEFECTO}.")
        t.fuente_id = FUENTE_POR_DEFECTO
    if not isinstance(t.tamano_base_pt, (int, float)) or not (
        TAMANO_FUENTE_MIN_PT <= t.tamano_base_pt <= TAMANO_FUENTE_MAX_PT
    ):
        base = t.tamano_base_pt if isinstance(t.tamano_base_pt, (int, float)) else 10.5
        t.tamano_base_pt = min(max(base, TAMANO_FUENTE_MIN_PT), TAMANO_FUENTE_MAX_PT)
        avisos.append("Tamaño de fuente base fuera de rango; se ajustó.")
    if t.peso_titulos not in PESOS:
        t.peso_titulos = "bold"
    if t.alineacion_titulos not in ALINEACIONES:
        t.alineacion_titulos = "centro"

    # --- Encabezado ---
    e = template.encabezado
    if not isinstance(e.logo_alto_cm, (int, float)) or not (
        LOGO_ALTO_MIN_CM <= e.logo_alto_cm <= LOGO_ALTO_MAX_CM
    ):
        base = e.logo_alto_cm if isinstance(e.logo_alto_cm, (int, float)) else 2.0
        e.logo_alto_cm = min(max(base, LOGO_ALTO_MIN_CM), LOGO_ALTO_MAX_CM)
        avisos.append("Tamaño del logo fuera de rango; se ajustó.")
    if e.logo_posicion not in POSICIONES_LOGO:
        e.logo_posicion = "izquierda"

    # --- Secciones: tipos válidos, sin duplicados, bloqueadas siempre visibles ---
    tipos_vistos: set[str] = set()
    secciones_validas: list[SeccionConfig] = []
    for s in template.secciones:
        if s.tipo not in SECCION_TIPOS:
            avisos.append(f"Se ignoró una sección de tipo desconocido «{s.tipo}».")
            continue
        if s.tipo in tipos_vistos:
            avisos.append(f"Sección «{s.tipo}» duplicada; se ignoró la repetición.")
            continue
        tipos_vistos.add(s.tipo)
        if s.tipo in SECCIONES_BLOQUEADAS and not s.visible:
            avisos.append(f"La sección «{s.tipo}» es obligatoria y no puede ocultarse.")
            s.visible = True
        secciones_validas.append(s)
    for tipo in SECCIONES_BLOQUEADAS:
        if tipo not in tipos_vistos:
            avisos.append(f"Faltaba la sección obligatoria «{tipo}»; se añadió.")
            secciones_validas.append(SeccionConfig(tipo=tipo, visible=True))
    template.secciones = secciones_validas

    if not any(s.visible for s in template.secciones):
        raise ValueError("La plantilla no tiene ninguna sección visible.")

    return avisos
