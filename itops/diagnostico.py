"""Diagnóstico de red de primer nivel: "No me funciona el internet".

Sigue el mismo orden que haría un técnico antes de escalar:
  1. ¿El equipo tiene una IP válida? (169.254.x.x = APIPA = no recibió IP del DHCP)
  2. ¿Hay salida a internet sin depender del DNS? (conexión TCP directa a una IP pública)
  3. ¿Funciona la resolución de nombres (DNS)?
  4. ¿Funciona la navegación web (HTTPS)?

Solo usa la librería estándar de Python, así funciona en Windows, macOS y Linux.
"""

import ipaddress
import socket
import urllib.request

TIMEOUT = 3


def obtener_ips_locales():
    """Devuelve las IPv4 del equipo (sin loopback)."""
    ips = set()
    try:
        # No envía paquetes: solo le pide al sistema la IP de la interfaz con ruta a internet.
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        for ip in socket.gethostbyname_ex(socket.gethostname())[2]:
            ips.add(ip)
    except OSError:
        pass
    return sorted(ip for ip in ips if not ipaddress.ip_address(ip).is_loopback)


def clasificar_ip(ip):
    """Explica qué significa una dirección IPv4."""
    direccion = ipaddress.ip_address(ip)
    if direccion.is_loopback:
        return "loopback", "Dirección local del propio equipo (127.x.x.x)."
    if direccion.is_link_local:
        return "apipa", ("APIPA (169.254.x.x): el equipo NO recibió IP del servidor DHCP. "
                         "Está conectado al Wi-Fi pero sin configuración de red válida.")
    if direccion.is_private:
        return "privada", "IP privada válida asignada por la red local."
    return "publica", "IP pública."


def probar_tcp(host="1.1.1.1", puerto=443, timeout=TIMEOUT):
    """Conexión directa a una IP pública: prueba salida a internet sin usar DNS."""
    try:
        with socket.create_connection((host, puerto), timeout=timeout):
            return True
    except OSError:
        return False


def probar_dns(nombre="www.google.com"):
    try:
        socket.setdefaulttimeout(TIMEOUT)
        return bool(socket.getaddrinfo(nombre, 443))
    except OSError:
        return False
    finally:
        socket.setdefaulttimeout(None)


def probar_https(url="https://www.google.com/generate_204", timeout=TIMEOUT):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as respuesta:
            return respuesta.status < 400
    except Exception:
        return False


def concluir(ips, tcp_ok, dns_ok, https_ok):
    """Lógica pura de decisión (separada de la red para poder probarla)."""
    tipos = [clasificar_ip(ip)[0] for ip in ips]
    if not ips or all(t == "apipa" for t in tipos):
        return ("DHCP / Wi-Fi",
                "El equipo no tiene una IP válida. Pasos: olvidar y reconectar la red Wi-Fi, "
                "renovar IP (Windows: ipconfig /release && ipconfig /renew). Si otros usuarios "
                "tienen el mismo problema, escalar a Infra: posible falla del servidor DHCP o "
                "pool de direcciones agotado.")
    if not tcp_ok:
        return ("Sin salida a internet",
                "Hay IP válida pero no hay salida. Revisar si otros usuarios están afectados; "
                "si es general, escalar a Infra (gateway, AP o enlace del proveedor).")
    if not dns_ok:
        return ("DNS",
                "Hay salida a internet pero no se resuelven nombres. Limpiar caché DNS "
                "(Windows: ipconfig /flushdns) y verificar servidores DNS. Escalar si es general.")
    if not https_ok:
        return ("Navegación web",
                "La red y el DNS funcionan pero la web no carga. Posible proxy, firewall o "
                "portal cautivo. Probar otro navegador y revisar configuración de proxy.")
    return ("Conexión OK",
            "La conexión funciona. El problema puede ser de un sitio o aplicación específica: "
            "preguntar al usuario qué sitio/app falla y desde cuándo.")


def diagnosticar():
    """Ejecuta las pruebas reales y devuelve (pasos, conclusión)."""
    ips = obtener_ips_locales()
    tcp_ok = probar_tcp()
    dns_ok = probar_dns()
    https_ok = probar_https() if (tcp_ok and dns_ok) else False

    detalle_ip = "; ".join(f"{ip} -> {clasificar_ip(ip)[1]}" for ip in ips) or "Sin IP IPv4"
    ip_ok = bool(ips) and any(clasificar_ip(ip)[0] != "apipa" for ip in ips)
    pasos = [
        ("1. Dirección IP", ip_ok, detalle_ip),
        ("2. Salida a internet (TCP 1.1.1.1:443)", tcp_ok, ""),
        ("3. Resolución DNS (www.google.com)", dns_ok, ""),
        ("4. Navegación HTTPS", https_ok, ""),
    ]
    return pasos, concluir(ips, tcp_ok, dns_ok, https_ok)
