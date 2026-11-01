# ITOps Helpdesk 🛠️

Mini sistema de **IT Operations** por línea de comandos, hecho en Python (solo librería estándar, sin dependencias).
Cubre las tres tareas diarias de un equipo de IT: **inventario de equipos**, **tickets de soporte** y **diagnóstico de red**.

## ¿Qué problema resuelve?

| Problema real en IT | Cómo lo resuelve |
|---|---|
| Inventario en Excel desactualizado, nadie sabe quién tiene qué laptop | Registro de equipos con estados (disponible, asignado, reparación, baja) e **historial completo** de cada equipo |
| Tickets sin orden: se atiende al que más grita | Prioridad automática con **matriz impacto × urgencia** (estilo ITIL) y clasificación automática por categoría |
| Se resuelven problemas pero nadie documenta | **No se puede cerrar un ticket sin documentar la solución**, ni escalar sin explicar qué se revisó |
| Los mismos pedidos se repiten cada semana | Reporte que **detecta pedidos repetidos** y sugiere una automatización o artículo de autoservicio |
| "No me funciona el internet" | **Diagnóstico de red automático** en orden: IP (detecta APIPA 169.254.x.x) → salida a internet → DNS → HTTPS |

## Instalación

Requiere Python 3.9 o superior.

```bash
git clone https://github.com/Angel14157/itops-helpdesk.git
cd itops-helpdesk
python -m itops demo          # carga datos de ejemplo
```

## Uso

```bash
# Inventario
python -m itops equipo agregar --serial LT-0004 --tipo laptop --marca HP --modelo "ProBook 440"
python -m itops equipo asignar LT-0004 "Ana Silva"
python -m itops equipo devolver LT-0004
python -m itops equipo listar --estado disponible
python -m itops equipo historial LT-0004
python -m itops equipo exportar inventario.csv

# Tickets
python -m itops ticket nuevo --solicitante "Luis" --titulo "No me funciona el internet" --impacto 3 --urgencia 2
python -m itops ticket listar --estado abierto
python -m itops ticket tomar 1
python -m itops ticket escalar 1 --motivo "IP 169.254.x.x, renovar IP no funcionó, 3 usuarios afectados"
python -m itops ticket resolver 1 --solucion "Se reinició el AP del piso 3 y se renovó la IP"

# Reporte y diagnóstico
python -m itops reporte
python -m itops diagnostico
```

### Ejemplo: diagnóstico de red

```
✔ 1. Dirección IP
    192.168.0.115 -> IP privada válida asignada por la red local.
✔ 2. Salida a internet (TCP 1.1.1.1:443)
✔ 3. Resolución DNS (www.google.com)
✔ 4. Navegación HTTPS

Resultado: Conexión OK
```

### Ejemplo: pedidos repetidos

```
== Pedidos repetidos: oportunidades de automatizar ==
• accesos (3 tickets) → Habilitar autoservicio para restablecer contraseña/MFA y publicar una guía.
```

### Matriz de prioridad

| Impacto \ Urgencia | 1 Alta | 2 Media | 3 Baja |
|---|---|---|---|
| **1 Alto** (muchos usuarios) | P1 Crítica | P2 Alta | P3 Media |
| **2 Medio** (un equipo) | P2 Alta | P3 Media | P4 Baja |
| **3 Baja** (una persona) | P3 Media | P4 Baja | P4 Baja |

## Pruebas

```bash
python -m unittest discover -s tests -v
```

## Estructura

```
itops/
├── db.py           # Esquema SQLite
├── inventario.py   # Ciclo de vida de equipos + historial
├── tickets.py      # Clasificación, prioridad, escalamiento, cierre
├── reportes.py     # Métricas y detección de pedidos repetidos
├── diagnostico.py  # Diagnóstico de red paso a paso
└── cli.py          # Interfaz de línea de comandos
tests/              # Pruebas unitarias
```

## Próximas mejoras

- Interfaz web (Flask) para que los usuarios abran tickets sin usar la terminal.
- Notificaciones por Slack al crear o escalar un ticket.
- Exportar la base de conocimiento (soluciones documentadas) a Markdown.

---
Desarrollado por Ángel (Angel14157), estudiante de Ingeniería en Informática (UPTAMCA).
