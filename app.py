# -*- coding: utf-8 -*-
"""
=======================================================================
 VOY TRAVEL AGENCY · Generador de Cotizaciones
=======================================================================
App web local (Streamlit + ReportLab) que digitaliza el modelo de
cotización de TRAVELS MORENO BLANCO S.A.S.

Novedades de esta versión:
  · Panel de colores corporativos (interfaz + PDF).
  · Servicios: Vuelos, Hotel, Traslados, Seguro y Otros.
  · Cada servicio se cobra "por pasajero adulto" o "total del grupo",
    con opción de comisión que se suma al precio.
  · Varias opciones por cotización (una página por opción), con
    pasajeros y fechas propios y vuelos/traslados compartibles.

Ejecutar:   streamlit run app.py
=======================================================================
"""

import io
import csv
import json
import logging
import os
import re
import sqlite3
import sys
import tempfile
import traceback
import urllib.request
from datetime import date, datetime
from pathlib import Path

import streamlit as st
from PIL import Image

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, PageBreak,
)

# ----------------------------------------------------------------------
# 1. RUTAS, EMPRESA Y CONSTANTES (extraídas del Word original)
# ----------------------------------------------------------------------
def _dir_recursos() -> Path:
    """Carpeta de recursos de solo lectura (assets).
    En un ejecutable de PyInstaller los archivos se extraen a sys._MEIPASS;
    en ejecución normal, junto a este archivo."""
    meipass = getattr(sys, "_MEIPASS", None)
    return Path(meipass) if meipass else Path(__file__).resolve().parent


def _dir_datos() -> Path:
    """Carpeta de escritura persistente (base de datos).
    Empaquetado -> %LOCALAPPDATA%\\VoyTravel (sobrevive al cierre).
    Normal      -> ./data junto a la app."""
    if getattr(sys, "frozen", False):
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
        d = base / "VoyTravel"
    else:
        d = Path(__file__).resolve().parent / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d


BASE_DIR = _dir_recursos()
ASSETS_DIR = BASE_DIR / "assets"
DATA_DIR = _dir_datos()
DB_PATH = DATA_DIR / "cotizaciones.db"
LOGO_PATH = ASSETS_DIR / "logo.png"

# --- Versión y actualizaciones ---
APP_VERSION = "1.1.0"
# Para habilitar el aviso de actualización, apunta esta URL a un archivo
# version.json publicado (por ejemplo en GitHub Releases). Déjalo vacío para
# desactivar la comprobación. Ver README-actualizaciones.md.
UPDATE_URL = ""

# --- Registro de errores (log) ---
LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = LOG_DIR / "voytravel.log"

logger = logging.getLogger("voytravel")
if not logger.handlers:
    try:
        _h = logging.FileHandler(LOG_PATH, encoding="utf-8")
        _h.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
        logger.addHandler(_h)
        logger.setLevel(logging.INFO)
    except Exception:
        pass


def buscar_actualizacion(version_actual: str, url: str, timeout: int = 6):
    """Consulta un version.json remoto y devuelve info si hay una versión nueva.
    Formato esperado: {"version": "1.2.0", "url": "...Setup.exe", "notas": "..."}.
    Nunca lanza excepción: si algo falla (sin internet, etc.), devuelve None."""
    if not url:
        return None

    def _tupla(v):
        return tuple(int(x) for x in str(v).strip().split(".") if x.isdigit())

    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode("utf-8"))
        ultima = str(data.get("version", "")).strip()
        if ultima and _tupla(ultima) > _tupla(version_actual):
            return {"version": ultima, "url": data.get("url", ""),
                    "notas": data.get("notas", "")}
    except Exception as e:
        logger.info("No se pudo comprobar actualizaciones: %s", e)
    return None

# --- Datos fijos de la empresa (membrete y pie) ---
EMPRESA_RAZON = "TRAVELS MORENO BLANCO S.A.S."
EMPRESA_NIT = "NIT 901.216.427-8"
EMPRESA_RNT = "RNT Nº 61761"
PIE_CIUDAD = "Floridablanca – Colombia"
PIE_TELEFONOS = "Teléfonos: +57 3165247361 - +57 3172426312"
PIE_CONTACTO = "Email: admin@voytravelagency.com  |  www.voytravelagency.com"

# --- Bloques de texto fijos (idénticos al Word) ---
NOTA_Y_LEGAL = (
    "Nota: El presente presupuesto no es válido para intercambiar por los "
    "servicios descritos. Todos los servicios están sujetos a disponibilidad "
    "y re-cotización a las tarifas vigentes. Es nuestro deber informar a todos "
    "nuestros usuarios y clientes el Artículo 17 de la ley 679/2001: La "
    "explotación y abuso sexual de menores de edad son sancionados penal y "
    "administrativamente en Colombia."
)
FIRMA_NOMBRE = "JUAN CARLOS MORENO BLANCO"
FIRMA_CARGO = "Gerente"

