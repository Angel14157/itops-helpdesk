import unittest

from itops import diagnostico, inventario, reportes, tickets
from itops.db import conectar


class PruebasInventario(unittest.TestCase):
    def setUp(self):
        self.con = conectar(":memory:")
        inventario.registrar_equipo(self.con, "LT-1", "laptop", "Lenovo", "E14")

    def test_ciclo_completo(self):
        inventario.asignar(self.con, "LT-1", "Ana")
        self.assertEqual(inventario.listar(self.con, "asignado")[0]["asignado_a"], "Ana")
        inventario.devolver(self.con, "LT-1")
        inventario.dar_baja(self.con, "LT-1", "Pantalla rota sin garantía")
        acciones = [h["accion"] for h in inventario.historial(self.con, "LT-1")]
        self.assertEqual(acciones, ["alta", "asignado", "devuelto", "baja"])

    def test_no_asigna_equipo_ocupado(self):
        inventario.asignar(self.con, "LT-1", "Ana")
        with self.assertRaises(inventario.ErrorInventario):
            inventario.asignar(self.con, "LT-1", "Luis")

    def test_no_da_baja_equipo_asignado(self):
        inventario.asignar(self.con, "LT-1", "Ana")
        with self.assertRaises(inventario.ErrorInventario):
            inventario.dar_baja(self.con, "LT-1", "x")

    def test_serial_duplicado(self):
        with self.assertRaises(inventario.ErrorInventario):
            inventario.registrar_equipo(self.con, "LT-1", "laptop")


class PruebasTickets(unittest.TestCase):
    def setUp(self):
        self.con = conectar(":memory:")

    def test_clasificacion(self):
        self.assertEqual(tickets.clasificar("No me funciona el internet"), "red")
        self.assertEqual(tickets.clasificar("Olvidé mi contraseña"), "accesos")
        self.assertEqual(tickets.clasificar("La impresora no imprime"), "impresora")
        self.assertEqual(tickets.clasificar("Necesito un crédito"), "otro")  # 'red' no es subcadena

    def test_prioridad(self):
        self.assertEqual(tickets.calcular_prioridad(1, 1), "P1-Critica")
        self.assertEqual(tickets.calcular_prioridad(3, 3), "P4-Baja")
        with self.assertRaises(tickets.ErrorTicket):
            tickets.calcular_prioridad(0, 1)

    def test_resolver_exige_documentar(self):
        tid = tickets.crear_ticket(self.con, "Ana", "Sin wifi", 3, 2)
        with self.assertRaises(tickets.ErrorTicket):
            tickets.resolver(self.con, tid, "")
        tickets.resolver(self.con, tid, "Se renovó la IP con ipconfig /renew")
        self.assertEqual(tickets.obtener(self.con, tid)["estado"], "resuelto")

    def test_escalar_exige_motivo(self):
        tid = tickets.crear_ticket(self.con, "Ana", "Sin wifi", 3, 2)
        with self.assertRaises(tickets.ErrorTicket):
            tickets.escalar(self.con, tid, "no sé")

    def test_pedidos_repetidos(self):
        for _ in range(3):
            tickets.crear_ticket(self.con, "X", "Olvidé mi contraseña", 3, 2)
        tickets.crear_ticket(self.con, "Y", "La impresora no imprime", 3, 2)
        repetidos = reportes.pedidos_repetidos(self.con, minimo=3)
        self.assertEqual([r[0] for r in repetidos], ["accesos"])


class PruebasDiagnostico(unittest.TestCase):
    def test_apipa(self):
        self.assertEqual(diagnostico.clasificar_ip("169.254.12.40")[0], "apipa")
        self.assertEqual(diagnostico.clasificar_ip("192.168.1.20")[0], "privada")

    def test_conclusiones(self):
        self.assertEqual(diagnostico.concluir(["169.254.12.40"], False, False, False)[0], "DHCP / Wi-Fi")
        self.assertEqual(diagnostico.concluir([], False, False, False)[0], "DHCP / Wi-Fi")
        self.assertEqual(diagnostico.concluir(["10.0.0.5"], False, False, False)[0], "Sin salida a internet")
        self.assertEqual(diagnostico.concluir(["10.0.0.5"], True, False, False)[0], "DNS")
        self.assertEqual(diagnostico.concluir(["10.0.0.5"], True, True, False)[0], "Navegación web")
        self.assertEqual(diagnostico.concluir(["10.0.0.5"], True, True, True)[0], "Conexión OK")


if __name__ == "__main__":
    unittest.main()
