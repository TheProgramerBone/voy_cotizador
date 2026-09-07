# -*- coding: utf-8 -*-
"""Fixtures compartidas: aísla cada test en una base de datos SQLite
temporal, monkeypatcheando `DB_PATH` como sugiere `CLAUDE.local.md` —
`_conectar()` (quotetrip/db.py) lee el nombre del módulo en cada llamada,
no lo captura en un closure al importar, así que este patch funciona sin
tocar la lógica de conexión."""

import sys
from datetime import date
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Apunta quotetrip.db al archivo SQLite temporal e inicializa el
    esquema. Devuelve la ruta por si un test la necesita."""
    import quotetrip.db as db

    ruta = tmp_path / "cotizaciones_test.db"
    monkeypatch.setattr(db, "DB_PATH", ruta)
    db.init_db()
    return ruta


@pytest.fixture
def glob_de_prueba() -> dict:
    """`glob` de ejemplo — misma forma exacta que construye
    `cotizacion_ui.py` al exportar (ver `render_tab_cotizacion`)."""
    return {
        "cliente": "Cliente de Prueba",
        "fecha_cotiz_txt": "7 de septiembre del 2026",
        "color_primario": "#2563EB",
        "color_secundario": "#1E3A8A",
        "razon_social": "Agencia de Prueba S.A.S.",
        "nit": "NIT 900.123.456-7",
        "rnt": "RNT 12345",
        "ciudad": "Bogotá",
        "telefonos": "300 000 0000",
        "contacto": "contacto@agencia.test",
        "logo_path": None,
        "firma_nombre": "Juan Pérez",
        "firma_cargo": "Asesor de viajes",
    }


def _opcion_de_prueba(
    nombre="Plan A",
    hotel="Hotel Caribe",
    adultos=2,
    menores=0,
    tarifa_dif=False,
    con_servicios_crudos=True,
) -> dict:
    """Construye una opción calculada (misma forma que `opciones_pdf` en
    `cotizacion_ui.py`). `con_servicios_crudos=True` incluye la lista
    `servicios` cruda (campo añadido en la Fase 5 del sistema de
    plantillas) para poder ejercitar el layout de tabla."""
    import quotetrip.calculos as calculos

    servicios = [
        {
            "clave": "vuelos",
            "etiqueta": "Vuelos",
            "desc": "Vuelos ida y vuelta",
            "monto": 1200000,
            "comision": 50000,
            "base": "persona",
        },
        {
            "clave": "hotel",
            "etiqueta": "Hotel",
            "desc": f"Hotel {hotel} Todo Incluido",
            "monto": 800000,
            "comision": 0,
            "base": "persona",
        },
        {
            "clave": "traslados",
            "etiqueta": "Traslados",
            "desc": "Traslados aeropuerto-hotel",
            "monto": 150000,
            "comision": 0,
            "base": "total",
        },
    ]
    calc = calculos.calcular_opcion(
        adultos, menores, tarifa_dif, 500000 if tarifa_dif else 0, servicios
    )
    op = {
        "nombre": nombre,
        "hotel": hotel,
        "ida": date(2026, 12, 10),
        "regreso": date(2026, 12, 15),
        "dias": 6,
        "noches": 5,
        "adultos": adultos,
        "menores": menores,
        "tarifa_menor_dif": tarifa_dif,
        "pasajeros_txt": calculos.texto_pasajeros(adultos, menores),
        "imgs_vuelos_bytes": [],
        "img_hotel_bytes": None,
        **calc,
    }
    if con_servicios_crudos:
        op["servicios"] = servicios
    return op


@pytest.fixture
def opcion_de_prueba():
    """Fixture-fábrica: `opcion_de_prueba()` o
    `opcion_de_prueba(nombre=..., adultos=..., ...)` — ver
    `_opcion_de_prueba` para los parámetros disponibles."""
    return _opcion_de_prueba