# --- Servicios: (clave, etiqueta, descripción por defecto) ---
INCLUSIONES = [
    ("vuelos",    "Vuelos",    "Vuelos desde Bucaramanga articulo personal"),
    ("hotel",     "Hotel",     "Hotel Todo Incluido"),
    ("traslados", "Traslados", "Traslados"),
    ("seguro",    "Seguro",    "Seguro de asistencia médica"),
    ("otros",     "Otros",     "Otros servicios"),
]
# Servicios que se pueden compartir entre todas las opciones
CLAVES_COMPARTIBLES = {"vuelos", "traslados"}

MESES_ES = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]

# --- Colores corporativos por defecto (verde del logo) ---
COLOR_PRIMARIO_DEF = "#00A858"   # verde VoyTravel (acentos, líneas)
COLOR_SECUNDARIO_DEF = "#0B5D33"  # verde oscuro (títulos, textos destacados)


# ----------------------------------------------------------------------
# 2. FUNCIONES AUXILIARES
# ----------------------------------------------------------------------
def formato_cop(valor) -> str:
    """2470000 -> '2.470.000'."""
    try:
        return f"{int(round(float(valor))):,}".replace(",", ".")
    except (ValueError, TypeError):
        return "0"


def fecha_en_espanol(d: date) -> str:
    """date(2026,6,26) -> '26 de junio del 2026'."""
    return f"{d.day} de {MESES_ES[d.month - 1]} del {d.year}"


def calcular_dias_noches(ida: date, regreso: date):
    """Devuelve (dias, noches). Convención de viajes: días = noches + 1."""
    if not ida or not regreso or regreso < ida:
        return 0, 0
    noches = (regreso - ida).days
    return noches + 1, noches


def nombre_archivo_seguro(nombre: str) -> str:
    """Limpia el nombre del cliente para usarlo como nombre de archivo."""
    limpio = re.sub(r"[^\w\sáéíóúñ-]", "", (nombre or "").strip(), flags=re.IGNORECASE)
    limpio = re.sub(r"\s+", "_", limpio)
    return limpio or "Cliente"


def texto_pasajeros(adultos: int, menores: int) -> str:
    """(2,1) -> 'Pasajeros: 2 adultos + 1 menor · 3 pasajeros'."""
    partes = [f"{adultos} adulto" + ("s" if adultos != 1 else "")]
    if menores > 0:
        partes.append(f"{menores} menor" + ("es" if menores != 1 else ""))
    total = adultos + menores
    return "Pasajeros: " + " + ".join(partes) + \
        f"  ·  {total} pasajero" + ("s" if total != 1 else "")


def calcular_opcion(adultos, menores, tarifa_menor_dif, valor_menor, servicios):
    """
    Calcula los importes de una opción a partir de sus servicios.
    Cada servicio tiene: monto + comisión (que se suma), y base 'persona' (por
    pasajero adulto) o 'total' (cobrado al grupo una sola vez).

      · suma_persona = servicios cobrados por pasajero (monto + comisión)
      · suma_total   = servicios cobrados por grupo (monto + comisión)
      · total_grupo  = suma_persona*adultos + menor_pp*menores + suma_total
      · valor_pasajero = lo que paga CADA pasajero, prorrateando lo del grupo
        (así nunca queda en 0 aunque todo sea 'total del grupo').
    """
    def efectivo(s):
        return int(s.get("monto", 0)) + int(s.get("comision", 0))

    suma_persona = sum(efectivo(s) for s in servicios if s["base"] == "persona")
    suma_total = sum(efectivo(s) for s in servicios if s["base"] == "total")
    personas = adultos + menores
    menor_pp = valor_menor if (tarifa_menor_dif and menores > 0) else suma_persona
    total_grupo = suma_persona * adultos + menor_pp * menores + suma_total

    # Prorrateo de los servicios de grupo entre todos los pasajeros
    grupo_por_cabeza = (suma_total / personas) if personas else 0
    valor_pasajero = suma_persona + grupo_por_cabeza          # adulto (todo incluido)
    valor_pasajero_menor = menor_pp + grupo_por_cabeza        # menor (todo incluido)

    items = [s["desc"] for s in servicios if s["desc"]]
    incluye = "Incluye: " + " + ".join(items) if items else "Incluye: —"

    return {
        "suma_persona": suma_persona,
        "suma_total": suma_total,
        "personas": personas,
        "menor_pp": menor_pp,
        "total_grupo": total_grupo,
        "valor_pasajero": valor_pasajero,
        "valor_pasajero_menor": valor_pasajero_menor,
        "incluye": incluye,
    }


