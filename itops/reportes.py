"""Reportes: detecta pedidos repetidos y sugiere automatizaciones o artículos de autoservicio."""

SUGERENCIAS = {
    "accesos": "Habilitar autoservicio para restablecer contraseña/MFA y publicar una guía "
               "paso a paso en la base de conocimiento.",
    "red": "Publicar guía de autodiagnóstico y pedir al usuario ejecutar "
           "'python -m itops diagnostico'. Si se repite en la misma zona, revisar AP y pool DHCP.",
    "impresora": "Crear artículo de instalación de impresoras y un script de despliegue de drivers.",
    "software": "Agregar el software al catálogo de instalación automática del MDM.",
    "hardware": "Verificar si las fallas se concentran en un mismo modelo o lote para gestionar garantía.",
    "otro": "Revisar los tickets manualmente y crear una categoría nueva si el patrón continúa.",
}


def resumen(con):
    """Cantidad de tickets por estado y por prioridad."""
    por_estado = con.execute(
        "SELECT estado, COUNT(*) AS total FROM tickets GROUP BY estado ORDER BY estado"
    ).fetchall()
    por_prioridad = con.execute(
        "SELECT prioridad, COUNT(*) AS total FROM tickets WHERE estado != 'resuelto' "
        "GROUP BY prioridad ORDER BY prioridad"
    ).fetchall()
    return por_estado, por_prioridad


def tiempo_promedio_resolucion(con):
    """Horas promedio de resolución por categoría (solo tickets resueltos)."""
    return con.execute(
        """SELECT categoria,
                  COUNT(*) AS resueltos,
                  ROUND(AVG((julianday(cerrado_en) - julianday(creado_en)) * 24), 1) AS horas
           FROM tickets WHERE estado = 'resuelto'
           GROUP BY categoria ORDER BY horas DESC"""
    ).fetchall()


def pedidos_repetidos(con, minimo=3, dias=30):
    """Categorías con `minimo` tickets o más en los últimos `dias`, con una sugerencia de mejora."""
    filas = con.execute(
        """SELECT categoria, COUNT(*) AS total FROM tickets
           WHERE creado_en >= datetime('now', 'localtime', ?)
           GROUP BY categoria HAVING COUNT(*) >= ?
           ORDER BY total DESC""",
        (f"-{int(dias)} days", minimo),
    ).fetchall()
    return [(f["categoria"], f["total"], SUGERENCIAS.get(f["categoria"], SUGERENCIAS["otro"]))
            for f in filas]
