# -*- coding: utf-8 -*-
"""Lógica de elementos libres del editor de plantillas (`plantillas_ui.py`)
— Fase 2. No dirige widgets reales (no hay una suite basada en
`streamlit.testing.v1.AppTest` en este proyecto todavía); en su lugar
ejercita directamente las funciones que seedean/leen `st.session_state`,
igual que hacen los callbacks reales de los botones del editor. Fuera de
`streamlit run`/`AppTest`, `st.session_state` sigue funcionando como un
diccionario normal (con un warning informativo, no un error) — suficiente
para probar esta lógica sin necesitar una sesión de Streamlit completa."""

import streamlit as st

from quotetrip import plantillas_ui as pu
from quotetrip.pdf.models import TemplateDefinition
from quotetrip.pdf.presets import obtener_preset


def _limpiar_session_state():
    for clave in list(st.session_state.keys()):
        del st.session_state[clave]


def test_agregar_y_reconstruir_elemento_texto():
    _limpiar_session_state()
    id_ = "tpl_test"
    p = f"pe_{id_}_"
    pu._seed_editor_state(id_, obtener_preset("clasica"))

    pu._agregar_elemento(id_, "texto")
    eid = st.session_state[p + "elementos_orden"][0]
    st.session_state[p + f"el_{eid}_texto"] = "Hola mundo"
    st.session_state[p + f"el_{eid}_x"] = 3.5

    definicion = pu._construir_definicion_desde_widgets(id_, None)
    assert len(definicion.elementos) == 1
    el = definicion.elementos[0]
    assert el.tipo == "texto"
    assert el.x_cm == 3.5
    assert el.opciones["texto"] == "Hola mundo"


def test_eliminar_elemento_lo_quita_de_la_reconstruccion():
    _limpiar_session_state()
    id_ = "tpl_test2"
    p = f"pe_{id_}_"
    pu._seed_editor_state(id_, obtener_preset("clasica"))

    pu._agregar_elemento(id_, "texto")
    pu._agregar_elemento(id_, "forma")
    orden = st.session_state[p + "elementos_orden"]
    assert len(orden) == 2

    pu._eliminar_elemento(id_, orden[0])
    definicion = pu._construir_definicion_desde_widgets(id_, None)
    assert len(definicion.elementos) == 1
    assert definicion.elementos[0].tipo == "forma"


def test_seed_desde_definicion_existente_recupera_los_elementos():
    _limpiar_session_state()
    id_ = "tpl_test3"
    base = obtener_preset("clasica")

    pu._seed_editor_state(id_, base)
    pu._agregar_elemento(id_, "imagen")
    guardada = pu._construir_definicion_desde_widgets(id_, base.id)

    # Simula reabrir el editor más tarde: re-seedear desde el JSON guardado
    # debe reproducir exactamente los mismos elementos.
    _limpiar_session_state()
    recargada = TemplateDefinition.from_json(guardada.to_json())
    pu._seed_editor_state(id_, recargada)
    reconstruida = pu._construir_definicion_desde_widgets(id_, base.id)

    assert len(reconstruida.elementos) == 1
    assert reconstruida.elementos[0].tipo == "imagen"
    assert reconstruida.elementos[0].id == guardada.elementos[0].id