# ----------------------------------------------------------------------
# 3. BASE DE DATOS SQLite (historial)
# ----------------------------------------------------------------------
def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS cotizaciones (
                                                        id            INTEGER PRIMARY KEY AUTOINCREMENT,
                                                        cliente       TEXT,
                                                        fecha_cotiz   TEXT,
                                                        num_opciones  INTEGER,
                                                        hoteles       TEXT,
                                                        valor_desde   INTEGER,
                                                        creado_en     TEXT
            )
            """
        )
    _asegurar_columnas()


def _asegurar_columnas():
    """Migración: agrega columnas nuevas si la BD ya existía con otro esquema."""
    nuevas = [("num_opciones", "INTEGER"), ("hoteles", "TEXT"),
              ("valor_desde", "INTEGER")]
    with sqlite3.connect(DB_PATH) as con:
        existentes = {r[1] for r in con.execute("PRAGMA table_info(cotizaciones)")}
        for col, tipo in nuevas:
            if col not in existentes:
                con.execute(f"ALTER TABLE cotizaciones ADD COLUMN {col} {tipo}")


def guardar_cotizacion(cliente, fecha_txt, num_opciones, hoteles, valor_desde):
    with sqlite3.connect(DB_PATH) as con:
        con.execute(
            """INSERT INTO cotizaciones
                   (cliente, fecha_cotiz, num_opciones, hoteles, valor_desde, creado_en)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (cliente, fecha_txt, int(num_opciones), hoteles, int(valor_desde),
             datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        )


def obtener_historial():
    with sqlite3.connect(DB_PATH) as con:
        con.row_factory = sqlite3.Row
        filas = con.execute("SELECT * FROM cotizaciones ORDER BY id DESC").fetchall()
    return [dict(f) for f in filas]


def borrar_historial():
    with sqlite3.connect(DB_PATH) as con:
        con.execute("DELETE FROM cotizaciones")


