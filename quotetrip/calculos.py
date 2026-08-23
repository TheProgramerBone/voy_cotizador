# -*- coding: utf-8 -*-
"""Funciones puras de formato y cálculo (sin Streamlit, sin BD) — fáciles de
probar solas."""

import re
from datetime import date

from .config import MESES_ES


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
    return (
        "Pasajeros: " + " + ".join(partes) + f"  ·  {total} pasajero" + ("s" if total != 1 else "")
    )


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
    valor_pasajero = suma_persona + grupo_por_cabeza  # adulto (todo incluido)
    valor_pasajero_menor = menor_pp + grupo_por_cabeza  # menor (todo incluido)

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
