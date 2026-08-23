# -*- coding: utf-8 -*-
"""Generación del PDF de la cotización (una página por opción) y utilidades
de imagen (Streamlit UploadedFile -> archivo compatible con ReportLab)."""

import io
import os
import tempfile
from pathlib import Path

from PIL import Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Image as RLImage,
)
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)

from .calculos import formato_cop
from .config import NOTA_Y_LEGAL


# ----------------------------------------------------------------------
# Imágenes
# ----------------------------------------------------------------------
def _a_png_rgb(raw_bytes: bytes) -> Image.Image:
    """Convierte bytes de imagen a un Image PIL en RGB con fondo blanco
    (si tenía transparencia)."""
    img = Image.open(io.BytesIO(raw_bytes))
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        fondo = Image.new("RGBA", img.size, (255, 255, 255, 255))
        fondo.paste(img, (0, 0), img)
        return fondo.convert("RGB")
    return img.convert("RGB")


def preparar_imagen(raw_bytes: bytes, carpeta_tmp: str) -> str:
    """Guarda la imagen como PNG RGB en un archivo temporal y devuelve la ruta."""
    fd, ruta = tempfile.mkstemp(suffix=".png", dir=carpeta_tmp)
    os.close(fd)
    _a_png_rgb(raw_bytes).save(ruta, format="PNG")
    return ruta