# ----------------------------------------------------------------------
# 4. IMÁGENES (Streamlit UploadedFile -> archivo compatible con ReportLab)
# ----------------------------------------------------------------------
def preparar_imagen(raw_bytes: bytes, carpeta_tmp: str) -> str:
    """Convierte bytes de imagen a un PNG RGB (fondo blanco) y devuelve la ruta."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fondo.paste(img, (0, 0), img)
        img = fondo.convert("RGB")
    else:
        img = img.convert("RGB")
    fd, ruta = tempfile.mkstemp(suffix=".png", dir=carpeta_tmp)
    os.close(fd)
    img.save(ruta, format="PNG")
    return ruta


def _imagen_flowable(ruta: str, ancho_max: float, alto_max: float = 19 * cm) -> RLImage:
    """Imagen ReportLab escalada proporcionalmente al ancho útil."""
    iw, ih = ImageReader(ruta).getSize()
    ratio = iw / ih if ih else 1
    ancho, alto = ancho_max, ancho_max / ratio
    if alto > alto_max:
        alto, ancho = alto_max, alto_max * ratio
    return RLImage(ruta, width=ancho, height=alto)


# ----------------------------------------------------------------------
# 5. GENERACIÓN DEL PDF (una página por opción, con colores corporativos)
# ----------------------------------------------------------------------
def _make_encabezado_pie(color_primario: str, color_secundario: str):
    """Devuelve la función que dibuja membrete y pie en cada página."""
    c_prim = colors.HexColor(color_primario)
    c_sec = colors.HexColor(color_secundario)

    def dibujar(canvas, doc):
        ancho, alto = A4
        canvas.saveState()

        # ---- Encabezado: logo + razón social ----
        if LOGO_PATH.exists():
            try:
                ir = ImageReader(str(LOGO_PATH))
                iw, ih = ir.getSize()
                logo_h = 2.0 * cm
                logo_w = logo_h * (iw / ih)
                canvas.drawImage(ir, doc.leftMargin, alto - 2.35 * cm,
                                 width=logo_w, height=logo_h,
                                 mask="auto", preserveAspectRatio=True)
            except Exception:
                pass

        top_y = alto - 1.35 * cm
        canvas.setFillColor(c_sec)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawRightString(ancho - doc.rightMargin, top_y, EMPRESA_RAZON)
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#333333"))
        canvas.drawRightString(ancho - doc.rightMargin, top_y - 0.42 * cm, EMPRESA_NIT)
        canvas.drawRightString(ancho - doc.rightMargin, top_y - 0.84 * cm, EMPRESA_RNT)

        canvas.setStrokeColor(c_prim)
        canvas.setLineWidth(1.0)
        canvas.line(doc.leftMargin, alto - 2.75 * cm, ancho - doc.rightMargin, alto - 2.75 * cm)

        # ---- Pie: datos de contacto ----
        canvas.setStrokeColor(c_prim)
        canvas.setLineWidth(1.0)
        canvas.line(doc.leftMargin, 2.45 * cm, ancho - doc.rightMargin, 2.45 * cm)
        canvas.setFillColor(colors.HexColor("#444444"))
        canvas.setFont("Helvetica", 8.5)
        cy = 2.05 * cm
        for i, linea in enumerate([PIE_CIUDAD, PIE_TELEFONOS, PIE_CONTACTO]):
            canvas.drawCentredString(ancho / 2.0, cy - i * 0.38 * cm, linea)

        canvas.restoreState()

    return dibujar


def construir_pdf(glob: dict, opciones: list) -> bytes:
    """
    Construye el PDF. `glob` trae cliente/fecha/colores; `opciones` es la lista
    de opciones ya calculadas, cada una con sus imágenes en bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=3.1 * cm, bottomMargin=2.9 * cm,
        leftMargin=2.2 * cm, rightMargin=2.2 * cm,
        title=f"Cotización - {glob['cliente']}", author=EMPRESA_RAZON,
    )
    ancho_util = doc.width
    c_sec = colors.HexColor(glob["color_secundario"])

    base = getSampleStyleSheet()
    est_fecha = ParagraphStyle("fecha", parent=base["Normal"], fontName="Helvetica",
                               fontSize=11, alignment=TA_LEFT, spaceAfter=6)
    est_titulo = ParagraphStyle("titulo", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=15, alignment=TA_CENTER, spaceAfter=4, leading=18,
                                textColor=c_sec)
    est_opcion = ParagraphStyle("opcion", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=12, alignment=TA_CENTER, spaceAfter=4, textColor=c_sec)
    est_sub = ParagraphStyle("sub", parent=base["Normal"], fontName="Helvetica",
                             fontSize=10.5, alignment=TA_CENTER,
                             textColor=colors.HexColor("#555555"), spaceAfter=2)
    est_valor = ParagraphStyle("valor", parent=base["Normal"], fontName="Helvetica-Bold",
                               fontSize=13, alignment=TA_CENTER, spaceBefore=8, spaceAfter=4)
    est_valor2 = ParagraphStyle("valor2", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=11, alignment=TA_CENTER, textColor=c_sec, spaceAfter=4)
    est_incluye = ParagraphStyle("incluye", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=11, alignment=TA_CENTER, leading=15, spaceAfter=10)
    est_nota = ParagraphStyle("nota", parent=base["Normal"], fontName="Helvetica",
                              fontSize=9.5, alignment=TA_JUSTIFY, leading=14, spaceAfter=14)
    est_firma = ParagraphStyle("firma", parent=base["Normal"], fontName="Helvetica",
                               fontSize=11, alignment=TA_LEFT, leading=15)
    est_firma_bold = ParagraphStyle("firmab", parent=est_firma, fontName="Helvetica-Bold")
    est_anexo = ParagraphStyle("anexo", parent=base["Normal"], fontName="Helvetica-Bold",
                               fontSize=11, alignment=TA_CENTER, textColor=c_sec,
                               spaceBefore=6, spaceAfter=8)
    est_caption = ParagraphStyle("caption", parent=base["Normal"], fontName="Helvetica-Oblique",
                                 fontSize=9.5, alignment=TA_CENTER,
                                 textColor=colors.HexColor("#555555"), spaceBefore=6, spaceAfter=4)

    varias = len(opciones) > 1
    story = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, op in enumerate(opciones):
            if i > 0:
                story.append(PageBreak())

            # ---- Encabezado de texto ----
            story.append(Paragraph(f"Bucaramanga, {glob['fecha_cotiz_txt']}", est_fecha))
            story.append(Paragraph("COTIZACIÓN", est_titulo))

            # ---- Etiqueta de la opción (si hay varias) ----
            if varias:
                etiqueta = op.get("nombre") or f"Opción {i + 1}"
                if op.get("hotel"):
                    etiqueta += f" — {op['hotel']}"
                story.append(Paragraph(etiqueta, est_opcion))
            story.append(Spacer(1, 0.35 * cm))

            # ---- Pasajeros ----
            story.append(Paragraph(op["pasajeros_txt"], est_sub))

            # ---- Hotel / fechas / duración ----
            partes = []
            if op.get("hotel"):
                partes.append(op["hotel"])
            if op.get("ida") and op.get("regreso"):
                partes.append(f"{op['ida'].strftime('%d/%m/%Y')} al {op['regreso'].strftime('%d/%m/%Y')}")
            if op.get("dias"):
                partes.append(f"{op['dias']} Días / {op['noches']} Noches")
            if partes:
                story.append(Paragraph("  ·  ".join(partes), est_sub))
            story.append(Spacer(1, 0.2 * cm))

            # ---- Valores (por pasajero, todo incluido) ----
            tarifa_dif = op.get("tarifa_menor_dif") and op.get("menores", 0) > 0
            if tarifa_dif:
                story.append(Paragraph(
                    f"Valor por pasajero adulto: ${formato_cop(op['valor_pasajero'])}", est_valor))
                story.append(Paragraph(
                    f"Valor por pasajero menor (12 años o menos): "
                    f"${formato_cop(op['valor_pasajero_menor'])}", est_sub))
            else:
                story.append(Paragraph(
                    f"VALOR TOTAL X PASAJERO: ${formato_cop(op['valor_pasajero'])}", est_valor))
            if op["personas"] > 1:
                story.append(Paragraph(
                    f"VALOR TOTAL {op['personas']} PASAJEROS: ${formato_cop(op['total_grupo'])}",
                    est_valor2))

            # ---- Inclusiones ----
            story.append(Paragraph(op["incluye"], est_incluye))

            # ---- Nota + cláusula legal ----
            story.append(Paragraph(NOTA_Y_LEGAL, est_nota))

            # ---- Firma ----
            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph("Cordialmente,", est_firma))
            story.append(Spacer(1, 1.0 * cm))
            story.append(Paragraph(FIRMA_NOMBRE, est_firma_bold))
            story.append(Paragraph(FIRMA_CARGO, est_firma))

            # ---- Anexos de la opción ----
            rutas_vuelos = [preparar_imagen(b, tmpdir) for b in op.get("imgs_vuelos_bytes", [])]
            ruta_hotel = preparar_imagen(op["img_hotel_bytes"], tmpdir) if op.get("img_hotel_bytes") else None
            if rutas_vuelos or ruta_hotel:
                story.append(Spacer(1, 0.4 * cm))
                story.append(Paragraph("Anexos", est_anexo))
                if rutas_vuelos:
                    tit = "Itinerario de vuelos" if len(rutas_vuelos) == 1 else "Itinerarios de vuelos"
                    story.append(Paragraph(tit, est_caption))
                    for r in rutas_vuelos:
                        story.append(_imagen_flowable(r, ancho_util))
                        story.append(Spacer(1, 0.5 * cm))
                if ruta_hotel:
                    story.append(Paragraph("Hotel", est_caption))
                    story.append(_imagen_flowable(ruta_hotel, ancho_util))

        dibujar = _make_encabezado_pie(glob["color_primario"], glob["color_secundario"])
        doc.build(story, onFirstPage=dibujar, onLaterPages=dibujar)

    buffer.seek(0)
    return buffer.getvalue()


