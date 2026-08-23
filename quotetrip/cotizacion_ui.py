# -*- coding: utf-8 -*-
"""Pestaña "Cotización": servicios compartidos, opciones (pasajeros, fechas,
hotel, servicios), cálculo en vivo y el botón "Aplicar y Exportar" que arma
el PDF y lo guarda en el historial."""

import traceback
from datetime import date

import streamlit as st

from .calculos import (
    calcular_dias_noches,
    calcular_opcion,
    fecha_en_espanol,
    formato_cop,
    nombre_archivo_seguro,
    texto_pasajeros,
)
from .config import CLAVES_COMPARTIBLES, INCLUSIONES, LOG_PATH, logger
from .db import guardar_cotizacion
from .pdf import construir_pdf


def _bytes_lista(key):
    files = st.session_state.get(key) or []
    if not isinstance(files, list):
        files = [files]
    return [f.getvalue() for f in files if f is not None]


def _bytes_uno(key):
    f = st.session_state.get(key)
    return f.getvalue() if f else None


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
        monto = st.number_input(
            f"Precio · {etiqueta} (COP)", min_value=0, step=50000, value=0, key=f"cost_{keyp}"
        )
    with c2:
        comision = st.number_input(
            f"Comisión · {etiqueta} (COP)",
            min_value=0,
            step=10000,
            value=0,
            key=f"com_{keyp}",
            help="Se suma al precio de este servicio.",
        )
    with c3:
        base = st.selectbox(
            f"Base · {etiqueta}", ["Por pasajero adulto", "Total del grupo"], key=f"base_{keyp}"
        )
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "desc": desc.strip(),
        "monto": int(monto),
        "comision": int(comision),
        "base": "persona" if base.startswith("Por") else "total",
    }


def _leer_servicio(clave, etiqueta, desc_def, keyp):
    b = st.session_state.get(f"base_{keyp}", "Por pasajero adulto")
    return {
        "clave": clave,
        "etiqueta": etiqueta,
        "desc": (st.session_state.get(f"desc_{keyp}", desc_def) or "").strip(),
        "monto": int(st.session_state.get(f"cost_{keyp}", 0)),
        "comision": int(st.session_state.get(f"com_{keyp}", 0)),
        "base": "persona" if b.startswith("Por") else "total",
    }


