"""Gestión de tickets de soporte de primer nivel.

- Clasifica automáticamente la categoría según palabras clave.
- Calcula la prioridad con una matriz de impacto x urgencia (estilo ITIL).
- Exige documentar la solución al cerrar, y el motivo al escalar.
"""

import re
import unicodedata

ESTADOS = ("abierto", "en_progreso", "escalado", "resuelto")

# Palabras clave (sin acentos) para la clasificación automática.
CATEGORIAS = {
    "red": {"internet", "wifi", "wi-fi", "red", "conexion", "conectar", "vpn", "navega",
            "navegar", "dns", "ip", "lento"},
    "accesos": {"contrasena", "password", "clave", "acceso", "mfa", "2fa", "bloqueado",
                "bloqueada", "permiso", "permisos", "login", "usuario"},
    "hardware": {"laptop", "pantalla", "teclado", "mouse", "bateria", "cargador",
                 "enciende", "monitor", "camara", "audifonos"},
    "impresora": {"impresora", "imprimir", "imprime", "escaner", "toner"},
    "software": {"instalar", "programa", "aplicacion", "app", "actualizar", "slack",
                 "google", "correo", "gmail", "drive", "excel", "zoom", "licencia"},
}

# Matriz impacto (1=alto, 3=bajo) x urgencia (1=alta, 3=baja).
_PRIORIDAD_POR_SUMA = {2: "P1-Critica", 3: "P2-Alta", 4: "P3-Media", 5: "P4-Baja", 6: "P4-Baja"}


class ErrorTicket(Exception):
    """Operación no permitida sobre un ticket."""


def _normalizar(texto):
    texto = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in texto if not unicodedata.combining(c))


def clasificar(texto):
    """Devuelve la categoría con más coincidencias de palabras clave, u 'otro'."""
    palabras = set(re.findall(r"[a-z0-9\-]+", _normalizar(texto)))
    mejor, puntos_mejor = "otro", 0
    for categoria, claves in CATEGORIAS.items():
        puntos = len(palabras & claves)
        if puntos > puntos_mejor:
            mejor, puntos_mejor = categoria, puntos
    return mejor


def calcular_prioridad(impacto, urgencia):
    if impacto not in (1, 2, 3) or urgencia not in (1, 2, 3):
        raise ErrorTicket("Impacto y urgencia deben ser 1 (alto), 2 (medio) o 3 (bajo).")
    return _PRIORIDAD_POR_SUMA[impacto + urgencia]


def crear_ticket(con, solicitante, titulo, impacto, urgencia, descripcion="", categoria=None):
    categoria = categoria or clasificar(f"{titulo} {descripcion}")
    prioridad = calcular_prioridad(impacto, urgencia)
    cur = con.execute(
        """INSERT INTO tickets (solicitante, titulo, descripcion, categoria, impacto, urgencia, prioridad)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (solicitante, titulo, descripcion, categoria, impacto, urgencia, prioridad),
    )
    con.commit()
    return cur.lastrowid


def obtener(con, ticket_id):
    ticket = con.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()
    if ticket is None:
        raise ErrorTicket(f"No existe el ticket #{ticket_id}.")
    return ticket


def listar(con, estado=None):
    """Lista tickets ordenados por prioridad y antigüedad."""
    sql = "SELECT * FROM tickets"
    params = ()
    if estado:
        sql += " WHERE estado = ?"
        params = (estado,)
    sql += " ORDER BY prioridad, creado_en, id"
    return con.execute(sql, params).fetchall()


def _agregar_nota(notas_actuales, nota):
    return f"{notas_actuales}\n{nota}" if notas_actuales else nota


def tomar(con, ticket_id):
    ticket = obtener(con, ticket_id)
    if ticket["estado"] == "resuelto":
        raise ErrorTicket(f"El ticket #{ticket_id} ya está resuelto.")
    con.execute("UPDATE tickets SET estado = 'en_progreso' WHERE id = ?", (ticket_id,))
    con.commit()


def escalar(con, ticket_id, motivo):
    """Escala el ticket a segundo nivel. Exige un motivo con la información completa."""
    if not motivo or len(motivo.strip()) < 10:
        raise ErrorTicket("Al escalar debes explicar qué revisaste y por qué escalas (mín. 10 caracteres).")
    ticket = obtener(con, ticket_id)
    if ticket["estado"] == "resuelto":
        raise ErrorTicket(f"El ticket #{ticket_id} ya está resuelto.")
    con.execute(
        "UPDATE tickets SET estado = 'escalado', notas = ? WHERE id = ?",
        (_agregar_nota(ticket["notas"], f"[ESCALADO] {motivo.strip()}"), ticket_id),
    )
    con.commit()


def resolver(con, ticket_id, solucion):
    """Cierra el ticket. La solución es obligatoria para alimentar la base de conocimiento."""
    if not solucion or len(solucion.strip()) < 10:
        raise ErrorTicket("Documenta la solución antes de cerrar (mín. 10 caracteres).")
    ticket = obtener(con, ticket_id)
    if ticket["estado"] == "resuelto":
        raise ErrorTicket(f"El ticket #{ticket_id} ya está resuelto.")
    con.execute(
        """UPDATE tickets SET estado = 'resuelto', solucion = ?,
           cerrado_en = datetime('now', 'localtime') WHERE id = ?""",
        (solucion.strip(), ticket_id),
    )
    con.commit()