# ======================================================================
# 6. INTERFAZ STREAMLIT
# ======================================================================
st.set_page_config(page_title="VoyTravel · Cotizaciones", page_icon="✈️", layout="wide")
init_db()

# ---------- Estado inicial de las opciones ----------
if "opciones" not in st.session_state:
    st.session_state["opciones"] = [{"id": 1}]
    st.session_state["next_opt_id"] = 2


# ---------- Utilidades para leer imágenes desde session_state ----------
def _bytes_lista(key):
    files = st.session_state.get(key) or []
    if not isinstance(files, list):
        files = [files]
    return [f.getvalue() for f in files if f is not None]


def _bytes_uno(key):
    f = st.session_state.get(key)
    return f.getvalue() if f else None


def _restaurar_colores():
    """Callback del botón: se ejecuta antes de recrear los selectores de color."""
    st.session_state["cp"] = COLOR_PRIMARIO_DEF
    st.session_state["cs"] = COLOR_SECUNDARIO_DEF


def fila_servicio(clave, etiqueta, desc_def, keyp, hotel_nombre=""):
    """Renderiza un servicio (check + descripción + precio + comisión + base).
    La comisión se suma al precio. Devuelve dict o None."""
    if not st.checkbox(etiqueta, key=f"chk_{keyp}"):
        return None
    if clave == "hotel" and hotel_nombre.strip():
        desc_def = f"Hotel {hotel_nombre.strip()} Todo Incluido"
    desc = st.text_input(f"Descripción · {etiqueta}", value=desc_def, key=f"desc_{keyp}")
    c1, c2, c3 = st.columns(3)
    with c1:
        monto = st.number_input(f"Precio · {etiqueta} (COP)", min_value=0, step=50000,
                                value=0, key=f"cost_{keyp}")
    with c2:
        comision = st.number_input(f"Comisión · {etiqueta} (COP)", min_value=0, step=10000,
                                   value=0, key=f"com_{keyp}",
                                   help="Se suma al precio de este servicio.")
    with c3:
        base = st.selectbox(f"Base · {etiqueta}", ["Por pasajero adulto", "Total del grupo"],
                            key=f"base_{keyp}")
    return {"clave": clave, "etiqueta": etiqueta, "desc": desc.strip(),
            "monto": int(monto), "comision": int(comision),
            "base": "persona" if base.startswith("Por") else "total"}


