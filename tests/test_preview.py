# -*- coding: utf-8 -*-
"""Vista previa rasterizada del editor de plantillas — Fase 3 del sistema
de plantillas PDF."""

import time

from quotetrip.pdf.presets import listar_presets, obtener_preset
from quotetrip.pdf.preview import renderizar_previsualizacion

_CUENTA_MUESTRA = {
    "razon_social": "Agencia de Prueba S.A.S.",
    "nit": "NIT 900.123.456-7",
    "rnt": "RNT 12345",
    "ciudad": "Bogotá",
    "telefonos": "300 000 0000",
    "contacto": "contacto@agencia.test",
    "logo_path": None,
    "color_primario": "#2563EB",
    "color_secundario": "#1E3A8A",
    "firma_nombre": "Juan Pérez",
    "firma_cargo": "Asesor de viajes",
}


def test_renderizar_previsualizacion_devuelve_png_valido():
    clasica = obtener_preset("clasica")
    png_bytes = renderizar_previsualizacion(clasica, _CUENTA_MUESTRA)
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"
    assert len(png_bytes) > 500  # no es una imagen vacía/en blanco irrisoria


def test_previsualizacion_de_todos_los_presets():
    for preset in listar_presets():
        png_bytes = renderizar_previsualizacion(preset, _CUENTA_MUESTRA)
        assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n", f"preset {preset.id} no generó PNG válido"


def test_previsualizacion_sin_datos_de_cuenta():
    """Debe funcionar incluso sin cuenta (cuenta=None/{}), con los valores
    por defecto de `_glob_de_muestra` — nunca debe fallar por datos
    faltantes al construir la vista previa."""
    clasica = obtener_preset("clasica")
    png_bytes = renderizar_previsualizacion(clasica, {})
    assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n"


def test_previsualizacion_tiempo_razonable():
    """Presupuesto de tiempo suave: la vista previa debe sentirse
    instantánea en un editor con rerender en cada interacción."""
    clasica = obtener_preset("clasica")
    inicio = time.perf_counter()
    renderizar_previsualizacion(clasica, _CUENTA_MUESTRA)
    duracion = time.perf_counter() - inicio
    assert duracion < 3.0
