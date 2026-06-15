# incremento5_pico.py
# Proyecto II - StrangerTEC Morse Translator
#
# Esto es la parte del Pico para el circuito incrementador en 5.
#
# La idea es sencilla: cuando un jugador mete un numero en Morse,
# tomamos el ASCII de ese numero, nos quedamos con los 4 bits
# de mas a la derecha (los LSB) y los mandamos tal cual a un
# circuito de compuertas logicas armado afuera del Pico.
#
# Ese circuito es el que hace la cuenta de +5 en hardware, y
# tiene sus propios 4 LEDs de salida. El Pico no lee esos LEDs
# ni hace ninguna suma: solo pone los 4 bits de entrada y avisa
# al PC por WiFi que numero se mando, para que el PC calcule
# el +5 por su lado y lo muestre en pantalla (debe coincidir
# con lo que se ve en los LEDs).
#
# Resumen del mensaje que se manda al PC (TCP, una linea por \n):
#   "INC5:SW:1:CHAR:3:ASCII:51:ENTRADA:0011"   -> switch ON, digito 3
#   "INC5:SW:0"                                 -> switch OFF
#
# Pines de entrada al circuito (Pico -> compuertas):
#   GP0 = A3 (el bit mas significativo)
#   GP1 = A2
#   GP2 = A1
#   GP3 = A0 (el bit menos significativo)
#
# Switch que activa/desactiva este modulo:
#   GP17, con pull-down interno (en ALTO = activado)
# ============================================================

import machine
import time
import network
import socket

# Datos de la red WiFi y del servidor en la PC.
# Cambiar aqui si la red o la IP del PC son distintas.
WIFI_SSID = "StrangerTEC_Red"
WIFI_PASS = "morse1234"
PC_IP     = "192.168.1.100"
PC_PUERTO = 9001

# Pines de entrada al circuito (en orden A3, A2, A1, A0)
PINES_ENTRADA = [0, 1, 2, 3]
PIN_SWITCH    = 17

# Solo los digitos 0-9 disparan el circuito
DIGITOS = "0123456789"


class CircuitoInc5:
    """
    Maneja la parte electrica del circuito: pone los 4 bits
    de entrada y revisa si el switch esta activado.

    No hace ninguna cuenta - eso es trabajo del circuito de
    compuertas que esta conectado a estos pines.
    """

    def __init__(self):
        self.pines = [machine.Pin(p, machine.Pin.OUT) for p in PINES_ENTRADA]
        self.switch = machine.Pin(PIN_SWITCH, machine.Pin.IN, machine.Pin.PULL_DOWN)
        self.apagar()

    def activado(self):
        """True si el switch esta en ON."""
        return self.switch.value() == 1

    def aplicar(self, valor):
        """
        Manda un numero de 0 a 15 a los pines A3 A2 A1 A0.
        El circuito de compuertas hace el resto.
        """
        for i, pin in enumerate(self.pines):
            pin.value((valor >> (3 - i)) & 1)

    def apagar(self):
        """Deja las 4 entradas en 0."""
        for pin in self.pines:
            pin.value(0)


class ConexionPC:
    """
    Se conecta a la red WiFi y abre un socket TCP hacia el PC
    para mandarle los resultados.
    """

    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.sock = None
        self.conectado = False

    def conectar(self, espera_max=15):
        print("Conectando a WiFi:", WIFI_SSID)
        self.wlan.active(True)
        self.wlan.connect(WIFI_SSID, WIFI_PASS)

        inicio = time.time()
        while not self.wlan.isconnected():
            if time.time() - inicio > espera_max:
                print("No se pudo conectar al WiFi")
                return False
            time.sleep_ms(200)

        print("WiFi conectado, IP del Pico:", self.wlan.ifconfig()[0])
        self.conectado = True
        return self._abrir_socket()

    def _abrir_socket(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.settimeout(10)
            self.sock.connect((PC_IP, PC_PUERTO))
            print("Conectado al servidor PC en", PC_IP, ":", PC_PUERTO)
            return True
        except Exception as e:
            print("No se pudo conectar al servidor PC:", e)
            self.sock = None
            return False

    def enviar(self, mensaje):
        """Manda una linea de texto al PC. Devuelve True/False."""
        if not self.sock:
            return False
        try:
            self.sock.send((mensaje + '\n').encode('utf-8'))
            return True
        except Exception as e:
            print("Error mandando al PC:", e)
            self.sock = None
            return False

    def cerrar(self):
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
            self.sock = None


class ModuloInc5:
    """
    Esta es la clase que se usa desde game_logic.py.

    Ejemplo de uso:

        from incremento5_pico import ModuloInc5

        inc5 = ModuloInc5()
        inc5.iniciar()              # conecta WiFi al arrancar

        # cada vez que se decodifica un caracter en Morse:
        inc5.procesar(caracter)
    """

    def __init__(self):
        self.circuito = CircuitoInc5()
        self.pc = ConexionPC()
        self.pc_listo = False

    def iniciar(self):
        """Intenta conectar al PC por WiFi. Si falla, el juego sigue igual."""
        self.pc_listo = self.pc.conectar()
        if self.pc_listo:
            print("Modulo Inc5 listo, conectado al PC")
        else:
            print("Modulo Inc5 sin conexion al PC (se sigue sin reportar)")
        return self.pc_listo

    def procesar(self, caracter):
        """
        Llamar esto cada vez que se decodifica un caracter en Morse,
        sin importar si viene del teclado del PC o del boton de la maqueta.

        - Si el switch esta apagado: apaga las entradas y avisa al PC.
        - Si esta encendido y el caracter es un digito: manda los
          4 bits al circuito y avisa al PC con el detalle.
        - Si esta encendido pero no es un digito: no hace nada.
        """
        if not self.circuito.activado():
            self.circuito.apagar()
            if self.pc_listo:
                self.pc.enviar("INC5:SW:0")
            return

        if caracter not in DIGITOS:
            return

        ascii_val = ord(caracter)
        entrada = ascii_val & 0x0F   # 4 bits LSB

        self.circuito.aplicar(entrada)

        bits = "{:04b}".format(entrada)
        print("Digito '{}' -> ASCII {} -> entrada al circuito {}".format(
            caracter, ascii_val, bits))

        if self.pc_listo:
            msg = "INC5:SW:1:CHAR:{}:ASCII:{}:ENTRADA:{}".format(
                caracter, ascii_val, bits)
            self.pc.enviar(msg)

    def cerrar(self):
        self.circuito.apagar()
        self.pc.cerrar()