# ----------------------------------------------------------------------
# SIDEBAR · Ajustes globales
# ----------------------------------------------------------------------
with st.sidebar:
    if LOGO_PATH.exists():
        st.image(str(LOGO_PATH), width=120)
    st.markdown(f"### {EMPRESA_RAZON}")
    st.caption(f"{EMPRESA_NIT} · {EMPRESA_RNT}")

    st.divider()
    st.markdown("#### Datos del cliente")
    cliente = st.text_input("Nombre del cliente", placeholder="Ej: Familia Pérez Gómez")
    fecha_cotiz = st.date_input("Fecha de la cotización", value=date.today(), format="DD/MM/YYYY")

    st.divider()
    st.markdown("#### 🎨 Colores corporativos")
    st.session_state.setdefault("cp", COLOR_PRIMARIO_DEF)
    st.session_state.setdefault("cs", COLOR_SECUNDARIO_DEF)
    color_primario = st.color_picker("Color primario (acentos y líneas)", key="cp")
    color_secundario = st.color_picker("Color secundario (títulos)", key="cs")
    st.button("Restaurar verde corporativo", use_container_width=True,
              on_click=_restaurar_colores)

    st.divider()
    st.markdown("#### Vuelos y traslados")
    compartir = st.checkbox("Usar los mismos vuelos y traslados en todas las opciones",
                            value=True)

    st.divider()
    st.caption(f"Versión {APP_VERSION}")

    # --- Aviso de actualización (si UPDATE_URL está configurada) ---
    @st.cache_data(ttl=3600, show_spinner=False)
    def _chequear_update(version, url):
        return buscar_actualizacion(version, url)

    _info = _chequear_update(APP_VERSION, UPDATE_URL) if UPDATE_URL else None
    if _info:
        st.warning(f"Nueva versión disponible: {_info['version']}")
        if _info.get("notas"):
            st.caption(_info["notas"])
        if _info.get("url"):
            if hasattr(st, "link_button"):
                st.link_button("⬇️ Descargar actualización", _info["url"],
                               use_container_width=True)
            else:
                st.markdown(f"[⬇️ Descargar actualización]({_info['url']})")

    # --- Registro de errores ---
    with st.expander("🛠 Registro de errores"):
        st.caption(f"Archivo: {LOG_PATH}")
        try:
            _txt = LOG_PATH.read_text(encoding="utf-8") if LOG_PATH.exists() else ""
        except Exception:
            _txt = ""
        if _txt.strip():
            _ultimas = "\n".join(_txt.strip().splitlines()[-40:])
            st.code(_ultimas, language="text")
            st.download_button("Descargar log completo", _txt.encode("utf-8"),
                               file_name="voytravel.log", mime="text/plain",
                               use_container_width=True)
            if st.button("Vaciar registro", use_container_width=True):
                try:
                    LOG_PATH.write_text("", encoding="utf-8")
                    st.rerun()
                except Exception:
                    pass
        else:
            st.caption("Sin errores registrados. 🎉")

