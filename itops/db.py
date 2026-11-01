"""Conexión y esquema de la base de datos SQLite."""

import os
import sqlite3

ESQUEMA = """
CREATE TABLE IF NOT EXISTS equipos (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    serial      TEXT UNIQUE NOT NULL,
    tipo        TEXT NOT NULL CHECK (tipo IN ('laptop', 'smartphone', 'monitor', 'otro')),
    marca       TEXT,
    modelo      TEXT,
    estado      TEXT NOT NULL DEFAULT 'disponible'
                CHECK (estado IN ('disponible', 'asignado', 'reparacion', 'baja')),
    asignado_a  TEXT,
    creado_en   TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS historial_equipos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id  INTEGER NOT NULL REFERENCES equipos(id),
    accion     TEXT NOT NULL,
    detalle    TEXT,
    fecha      TEXT NOT NULL DEFAULT (datetime('now', 'localtime'))
);

CREATE TABLE IF NOT EXISTS tickets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    solicitante  TEXT NOT NULL,
    titulo       TEXT NOT NULL,
    descripcion  TEXT,
    categoria    TEXT NOT NULL,
    impacto      INTEGER NOT NULL CHECK (impacto BETWEEN 1 AND 3),
    urgencia     INTEGER NOT NULL CHECK (urgencia BETWEEN 1 AND 3),
    prioridad    TEXT NOT NULL,
    estado       TEXT NOT NULL DEFAULT 'abierto'
                 CHECK (estado IN ('abierto', 'en_progreso', 'escalado', 'resuelto')),
    notas        TEXT,
    solucion     TEXT,
    creado_en    TEXT NOT NULL DEFAULT (datetime('now', 'localtime')),
    cerrado_en   TEXT
);
"""


def conectar(ruta=None):
    """Abre la base de datos (la crea si no existe) y devuelve la conexión.

    La ruta se puede definir con la variable de entorno ITOPS_DB.
    Usa ":memory:" para una base temporal (útil en pruebas).
    """
    ruta = ruta or os.environ.get("ITOPS_DB", "itops.db")
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    con.executescript(ESQUEMA)
    return con
