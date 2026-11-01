"""Inventario de equipos: altas, asignaciones, devoluciones, reparaciones y bajas.

Cada cambio queda registrado en `historial_equipos` para tener trazabilidad.
"""

import csv

TIPOS = ("laptop", "smartphone", "monitor", "otro")


class ErrorInventario(Exception):
    """Operación no permitida sobre un equipo."""


def _obtener(con, serial):
    equipo = con.execute("SELECT * FROM equipos WHERE serial = ?", (serial,)).fetchone()
    if equipo is None:
        raise ErrorInventario(f"No existe un equipo con serial '{serial}'.")
    return equipo


def _registrar_historial(con, equipo_id, accion, detalle=None):
    con.execute(
        "INSERT INTO historial_equipos (equipo_id, accion, detalle) VALUES (?, ?, ?)",
        (equipo_id, accion, detalle),
    )


def registrar_equipo(con, serial, tipo, marca=None, modelo=None):
    """Da de alta un equipo nuevo en estado 'disponible'."""
    tipo = tipo.lower()
    if tipo not in TIPOS:
        raise ErrorInventario(f"Tipo inválido '{tipo}'. Usa uno de: {', '.join(TIPOS)}.")
    if con.execute("SELECT 1 FROM equipos WHERE serial = ?", (serial,)).fetchone():
        raise ErrorInventario(f"Ya existe un equipo con serial '{serial}'.")
    cur = con.execute(
        "INSERT INTO equipos (serial, tipo, marca, modelo) VALUES (?, ?, ?, ?)",
        (serial, tipo, marca, modelo),
    )
    _registrar_historial(con, cur.lastrowid, "alta", f"{tipo} {marca or ''} {modelo or ''}".strip())
    con.commit()
    return cur.lastrowid


def asignar(con, serial, persona):
    """Entrega un equipo disponible a un colaborador (onboarding)."""
    equipo = _obtener(con, serial)
    if equipo["estado"] != "disponible":
        raise ErrorInventario(
            f"El equipo '{serial}' no está disponible (estado actual: {equipo['estado']})."
        )
    con.execute(
        "UPDATE equipos SET estado = 'asignado', asignado_a = ? WHERE id = ?",
        (persona, equipo["id"]),
    )
    _registrar_historial(con, equipo["id"], "asignado", persona)
    con.commit()


def devolver(con, serial):
    """Recibe un equipo de vuelta (offboarding o cambio de equipo)."""
    equipo = _obtener(con, serial)
    if equipo["estado"] not in ("asignado", "reparacion"):
        raise ErrorInventario(
            f"El equipo '{serial}' no se puede devolver (estado actual: {equipo['estado']})."
        )
    detalle = equipo["asignado_a"] or "regreso de reparación"
    con.execute(
        "UPDATE equipos SET estado = 'disponible', asignado_a = NULL WHERE id = ?",
        (equipo["id"],),
    )
    _registrar_historial(con, equipo["id"], "devuelto", detalle)
    con.commit()


def enviar_reparacion(con, serial, detalle=None):
    """Marca un equipo como en reparación o garantía."""
    equipo = _obtener(con, serial)
    if equipo["estado"] == "baja":
        raise ErrorInventario(f"El equipo '{serial}' está dado de baja.")
    con.execute(
        "UPDATE equipos SET estado = 'reparacion', asignado_a = NULL WHERE id = ?",
        (equipo["id"],),
    )
    _registrar_historial(con, equipo["id"], "reparacion", detalle)
    con.commit()


def dar_baja(con, serial, motivo):
    """Retira definitivamente un equipo del inventario activo."""
    equipo = _obtener(con, serial)
    if equipo["estado"] == "asignado":
        raise ErrorInventario(
            f"El equipo '{serial}' está asignado a {equipo['asignado_a']}. Primero debe devolverse."
        )
    con.execute(
        "UPDATE equipos SET estado = 'baja', asignado_a = NULL WHERE id = ?", (equipo["id"],)
    )
    _registrar_historial(con, equipo["id"], "baja", motivo)
    con.commit()


def listar(con, estado=None):
    if estado:
        return con.execute(
            "SELECT * FROM equipos WHERE estado = ? ORDER BY tipo, serial", (estado,)
        ).fetchall()
    return con.execute("SELECT * FROM equipos ORDER BY estado, tipo, serial").fetchall()


def historial(con, serial):
    equipo = _obtener(con, serial)
    return con.execute(
        "SELECT fecha, accion, detalle FROM historial_equipos WHERE equipo_id = ? ORDER BY id",
        (equipo["id"],),
    ).fetchall()


def exportar_csv(con, ruta):
    """Exporta el inventario completo a CSV (para conteos físicos o conciliación)."""
    filas = listar(con)
    columnas = ["serial", "tipo", "marca", "modelo", "estado", "asignado_a", "creado_en"]
    with open(ruta, "w", newline="", encoding="utf-8") as f:
        escritor = csv.writer(f)
        escritor.writerow(columnas)
        for fila in filas:
            escritor.writerow([fila[c] for c in columnas])
    return len(filas)