# --- Inyectar los colores en la interfaz ---
st.markdown(
    f"""
    <style>
      .stButton>button[kind="primary"] {{ background:{color_primario}; border:0; color:#fff; }}
      .stButton>button[kind="primary"]:hover {{ filter:brightness(0.9); }}
      h1, h2, h3 {{ color:{color_secundario}; }}
      [data-testid="stMetricValue"] {{ color:{color_secundario}; }}
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown("## Generador de Cotizaciones")

tab_cotiz, tab_hist = st.tabs(["📝  Cotización", "📁  Historial"])

# ----------------------------------------------------------------------
# TAB · COTIZACIÓN
# ----------------------------------------------------------------------
with tab_cotiz:

    # -------- Bloque compartido de vuelos y traslados --------
    servicios_compartidos = []
    if compartir:
        with st.expander("✈️ Vuelos y traslados compartidos (aplican a todas las opciones)",
                         expanded=True):
            for clave, etiqueta, desc_def in INCLUSIONES:
                if clave in CLAVES_COMPARTIBLES:
                    s = fila_servicio(clave, etiqueta, desc_def, keyp=f"{clave}_shared")
                    if s:
                        servicios_compartidos.append(s)
            st.markdown("**Capturas de itinerarios de vuelos (compartidas)**")
            st.file_uploader("Subir itinerarios de vuelos",
                             type=["png", "jpg", "jpeg", "webp"],
                             accept_multiple_files=True, key="upv_shared",
                             label_visibility="collapsed")
        imgs_vuelos_compartidas = _bytes_lista("upv_shared")
    else:
        imgs_vuelos_compartidas = []

    # -------- Controles para agregar / quitar opciones --------
    cA, cB = st.columns([3, 1])
    with cA:
        st.markdown("### Opciones de la cotización")
    with cB:
        if st.button("➕  Agregar opción", use_container_width=True):
            nid = st.session_state["next_opt_id"]
            st.session_state["opciones"].append({"id": nid})
            st.session_state["next_opt_id"] += 1
            st.rerun()

    opciones = st.session_state["opciones"]
    etiquetas = [f"Opción {i + 1}" for i in range(len(opciones))]
    tabs_op = st.tabs(etiquetas)

    # -------- Render de cada opción --------
    for i, (op, tab) in enumerate(zip(opciones, tabs_op)):
        oid = op["id"]
        with tab:
            top1, top2 = st.columns([3, 1])
            with top1:
                st.text_input("Nombre de la opción", value=f"Opción {i + 1}", key=f"nom_{oid}")
            with top2:
                st.write("")
                if len(opciones) > 1 and st.button("🗑 Eliminar", key=f"del_{oid}",
                                                   use_container_width=True):
                    st.session_state["opciones"] = [o for o in opciones if o["id"] != oid]
                    st.rerun()

            # Fechas de esta opción
            f1, f2 = st.columns(2)
            with f1:
                st.date_input("Fecha de ida", value=date(date.today().year, 1, 1),
                              format="DD/MM/YYYY", key=f"ida_{oid}")
            with f2:
                st.date_input("Fecha de regreso", value=date(date.today().year, 1, 5),
                              format="DD/MM/YYYY", key=f"reg_{oid}")
            ida = st.session_state[f"ida_{oid}"]
            reg = st.session_state[f"reg_{oid}"]
            dias, noches = calcular_dias_noches(ida, reg)
            if reg < ida:
                st.warning("La fecha de regreso es anterior a la de ida.")
            else:
                m1, m2 = st.columns(2)
                m1.metric("Días", dias)
                m2.metric("Noches", noches)

            # Pasajeros de esta opción
            p1, p2 = st.columns(2)
            with p1:
                adultos = int(st.number_input("Adultos (mayores de 12 años)", min_value=1,
                                              value=2, step=1, key=f"ad_{oid}"))
            with p2:
                menores = int(st.number_input("Menores (12 años o menos)", min_value=0,
                                              value=0, step=1, key=f"me_{oid}"))
            personas = adultos + menores
            st.caption(f"Se considera **adulto** a los mayores de 12 años. "
                       f"Total: **{personas} pasajero{'s' if personas != 1 else ''}**.")

            # Hotel
            hotel = st.text_input("Nombre del hotel", key=f"hotel_{oid}",
                                  placeholder="Ej: Hotel Riu Palace")

            # Servicios de esta opción (los compartidos no se repiten aquí)
            st.markdown("**Servicios**")
            st.caption("Marca cada servicio, ingresa su precio y comisión, "
                       "e indica si es por pasajero o total del grupo.")
            servicios_opcion = []
            for clave, etiqueta, desc_def in INCLUSIONES:
                if compartir and clave in CLAVES_COMPARTIBLES:
                    continue
                s = fila_servicio(clave, etiqueta, desc_def, keyp=f"{clave}_{oid}",
                                  hotel_nombre=hotel)
                if s:
                    servicios_opcion.append(s)

            # Tarifa de menores
            tarifa_menor_dif = False
            valor_menor = 0
            if menores > 0:
                tarifa_menor_dif = st.checkbox("Los menores pagan una tarifa diferente",
                                               key=f"tmd_{oid}")
                if tarifa_menor_dif:
                    valor_menor = int(st.number_input("Valor por menor (COP)", min_value=0,
                                                      step=50000, value=0, key=f"vm_{oid}"))

            # Imagen del hotel de esta opción
            st.file_uploader("Foto del hotel", type=["png", "jpg", "jpeg", "webp"],
                             accept_multiple_files=False, key=f"uph_{oid}")

            # Imágenes de vuelos propias (solo si NO se comparten)
            if not compartir:
                st.file_uploader("Capturas de itinerarios de vuelos",
                                 type=["png", "jpg", "jpeg", "webp"],
                                 accept_multiple_files=True, key=f"upv_{oid}")

            # ----- Cálculo y resumen en vivo de la opción -----
            servicios = servicios_compartidos + servicios_opcion
            calc = calcular_opcion(adultos, menores, tarifa_menor_dif, valor_menor, servicios)

            st.divider()
            r1, r2 = st.columns(2)
            with r1:
                st.metric("Valor por pasajero", f"${formato_cop(calc['valor_pasajero'])}")
            with r2:
                if personas > 1:
                    st.metric(f"Valor total ({personas} pasajeros)",
                              f"${formato_cop(calc['total_grupo'])}")
            if tarifa_menor_dif and menores > 0:
                st.caption(f"Valor por pasajero menor: ${formato_cop(calc['valor_pasajero_menor'])}")
            st.info(calc["incluye"])

    st.divider()

    # -------- Botón: generar y exportar --------
    if st.button("💾  Aplicar y Exportar", type="primary", use_container_width=True):
        if not cliente.strip():
            st.error("Ingresa el **nombre del cliente** en la barra lateral antes de exportar.")
        else:
            try:
                # Reconstruir todas las opciones desde session_state
                opciones_pdf = []
                hoteles, valores_desde = [], []
                error = None

                def _leer_servicio(clave, etiqueta, desc_def, keyp):
                    b = st.session_state.get(f"base_{keyp}", "Por pasajero adulto")
                    return {
                        "clave": clave, "etiqueta": etiqueta,
                        "desc": (st.session_state.get(f"desc_{keyp}", desc_def) or "").strip(),
                        "monto": int(st.session_state.get(f"cost_{keyp}", 0)),
                        "comision": int(st.session_state.get(f"com_{keyp}", 0)),
                        "base": "persona" if b.startswith("Por") else "total",
                    }

                for i, op in enumerate(st.session_state["opciones"]):
                    oid = op["id"]
                    nombre = st.session_state.get(f"nom_{oid}", f"Opción {i + 1}")
                    ida = st.session_state.get(f"ida_{oid}")
                    reg = st.session_state.get(f"reg_{oid}")
                    dias, noches = calcular_dias_noches(ida, reg)
                    adultos = int(st.session_state.get(f"ad_{oid}", 1))
                    menores = int(st.session_state.get(f"me_{oid}", 0))
                    hotel = (st.session_state.get(f"hotel_{oid}", "") or "").strip()
                    tarifa_menor_dif = bool(st.session_state.get(f"tmd_{oid}", False))
                    valor_menor = int(st.session_state.get(f"vm_{oid}", 0))

                    # Servicios propios
                    serv = []
                    for clave, etiqueta, desc_def in INCLUSIONES:
                        if compartir and clave in CLAVES_COMPARTIBLES:
                            continue
                        if st.session_state.get(f"chk_{clave}_{oid}"):
                            serv.append(_leer_servicio(clave, etiqueta, desc_def, f"{clave}_{oid}"))

                    # Servicios compartidos
                    serv_comp = []
                    if compartir:
                        for clave, etiqueta, desc_def in INCLUSIONES:
                            if clave in CLAVES_COMPARTIBLES and st.session_state.get(f"chk_{clave}_shared"):
                                serv_comp.append(_leer_servicio(clave, etiqueta, desc_def, f"{clave}_shared"))

                    servicios = serv_comp + serv
                    if not servicios:
                        error = f"La opción «{nombre}» no tiene servicios marcados."
                        break

                    calc = calcular_opcion(adultos, menores, tarifa_menor_dif, valor_menor, servicios)

                    imgs_vuelos = imgs_vuelos_compartidas if compartir else _bytes_lista(f"upv_{oid}")
                    img_hotel = _bytes_uno(f"uph_{oid}")

                    opciones_pdf.append({
                        "nombre": nombre, "hotel": hotel, "ida": ida, "regreso": reg,
                        "dias": dias, "noches": noches, "adultos": adultos, "menores": menores,
                        "tarifa_menor_dif": tarifa_menor_dif,
                        "pasajeros_txt": texto_pasajeros(adultos, menores),
                        "imgs_vuelos_bytes": imgs_vuelos, "img_hotel_bytes": img_hotel,
                        **calc,
                    })
                    if hotel:
                        hoteles.append(hotel)
                    valores_desde.append(int(round(calc["valor_pasajero"])) or calc["total_grupo"])

                if error:
                    st.error(error)
                else:
                    glob = {
                        "cliente": cliente.strip(),
                        "fecha_cotiz_txt": fecha_en_espanol(fecha_cotiz),
                        "color_primario": color_primario,
                        "color_secundario": color_secundario,
                    }
                    pdf_bytes = construir_pdf(glob, opciones_pdf)
                    guardar_cotizacion(
                        cliente.strip(), glob["fecha_cotiz_txt"], len(opciones_pdf),
                        "; ".join(hoteles) if hoteles else "-",
                        min(valores_desde) if valores_desde else 0,
                    )
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_nombre"] = f"Cotizacion_{nombre_archivo_seguro(cliente)}.pdf"
                    logger.info("PDF generado para '%s' con %d opción(es).",
                                cliente.strip(), len(opciones_pdf))
                    st.success(f"Cotización con {len(opciones_pdf)} opción(es) generada y guardada.")
            except Exception as e:
                tb = traceback.format_exc()
                logger.error("Error al generar la cotización: %s\n%s", e, tb)
                st.error(f"Ocurrió un error al generar el PDF: {e}")
                with st.expander("Ver detalle del error (para soporte)"):
                    st.code(tb, language="text")
                st.caption(f"El error también quedó guardado en el registro: {LOG_PATH}")

    if st.session_state.get("pdf_bytes"):
        st.download_button("⬇️  Exportar PDF", data=st.session_state["pdf_bytes"],
                           file_name=st.session_state["pdf_nombre"],
                           mime="application/pdf", use_container_width=True)

# ----------------------------------------------------------------------
# TAB · HISTORIAL
# ----------------------------------------------------------------------
with tab_hist:
    st.subheader("Historial de cotizaciones")
    registros = obtener_historial()

    if not registros:
        st.info("Todavía no hay cotizaciones guardadas.")
    else:
        tabla = [
            {
                "ID": r["id"],
                "Cliente": r["cliente"],
                "Fecha": r["fecha_cotiz"],
                "Opciones": r.get("num_opciones") or 1,
                "Hoteles": r.get("hoteles") or "-",
                "Desde (x pasajero)": f"${formato_cop(r.get('valor_desde') or 0)}",
                "Generada": r["creado_en"],
            }
            for r in registros
        ]
        st.dataframe(tabla, use_container_width=True, hide_index=True)

        c1, c2 = st.columns(2)
        with c1:
            buf = io.StringIO()
            w = csv.DictWriter(buf, fieldnames=list(tabla[0].keys()))
            w.writeheader(); w.writerows(tabla)
            st.download_button("⬇️  Descargar historial (CSV)",
                               data=buf.getvalue().encode("utf-8-sig"),
                               file_name="historial_cotizaciones.csv",
                               mime="text/csv", use_container_width=True)
        with c2:
            if st.button("🗑️  Vaciar historial", use_container_width=True):
                st.session_state["confirmar_borrado"] = True

        if st.session_state.get("confirmar_borrado"):
            st.warning("¿Seguro que deseas eliminar **todo** el historial?")
            cb1, cb2 = st.columns(2)
            if cb1.button("Sí, borrar todo", type="primary", use_container_width=True):
                borrar_historial()
                st.session_state["confirmar_borrado"] = False
                st.rerun()
            if cb2.button("Cancelar", use_container_width=True):
                st.session_state["confirmar_borrado"] = False
                st.rerun()