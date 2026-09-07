# -*- coding: utf-8 -*-
"""CRUD de plantillas, exclusividad de la predeterminada, e idempotencia de
la migración — Fase 1 del sistema de plantillas PDF."""

import sqlite3

import quotetrip.db as db


def test_tabla_plantillas_existe_tras_init_db(db_path):
    with sqlite3.connect(db_path) as con:
        tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "plantillas" in tablas


def test_columnas_nuevas_existen(db_path):
    with sqlite3.connect(db_path) as con:
        cols_cot = {r[1] for r in con.execute("PRAGMA table_info(cotizaciones)")}
        cols_cuenta = {r[1] for r in con.execute("PRAGMA table_info(cuenta)")}
    assert {"plantilla_id", "plantilla_snapshot_json"} <= cols_cot
    assert "plantilla_predeterminada_id" in cols_cuenta


def test_init_db_es_idempotente(db_path):
    # Llamarlo de nuevo sobre la misma BD no debe fallar ni duplicar nada.
    db.init_db()
    db.init_db()
    with sqlite3.connect(db_path) as con:
        n = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    assert n >= 3  # cotizaciones, cuenta, plantillas


def test_migracion_desde_bd_antigua(tmp_path, monkeypatch):
    """Simula una instalación existente con el esquema viejo (sin
    `plantillas` ni las columnas nuevas) y confirma que init_db() la
    actualiza sin perder datos."""
    ruta = tmp_path / "vieja.db"
    with sqlite3.connect(ruta) as con:
        con.execute(
            """CREATE TABLE cotizaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT, cliente TEXT,
                fecha_cotiz TEXT, num_opciones INTEGER, hoteles TEXT,
                valor_desde INTEGER, creado_en TEXT
            )"""
        )
        con.execute(
            "INSERT INTO cotizaciones (cliente, fecha_cotiz, num_opciones, hoteles, "
            "valor_desde, creado_en) VALUES ('Cliente Viejo', '1 enero', 1, 'Hotel X', 100, 'x')"
        )
        con.execute(
            """CREATE TABLE cuenta (
                id INTEGER PRIMARY KEY AUTOINCREMENT, razon_social TEXT, usuario TEXT
            )"""
        )
        con.execute("INSERT INTO cuenta (razon_social, usuario) VALUES ('Agencia Vieja', 'admin')")

    monkeypatch.setattr(db, "DB_PATH", ruta)
    db.init_db()

    with sqlite3.connect(ruta) as con:
        con.row_factory = sqlite3.Row
        fila = con.execute("SELECT * FROM cotizaciones").fetchone()
        cuenta = con.execute("SELECT * FROM cuenta").fetchone()
        cols_cot = {r[1] for r in con.execute("PRAGMA table_info(cotizaciones)")}
        cols_cuenta = {r[1] for r in con.execute("PRAGMA table_info(cuenta)")}

    assert fila["cliente"] == "Cliente Viejo"  # el dato preexistente sobrevive
    assert cuenta["razon_social"] == "Agencia Vieja"
    assert {"plantilla_id", "plantilla_snapshot_json"} <= cols_cot
    assert "plantilla_predeterminada_id" in cols_cuenta


def test_crear_obtener_actualizar_plantilla(db_path):
    db.crear_plantilla("t1", "Mi plantilla", base_id="clasica", definicion_json='{"a": 1}')
    fila = db.obtener_plantilla("t1")
    assert fila["nombre"] == "Mi plantilla"
    assert fila["tipo"] == "custom"
    assert fila["base_id"] == "clasica"

    db.actualizar_plantilla("t1", nombre="Renombrada")
    fila2 = db.obtener_plantilla("t1")
    assert fila2["nombre"] == "Renombrada"
    assert fila2["definicion_json"] == '{"a": 1}'  # no se tocó

    db.actualizar_plantilla("t1", definicion_json='{"a": 2}')
    fila3 = db.obtener_plantilla("t1")
    assert fila3["definicion_json"] == '{"a": 2}'


def test_obtener_plantillas_lista_todas(db_path):
    db.crear_plantilla("t1", "Zeta", None, "{}")
    db.crear_plantilla("t2", "Alfa", None, "{}")
    nombres = [f["nombre"] for f in db.obtener_plantillas()]
    assert nombres == ["Alfa", "Zeta"]  # orden alfabético


def test_duplicar_no_muta_original(db_path):
    """`crear_plantilla` para una copia no debe afectar la fila original —
    verifica el desacople exigido por el requisito de duplicación."""
    db.crear_plantilla("original", "Original", None, '{"x": 1}')
    db.crear_plantilla("copia", "Copia de Original", base_id="original", definicion_json='{"x": 1}')
    db.actualizar_plantilla("copia", definicion_json='{"x": 999}')

    original = db.obtener_plantilla("original")
    copia = db.obtener_plantilla("copia")
    assert original["definicion_json"] == '{"x": 1}'
    assert copia["definicion_json"] == '{"x": 999}'


def test_borrar_plantilla_resetea_predeterminada(db_path):
    db.crear_cuenta(
        {
            "razon_social": "A",
            "nit": "1",
            "ciudad": "Bogotá",
            "telefonos": "1",
            "contacto": "c",
            "color_primario": "#000000",
            "color_secundario": "#111111",
            "firma_nombre": "n",
            "firma_cargo": "c",
            "usuario": "admin",
            "hash_password": "h",
            "salt_password": "s",
            "pregunta_seguridad": "p",
            "hash_respuesta": "h",
            "salt_respuesta": "s",
            "hash_codigo_recup": "h",
            "salt_codigo_recup": "s",
        }
    )
    db.crear_plantilla("t1", "Mi plantilla", None, "{}")
    db.actualizar_cuenta({"plantilla_predeterminada_id": "t1"})
    assert db.obtener_cuenta()["plantilla_predeterminada_id"] == "t1"

    db.borrar_plantilla("t1")
    assert db.obtener_plantilla("t1") is None
    assert db.obtener_cuenta()["plantilla_predeterminada_id"] is None


def test_guardar_cotizacion_con_plantilla(db_path):
    db.guardar_cotizacion(
        "Cliente",
        "1 enero",
        1,
        "Hotel X",
        1000,
        datos_json="{}",
        plantilla_id="clasica",
        plantilla_snapshot_json='{"id": "clasica"}',
    )
    fila = db.obtener_historial()[0]
    assert fila["plantilla_id"] == "clasica"
    assert fila["plantilla_snapshot_json"] == '{"id": "clasica"}'


def test_guardar_cotizacion_sin_plantilla_sigue_funcionando(db_path):
    """Regresión: la firma histórica (sin argumentos de plantilla) no debe
    romperse — es exactamente como la llama hoy `cotizacion_ui.py` antes
    de la Fase 5."""
    db.guardar_cotizacion("Cliente", "1 enero", 1, "Hotel X", 1000, datos_json="{}")
    fila = db.obtener_historial()[0]
    assert fila["plantilla_id"] is None
    assert fila["plantilla_snapshot_json"] is None
