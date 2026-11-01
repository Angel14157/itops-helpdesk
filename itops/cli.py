"""Interfaz de línea de comandos.  Uso:  python -m itops --help"""

import argparse
import sys

from . import diagnostico, inventario, reportes, tickets
from .db import conectar


def imprimir_tabla(filas, columnas):
    if not filas:
        print("(sin resultados)")
        return
    datos = [[str(f[c] if f[c] is not None else "-") for c in columnas] for f in filas]
    anchos = [max(len(c), *(len(d[i]) for d in datos)) for i, c in enumerate(columnas)]
    print("  ".join(c.upper().ljust(a) for c, a in zip(columnas, anchos)))
    print("  ".join("-" * a for a in anchos))
    for d in datos:
        print("  ".join(v.ljust(a) for v, a in zip(d, anchos)))


# ---------- Equipos ----------

def cmd_equipo(args, con):
    acc = args.accion
    if acc == "agregar":
        inventario.registrar_equipo(con, args.serial, args.tipo, args.marca, args.modelo)
        print(f"✔ Equipo {args.serial} registrado.")
    elif acc == "asignar":
        inventario.asignar(con, args.serial, args.persona)
        print(f"✔ Equipo {args.serial} asignado a {args.persona}.")
    elif acc == "devolver":
        inventario.devolver(con, args.serial)
        print(f"✔ Equipo {args.serial} recibido y disponible.")
    elif acc == "reparacion":
        inventario.enviar_reparacion(con, args.serial, args.detalle)
        print(f"✔ Equipo {args.serial} enviado a reparación.")
    elif acc == "baja":
        inventario.dar_baja(con, args.serial, args.motivo)
        print(f"✔ Equipo {args.serial} dado de baja.")
    elif acc == "listar":
        imprimir_tabla(inventario.listar(con, args.estado),
                       ["serial", "tipo", "marca", "modelo", "estado", "asignado_a"])
    elif acc == "historial":
        imprimir_tabla(inventario.historial(con, args.serial), ["fecha", "accion", "detalle"])
    elif acc == "exportar":
        n = inventario.exportar_csv(con, args.archivo)
        print(f"✔ {n} equipos exportados a {args.archivo}.")


# ---------- Tickets ----------

def cmd_ticket(args, con):
    acc = args.accion
    if acc == "nuevo":
        tid = tickets.crear_ticket(con, args.solicitante, args.titulo, args.impacto,
                                   args.urgencia, args.descripcion or "", args.categoria)
        t = tickets.obtener(con, tid)
        print(f"✔ Ticket #{tid} creado | categoría: {t['categoria']} | prioridad: {t['prioridad']}")
    elif acc == "listar":
        imprimir_tabla(tickets.listar(con, args.estado),
                       ["id", "prioridad", "estado", "categoria", "solicitante", "titulo"])
    elif acc == "ver":
        t = tickets.obtener(con, args.id)
        for campo in t.keys():
            print(f"{campo:>12}: {t[campo] if t[campo] is not None else '-'}")
    elif acc == "tomar":
        tickets.tomar(con, args.id)
        print(f"✔ Ticket #{args.id} en progreso.")
    elif acc == "escalar":
        tickets.escalar(con, args.id, args.motivo)
        print(f"✔ Ticket #{args.id} escalado.")
    elif acc == "resolver":
        tickets.resolver(con, args.id, args.solucion)
        print(f"✔ Ticket #{args.id} resuelto y documentado.")


# ---------- Reporte / Diagnóstico / Demo ----------

def cmd_reporte(args, con):
    por_estado, por_prioridad = reportes.resumen(con)
    print("\n== Tickets por estado ==")
    imprimir_tabla(por_estado, ["estado", "total"])
    print("\n== Tickets abiertos por prioridad ==")
    imprimir_tabla(por_prioridad, ["prioridad", "total"])
    print("\n== Tiempo promedio de resolución (horas) ==")
    imprimir_tabla(reportes.tiempo_promedio_resolucion(con), ["categoria", "resueltos", "horas"])
    print(f"\n== Pedidos repetidos (≥{args.minimo} en {args.dias} días): oportunidades de automatizar ==")
    repetidos = reportes.pedidos_repetidos(con, args.minimo, args.dias)
    if not repetidos:
        print("(ninguno)")
    for categoria, total, sugerencia in repetidos:
        print(f"• {categoria} ({total} tickets) → {sugerencia}")


def cmd_diagnostico(args, con):
    print("Diagnóstico de red en curso...\n")
    pasos, (problema, recomendacion) = diagnostico.diagnosticar()
    for nombre, ok, detalle in pasos:
        print(f"{'✔' if ok else '✘'} {nombre}" + (f"\n    {detalle}" if detalle else ""))
    print(f"\nResultado: {problema}\n{recomendacion}")