def render_tab_cotizacion(
    cuenta, cliente, fecha_cotiz, color_primario, color_secundario, compartir
):
    # -------- Estado inicial de las opciones --------
    if "opciones" not in st.session_state:
        st.session_state["opciones"] = [{"id": 1}]
        st.session_state["next_opt_id"] = 2

    # -------- Bloque compartido de vuelos y traslados --------
    servicios_compartidos = []
    if compartir:
        with st.expander(
            "✈️ Vuelos y traslados compartidos (aplican a todas las opciones)", expanded=True
        ):
            for clave, etiqueta, desc_def in INCLUSIONES:
                if clave in CLAVES_COMPARTIBLES:
                    s = fila_servicio(clave, etiqueta, desc_def, keyp=f"{clave}_shared")
                    if s:
                        servicios_compartidos.append(s)
            st.markdown("**Capturas de itinerarios de vuelos (compartidas)**")
            st.file_uploader(
                "Subir itinerarios de vuelos",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=True,
                key="upv_shared",
                label_visibility="collapsed",
            )
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
                if len(opciones) > 1 and st.button(
                    "🗑 Eliminar", key=f"del_{oid}", use_container_width=True
                ):
                    st.session_state["opciones"] = [o for o in opciones if o["id"] != oid]
                    st.rerun()

            # Fechas de esta opción
            f1, f2 = st.columns(2)
            with f1:
                st.date_input(
                    "Fecha de ida",
                    value=date(date.today().year, 1, 1),
                    format="DD/MM/YYYY",
                    key=f"ida_{oid}",
                )
            with f2:
                st.date_input(
                    "Fecha de regreso",
                    value=date(date.today().year, 1, 5),
                    format="DD/MM/YYYY",
                    key=f"reg_{oid}",
                )
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
                adultos = int(
                    st.number_input(
                        "Adultos (mayores de 12 años)",
                        min_value=1,
                        value=2,
                        step=1,
                        key=f"ad_{oid}",
                    )
                )
            with p2:
                menores = int(
                    st.number_input(
                        "Menores (12 años o menos)", min_value=0, value=0, step=1, key=f"me_{oid}"
                    )
                )
            personas = adultos + menores
            st.caption(
                f"Se considera **adulto** a los mayores de 12 años. "
                f"Total: **{personas} pasajero{'s' if personas != 1 else ''}**."
            )

            # Hotel
            hotel = st.text_input(
                "Nombre del hotel", key=f"hotel_{oid}", placeholder="Ej: Hotel Riu Palace"
            )

            # Servicios de esta opción (los compartidos no se repiten aquí)
            st.markdown("**Servicios**")
            st.caption(
                "Marca cada servicio, ingresa su precio y comisión, "
                "e indica si es por pasajero o total del grupo."
            )
            servicios_opcion = []
            for clave, etiqueta, desc_def in INCLUSIONES:
                if compartir and clave in CLAVES_COMPARTIBLES:
                    continue
                s = fila_servicio(
                    clave, etiqueta, desc_def, keyp=f"{clave}_{oid}", hotel_nombre=hotel
                )
                if s:
                    servicios_opcion.append(s)

            # Tarifa de menores
            tarifa_menor_dif = False
            valor_menor = 0
            if menores > 0:
                tarifa_menor_dif = st.checkbox(
                    "Los menores pagan una tarifa diferente", key=f"tmd_{oid}"
                )
                if tarifa_menor_dif:
                    valor_menor = int(
                        st.number_input(
                            "Valor por menor (COP)",
                            min_value=0,
                            step=50000,
                            value=0,
                            key=f"vm_{oid}",
                        )
                    )

            # Imagen del hotel de esta opción
            st.file_uploader(
                "Foto del hotel",
                type=["png", "jpg", "jpeg", "webp"],
                accept_multiple_files=False,
                key=f"uph_{oid}",
            )

            # Imágenes de vuelos propias (solo si NO se comparten)
            if not compartir:
                st.file_uploader(
                    "Capturas de itinerarios de vuelos",
                    type=["png", "jpg", "jpeg", "webp"],
                    accept_multiple_files=True,
                    key=f"upv_{oid}",
                )

            # ----- Cálculo y resumen en vivo de la opción -----
            servicios = servicios_compartidos + servicios_opcion
            calc = calcular_opcion(adultos, menores, tarifa_menor_dif, valor_menor, servicios)

            st.divider()
            r1, r2 = st.columns(2)
            with r1:
                st.metric("Valor por pasajero", f"${formato_cop(calc['valor_pasajero'])}")
            with r2:
                if personas > 1:
                    st.metric(
                        f"Valor total ({personas} pasajeros)",
                        f"${formato_cop(calc['total_grupo'])}",
                    )
            if tarifa_menor_dif and menores > 0:
                st.caption(
                    f"Valor por pasajero menor: ${formato_cop(calc['valor_pasajero_menor'])}"
                )
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

                for i, op in enumerate(st.session_state["opciones"]):
                    oid = op["id"]
                    nombre = st.session_state.get(f"nom_{oid}", f"Opción {i + 1}")
                    ida = st.session_state.get(f"ida_{oid}")
                    reg = st.session_state.get(f"reg_{oid}")
                    if ida and reg and reg < ida:
                        error = (
                            f"La opción «{nombre}» tiene la fecha de regreso antes que la de ida."
                        )
                        break
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
                            if clave in CLAVES_COMPARTIBLES and st.session_state.get(
                                f"chk_{clave}_shared"
                            ):
                                serv_comp.append(
                                    _leer_servicio(clave, etiqueta, desc_def, f"{clave}_shared")
                                )

                    servicios = serv_comp + serv
                    if not servicios:
                        error = f"La opción «{nombre}» no tiene servicios marcados."
                        break

                    calc = calcular_opcion(
                        adultos, menores, tarifa_menor_dif, valor_menor, servicios
                    )

                    imgs_vuelos = (
                        imgs_vuelos_compartidas if compartir else _bytes_lista(f"upv_{oid}")
                    )
                    img_hotel = _bytes_uno(f"uph_{oid}")

                    opciones_pdf.append(
                        {
                            "nombre": nombre,
                            "hotel": hotel,
                            "ida": ida,
                            "regreso": reg,
                            "dias": dias,
                            "noches": noches,
                            "adultos": adultos,
                            "menores": menores,
                            "tarifa_menor_dif": tarifa_menor_dif,
                            "pasajeros_txt": texto_pasajeros(adultos, menores),
                            "imgs_vuelos_bytes": imgs_vuelos,
                            "img_hotel_bytes": img_hotel,
                            **calc,
                        }
                    )
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
                        "razon_social": cuenta.get("razon_social") or "",
                        "nit": cuenta.get("nit") or "",
                        "rnt": cuenta.get("rnt") or "",
                        "ciudad": cuenta.get("ciudad") or "",
                        "telefonos": cuenta.get("telefonos") or "",
                        "contacto": cuenta.get("contacto") or "",
                        "logo_path": cuenta.get("logo_path"),
                        "firma_nombre": cuenta.get("firma_nombre") or "",
                        "firma_cargo": cuenta.get("firma_cargo") or "",
                    }
                    pdf_bytes = construir_pdf(glob, opciones_pdf)
                    guardar_cotizacion(
                        cliente.strip(),
                        glob["fecha_cotiz_txt"],
                        len(opciones_pdf),
                        "; ".join(hoteles) if hoteles else "-",
                        min(valores_desde) if valores_desde else 0,
                    )
                    st.session_state["pdf_bytes"] = pdf_bytes
                    st.session_state["pdf_nombre"] = (
                        f"Cotizacion_{nombre_archivo_seguro(cliente)}.pdf"
                    )
                    logger.info(
                        "PDF generado para '%s' con %d opción(es).",
                        cliente.strip(),
                        len(opciones_pdf),
                    )
                    st.success(
                        f"Cotización con {len(opciones_pdf)} opción(es) generada y guardada."
                    )
            except Exception as e:
                tb = traceback.format_exc()
                logger.error("Error al generar la cotización: %s\n%s", e, tb)
                st.error(f"Ocurrió un error al generar el PDF: {e}")
                with st.expander("Ver detalle del error (para soporte)"):
                    st.code(tb, language="text")
                st.caption(f"El error también quedó guardado en el registro: {LOG_PATH}")

    if st.session_state.get("pdf_bytes"):
        st.download_button(
            "⬇️  Exportar PDF",
            data=st.session_state["pdf_bytes"],
            file_name=st.session_state["pdf_nombre"],
            mime="application/pdf",
            use_container_width=True,
        )