def guardar_logo_cuenta(raw_bytes: bytes, destino: Path) -> str:
    """Guarda el logo de una cuenta en una ruta fija (se sobreescribe si ya
    existía). A diferencia de `preparar_imagen`, no es temporal."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    _a_png_rgb(raw_bytes).save(destino, format="PNG")
    return str(destino)


def _imagen_flowable(ruta: str, ancho_max: float, alto_max: float = 19 * cm) -> RLImage:
    """Imagen ReportLab escalada proporcionalmente al ancho útil."""
    iw, ih = ImageReader(ruta).getSize()
    ratio = iw / ih if ih else 1
    ancho, alto = ancho_max, ancho_max / ratio
    if alto > alto_max:
        alto, ancho = alto_max, alto_max * ratio
    return RLImage(ruta, width=ancho, height=alto)


# ----------------------------------------------------------------------
# Encabezado y pie (membrete de la cuenta, colores propios)
# ----------------------------------------------------------------------
def _make_encabezado_pie(glob: dict):
    """Devuelve la función que dibuja membrete y pie en cada página, con los
    datos de la cuenta (`glob`: razon_social, nit, rnt, logo_path, ciudad,
    telefonos, contacto, color_primario, color_secundario)."""
    c_prim = colors.HexColor(glob["color_primario"])
    c_sec = colors.HexColor(glob["color_secundario"])
    logo_path = glob.get("logo_path")

    def dibujar(canvas, doc):
        ancho, alto = A4
        canvas.saveState()

        # ---- Encabezado: logo + razón social ----
        if logo_path and Path(logo_path).exists():
            try:
                ir = ImageReader(str(logo_path))
                iw, ih = ir.getSize()
                logo_h = 2.0 * cm
                logo_w = logo_h * (iw / ih)
                canvas.drawImage(
                    ir,
                    doc.leftMargin,
                    alto - 2.35 * cm,
                    width=logo_w,
                    height=logo_h,
                    mask="auto",
                    preserveAspectRatio=True,
                )
            except Exception:
                pass

        top_y = alto - 1.35 * cm
        canvas.setFillColor(c_sec)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawRightString(ancho - doc.rightMargin, top_y, glob.get("razon_social") or "")
        canvas.setFont("Helvetica", 9)
        canvas.setFillColor(colors.HexColor("#333333"))
        lineas_extra = [l for l in [glob.get("nit"), glob.get("rnt")] if l]
        for i, linea in enumerate(lineas_extra):
            canvas.drawRightString(ancho - doc.rightMargin, top_y - (i + 1) * 0.42 * cm, linea)

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
        lineas_pie = [
            l for l in [glob.get("ciudad"), glob.get("telefonos"), glob.get("contacto")] if l
        ]
        for i, linea in enumerate(lineas_pie):
            canvas.drawCentredString(ancho / 2.0, cy - i * 0.38 * cm, linea)

        canvas.restoreState()

    return dibujar


# ----------------------------------------------------------------------
# Documento
# ----------------------------------------------------------------------
def construir_pdf(glob: dict, opciones: list) -> bytes:
    """
    Construye el PDF. `glob` trae cliente/fecha/colores/datos de la cuenta
    (razon_social, nit, rnt, ciudad, telefonos, contacto, logo_path,
    firma_nombre, firma_cargo); `opciones` es la lista de opciones ya
    calculadas, cada una con sus imágenes en bytes.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=3.1 * cm,
        bottomMargin=2.9 * cm,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        title=f"Cotización - {glob['cliente']}",
        author=glob.get("razon_social") or "",
    )
    ancho_util = doc.width
    c_sec = colors.HexColor(glob["color_secundario"])

    base = getSampleStyleSheet()
    est_fecha = ParagraphStyle(
        "fecha",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        alignment=TA_LEFT,
        spaceAfter=6,
    )
    est_titulo = ParagraphStyle(
        "titulo",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=15,
        alignment=TA_CENTER,
        spaceAfter=4,
        leading=18,
        textColor=c_sec,
    )
    est_opcion = ParagraphStyle(
        "opcion",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=4,
        textColor=c_sec,
    )
    est_sub = ParagraphStyle(
        "sub",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=10.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceAfter=2,
    )
    est_valor = ParagraphStyle(
        "valor",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        alignment=TA_CENTER,
        spaceBefore=8,
        spaceAfter=4,
    )
    est_valor2 = ParagraphStyle(
        "valor2",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_CENTER,
        textColor=c_sec,
        spaceAfter=4,
    )
    est_incluye = ParagraphStyle(
        "incluye",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        alignment=TA_CENTER,
        leading=15,
        spaceAfter=10,
    )
    est_nota = ParagraphStyle(
        "nota",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=9.5,
        alignment=TA_JUSTIFY,
        leading=14,
        spaceAfter=14,
    )
    est_firma = ParagraphStyle(
        "firma",
        parent=base["Normal"],
        fontName="Helvetica",
        fontSize=11,
        alignment=TA_LEFT,
        leading=15,
    )
    est_firma_bold = ParagraphStyle("firmab", parent=est_firma, fontName="Helvetica-Bold")
    est_anexo = ParagraphStyle(
        "anexo",
        parent=base["Normal"],
        fontName="Helvetica-Bold",
        fontSize=11,
        alignment=TA_CENTER,
        textColor=c_sec,
        spaceBefore=6,
        spaceAfter=8,
    )
    est_caption = ParagraphStyle(
        "caption",
        parent=base["Normal"],
        fontName="Helvetica-Oblique",
        fontSize=9.5,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#555555"),
        spaceBefore=6,
        spaceAfter=4,
    )

    varias = len(opciones) > 1
    story = []

    with tempfile.TemporaryDirectory() as tmpdir:
        for i, op in enumerate(opciones):
            if i > 0:
                story.append(PageBreak())

            # ---- Encabezado de texto ----
            story.append(Paragraph(glob["fecha_cotiz_txt"], est_fecha))
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
                partes.append(
                    f"{op['ida'].strftime('%d/%m/%Y')} al {op['regreso'].strftime('%d/%m/%Y')}"
                )
            if op.get("dias"):
                partes.append(f"{op['dias']} Días / {op['noches']} Noches")
            if partes:
                story.append(Paragraph("  ·  ".join(partes), est_sub))
            story.append(Spacer(1, 0.2 * cm))

            # ---- Valores (por pasajero, todo incluido) ----
            tarifa_dif = op.get("tarifa_menor_dif") and op.get("menores", 0) > 0
            if tarifa_dif:
                story.append(
                    Paragraph(
                        f"Valor por pasajero adulto: ${formato_cop(op['valor_pasajero'])}",
                        est_valor,
                    )
                )
                story.append(
                    Paragraph(
                        f"Valor por pasajero menor (12 años o menos): "
                        f"${formato_cop(op['valor_pasajero_menor'])}",
                        est_sub,
                    )
                )
            else:
                story.append(
                    Paragraph(
                        f"VALOR TOTAL X PASAJERO: ${formato_cop(op['valor_pasajero'])}", est_valor
                    )
                )
            if op["personas"] > 1:
                story.append(
                    Paragraph(
                        f"VALOR TOTAL {op['personas']} PASAJEROS: ${formato_cop(op['total_grupo'])}",
                        est_valor2,
                    )
                )

            # ---- Inclusiones ----
            story.append(Paragraph(op["incluye"], est_incluye))

            # ---- Nota + cláusula legal ----
            story.append(Paragraph(NOTA_Y_LEGAL, est_nota))

            # ---- Firma ----
            story.append(Spacer(1, 0.4 * cm))
            story.append(Paragraph("Cordialmente,", est_firma))
            story.append(Spacer(1, 1.0 * cm))
            story.append(Paragraph(glob.get("firma_nombre") or "", est_firma_bold))
            story.append(Paragraph(glob.get("firma_cargo") or "", est_firma))

            # ---- Anexos de la opción ----
            rutas_vuelos = [preparar_imagen(b, tmpdir) for b in op.get("imgs_vuelos_bytes", [])]
            ruta_hotel = (
                preparar_imagen(op["img_hotel_bytes"], tmpdir)
                if op.get("img_hotel_bytes")
                else None
            )
            if rutas_vuelos or ruta_hotel:
                story.append(Spacer(1, 0.4 * cm))
                story.append(Paragraph("Anexos", est_anexo))
                if rutas_vuelos:
                    tit = (
                        "Itinerario de vuelos"
                        if len(rutas_vuelos) == 1
                        else "Itinerarios de vuelos"
                    )
                    story.append(Paragraph(tit, est_caption))
                    for r in rutas_vuelos:
                        story.append(_imagen_flowable(r, ancho_util))
                        story.append(Spacer(1, 0.5 * cm))
                if ruta_hotel:
                    story.append(Paragraph("Hotel", est_caption))
                    story.append(_imagen_flowable(ruta_hotel, ancho_util))

        dibujar = _make_encabezado_pie(glob)
        doc.build(story, onFirstPage=dibujar, onLaterPages=dibujar)

    buffer.seek(0)
    return buffer.getvalue()
