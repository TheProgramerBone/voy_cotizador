# -*- coding: utf-8 -*-
"""Asistente guiado (modal, primera vez que se entra) y pestaña de ayuda
permanente con el mismo contenido en formato estático."""

import streamlit as st

from .config import PRODUCTO_NOMBRE
from .db import actualizar_cuenta

PASOS = [
    (
        f"¡Bienvenido a {PRODUCTO_NOMBRE}!",
        "Aquí armas cotizaciones de viaje profesionales en minutos y las exportas "
        "en PDF con la marca de tu agencia.",
    ),
    (
        "1. Servicios compartidos",
        "Si varias opciones de una misma cotización usan los mismos vuelos y "
        "traslados, actívalos una sola vez arriba (barra lateral desactivada) y "
        "se repiten automáticamente en todas las opciones.",
    ),
    (
        "2. Arma cada opción",
        "Cada pestaña de opción tiene sus propias fechas, pasajeros, hotel y "
        "servicios. Marca cada servicio, pon el precio, la comisión (se suma al "
        "precio) y si se cobra por pasajero adulto o por el total del grupo.",
    ),
    (
        "3. Genera el PDF",
        "Cuando termines, pon el nombre del cliente en la barra lateral y pulsa "
        "«Aplicar y Exportar». Se genera un PDF con una página por opción, con tu "
        "logo y colores, y queda guardado en el historial.",
    ),
    (
        "4. Historial",
        "En la pestaña Historial puedes ver, filtrar y descargar en CSV todas las "
        "cotizaciones que has generado con esta cuenta.",
    ),
]


@st.dialog("Cómo usar " + PRODUCTO_NOMBRE, width="large")
def _dialogo_tutorial():
    paso = st.session_state.get("tutorial_paso", 0)
    titulo, texto = PASOS[paso]
    st.markdown(f"#### {titulo}")
    st.write(texto)
    st.progress((paso + 1) / len(PASOS))

    c1, c2, c3 = st.columns(3)
    with c1:
        if paso > 0 and st.button("← Atrás", use_container_width=True):
            st.session_state["tutorial_paso"] = paso - 1
            st.rerun()
    with c2:
        if st.button("Saltar", use_container_width=True):
            _cerrar_tutorial()
    with c3:
        if paso < len(PASOS) - 1:
            if st.button("Siguiente →", type="primary", use_container_width=True):
                st.session_state["tutorial_paso"] = paso + 1
                st.rerun()
        elif st.button("Listo ✓", type="primary", use_container_width=True):
            _cerrar_tutorial()


def _cerrar_tutorial():
    actualizar_cuenta({"tutorial_visto": 1})
    st.session_state["cuenta_nueva"] = False
    st.session_state.pop("tutorial_paso", None)
    st.rerun()


def mostrar_tutorial():
    st.session_state.setdefault("tutorial_paso", 0)
    _dialogo_tutorial()


def tab_ayuda():
    st.subheader("Ayuda / Tutorial")
    st.caption(f"Guía rápida de {PRODUCTO_NOMBRE}, paso a paso.")
    for titulo, texto in PASOS:
        with st.expander(titulo):
            st.write(texto)
    st.divider()
    if st.button("▶ Volver a ver el asistente guiado"):
        st.session_state["tutorial_paso"] = 0
        st.session_state["mostrar_tutorial_manual"] = True
        st.rerun()