def cmd_demo(args, con):
    """Carga datos de ejemplo para mostrar el sistema."""
    equipos = [
        ("LT-0001", "laptop", "Lenovo", "ThinkPad E14"),
        ("LT-0002", "laptop", "Apple", "MacBook Air M2"),
        ("LT-0003", "laptop", "Dell", "Latitude 5440"),
        ("SP-0001", "smartphone", "Samsung", "Galaxy A55"),
        ("MN-0001", "monitor", "LG", "24MK430"),
    ]
    for e in equipos:
        try:
            inventario.registrar_equipo(con, *e)
        except inventario.ErrorInventario:
            pass
    for serial, persona in (("LT-0001", "María Pérez"), ("SP-0001", "José Rodríguez")):
        try:
            inventario.asignar(con, serial, persona)
        except inventario.ErrorInventario:
            pass

    ejemplos = [
        ("María Pérez", "No me funciona el internet", "La laptop dice conectado al wifi pero no navega", 3, 2),
        ("Carlos Gómez", "Olvidé mi contraseña de Google", "", 3, 1),
        ("Ana Silva", "Necesito restablecer el MFA", "Cambié de teléfono y perdí el acceso", 3, 1),
        ("Luis Torres", "Usuario bloqueado", "Puse mal la clave varias veces", 3, 2),
        ("Pedro Díaz", "La impresora del piso 2 no imprime", "", 2, 2),
        ("Toda el área de Pagos", "Sin internet en el piso 3", "Nadie del piso navega", 1, 1),
        ("Sofía Ruiz", "Instalar Zoom", "Lo necesito para una reunión mañana", 3, 3),
    ]
    ids = [tickets.crear_ticket(con, *t[:2], t[3], t[4], t[2]) for t in ejemplos]
    tickets.resolver(con, ids[1], "Se envió enlace de restablecimiento desde la consola de Google Workspace.")
    tickets.escalar(con, ids[5], "Varios usuarios del piso 3 con IP 169.254.x.x. Posible falla del DHCP o del AP del piso.")
    print(f"✔ Datos de ejemplo cargados: {len(equipos)} equipos y {len(ejemplos)} tickets.")


def construir_parser():
    p = argparse.ArgumentParser(prog="itops", description="Mini sistema de IT Operations: inventario, tickets y diagnóstico de red.")
    p.add_argument("--db", help="Ruta de la base de datos (por defecto: itops.db)")
    sub = p.add_subparsers(dest="comando", required=True)

    # equipo
    pe = sub.add_parser("equipo", help="Inventario de equipos").add_subparsers(dest="accion", required=True)
    a = pe.add_parser("agregar"); a.add_argument("--serial", required=True)
    a.add_argument("--tipo", required=True, choices=inventario.TIPOS); a.add_argument("--marca"); a.add_argument("--modelo")
    a = pe.add_parser("asignar"); a.add_argument("serial"); a.add_argument("persona")
    a = pe.add_parser("devolver"); a.add_argument("serial")
    a = pe.add_parser("reparacion"); a.add_argument("serial"); a.add_argument("--detalle")
    a = pe.add_parser("baja"); a.add_argument("serial"); a.add_argument("--motivo", required=True)
    a = pe.add_parser("listar"); a.add_argument("--estado", choices=("disponible", "asignado", "reparacion", "baja"))
    a = pe.add_parser("historial"); a.add_argument("serial")
    a = pe.add_parser("exportar"); a.add_argument("archivo")

    # ticket
    pt = sub.add_parser("ticket", help="Tickets de soporte").add_subparsers(dest="accion", required=True)
    a = pt.add_parser("nuevo"); a.add_argument("--solicitante", required=True); a.add_argument("--titulo", required=True)
    a.add_argument("--descripcion"); a.add_argument("--categoria", choices=(*tickets.CATEGORIAS, "otro"))
    a.add_argument("--impacto", type=int, choices=(1, 2, 3), required=True, help="1=alto (muchos usuarios) 3=bajo (una persona)")
    a.add_argument("--urgencia", type=int, choices=(1, 2, 3), required=True, help="1=alta 3=baja")
    a = pt.add_parser("listar"); a.add_argument("--estado", choices=tickets.ESTADOS)
    a = pt.add_parser("ver"); a.add_argument("id", type=int)
    a = pt.add_parser("tomar"); a.add_argument("id", type=int)
    a = pt.add_parser("escalar"); a.add_argument("id", type=int); a.add_argument("--motivo", required=True)
    a = pt.add_parser("resolver"); a.add_argument("id", type=int); a.add_argument("--solucion", required=True)

    a = sub.add_parser("reporte", help="Métricas y pedidos repetidos")
    a.add_argument("--minimo", type=int, default=3); a.add_argument("--dias", type=int, default=30)
    sub.add_parser("diagnostico", help="Diagnóstico de red de este equipo")
    sub.add_parser("demo", help="Cargar datos de ejemplo")
    return p


COMANDOS = {"equipo": cmd_equipo, "ticket": cmd_ticket, "reporte": cmd_reporte,
            "diagnostico": cmd_diagnostico, "demo": cmd_demo}


def main(argv=None):
    args = construir_parser().parse_args(argv)
    con = conectar(args.db)
    try:
        COMANDOS[args.comando](args, con)
    except (inventario.ErrorInventario, tickets.ErrorTicket) as e:
        print(f"✘ {e}", file=sys.stderr)
        return 1
    finally:
        con.close()
    return 0
