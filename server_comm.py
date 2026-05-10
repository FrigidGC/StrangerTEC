# Comunicacion del Pico W con el servidor PC via TCP/IP (WiFi).
# El Pico actua como cliente TCP; el PC actua como servidor.
# Basado en raspyConnection.py provisto por la catedra.
#
#
# Protocolo (texto plano, terminado en \n):
#   PICO -> PC   "LISTO"           PICO -> PC   "MODO:SIMPLE"
#   PICO -> PC   "MODO:ESCUCHA"    PC   -> PICO "FRASE:<texto>"
#   PICO -> PC   "MORSE:<texto>"   PICO -> PC   "RESP:<texto>"
#   PC   -> PICO "PUNTAJE:<n>"     PC   -> PICO "INICIO"
# ============================================================

import socket
import time


IP_SERVIDOR = "192.168.8.134"  # IP del PC servidor (ajustar segun red)
PUERTO      = 8001             # mismo puerto que server.py del profesor


class ServerComm:
    """
    Cliente TCP que conecta el Pico W al servidor PC.
    Usa recv(1024) con buffer igual que raspyConnection.py del profesor.
    """

    def __init__(self, buzzer=None):
        self._sock = None    # socket TCP activo
        self._buf  = b''     # fragmentos recibidos pendientes de procesar
        self._buz  = buzzer  # instancia de LectorMorse para feedback auditivo

    # ── Helpers de buzzer ─────────────────────────────────────

    def _pip(self, hz, ms):
        """Emite un tono de 'ms' ms a 'hz' Hz si hay buzzer disponible."""
        if self._buz is None:
            return
        self._buz._buz.freq(hz)
        self._buz.buzzer_on()
        time.sleep_ms(ms)
        self._buz.buzzer_off()
        # Restaurar la frecuencia Morse normal
        self._buz._buz.freq(self._buz.FREC_BUZZER)
        time.sleep_ms(30)   # pequena pausa entre pips

    def _beep_conectando(self):
        """Pip corto neutro: inicio de un intento de conexion."""
        self._pip(500, 60)

    def _beep_tcp_ok(self):
        """Dos pips ascendentes: TCP conectado correctamente."""
        self._pip(700, 80)
        self._pip(1050, 130)

    def _beep_tcp_fallo(self):
        """Pip grave: intento de conexion fallido."""
        self._pip(280, 90)

    def _beep_sin_tcp(self):
        """Tres pips graves: sin conexion tras todos los reintentos."""
        for _ in range(3):
            self._pip(220, 110)

    def _beep_msg_enviado(self):
        """Pip muy corto y agudo: mensaje enviado al PC."""
        self._pip(1100, 35)

    def _beep_msg_recibido(self):
        """Pip corto medio: mensaje recibido del PC."""
        self._pip(880, 50)

    def _beep_error_tx(self):
        """Pip grave corto: error al enviar un mensaje."""
        self._pip(260, 100)

    def _beep_desconectado(self):
        """Pip grave largo: servidor cerro la conexion."""
        self._pip(220, 200)

    # ── Conexion ──────────────────────────────────────────────

    def conectar(self, reintentos=10, espera_seg=2):
        """
        Intenta conectar al servidor PC via TCP.

        CORRECCION ECONNABORTED: en MicroPython el stack lwIP no libera
        el descriptor interno a tiempo aunque se llame .close(). La solucion
        es usar socket.getaddrinfo() en cada intento (patron del profesor):
        esto fuerza a lwIP a resolver la direccion y asignar un descriptor
        completamente nuevo en cada iteracion, evitando ECONNABORTED.

        Devuelve True si tiene exito, False si falla tras todos los reintentos.
        """
        for intento in range(1, reintentos + 1):
            # Cerrar socket anterior si existe
            if self._sock is not None:
                try:
                    self._sock.close()
                except Exception:
                    pass
                self._sock = None

            self._beep_conectando()
            print("TCP intento {}/{}...".format(intento, reintentos))
            try:
                # getaddrinfo() fuerza un descriptor nuevo en cada intento
                # (patron identico al connectToPC() del profesor)
                addr_info = socket.getaddrinfo(IP_SERVIDOR, PUERTO)
                addr      = addr_info[0][-1]
                sock      = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.connect(addr)
                sock.settimeout(0.5)
                self._sock = sock
                self._buf  = b''
                print("TCP OK con {}:{}".format(IP_SERVIDOR, PUERTO))
                self._beep_tcp_ok()
                return True
            except Exception as e:
                print("TCP intento {}/{}: {}".format(intento, reintentos, e))
                self._beep_tcp_fallo()
                if intento < reintentos:
                    time.sleep(espera_seg)

        self._beep_sin_tcp()
        return False

    # ── Envio ─────────────────────────────────────────────────

    def enviar(self, mensaje):
        """
        Envia un mensaje al PC terminado en \\n.
        Devuelve True si tiene exito, False si falla.
        """
        if not self._sock:
            return False
        try:
            self._sock.sendall((mensaje + '\n').encode())
            print("PICO ->", mensaje)
            self._beep_msg_enviado()
            return True
        except Exception as e:
            print("Error TX:", e)
            self._beep_error_tx()
            return False

    # ── Recepcion ─────────────────────────────────────────────

    def recibir(self, timeout_ms=120000):
        """
        Espera un mensaje completo del PC (linea terminada en \\n).
        Acumula datos en buffer interno con recv(1024).
        Devuelve el texto sin \\n ni espacios, o '' si vence el timeout.
        """
        if not self._sock:
            return ''
        inicio = time.ticks_ms()
        while True:
            # Si ya hay una linea completa en el buffer, extraerla
            if b'\n' in self._buf:
                linea, self._buf = self._buf.split(b'\n', 1)
                msg = linea.decode('utf-8', 'ignore').strip()
                if msg:
                    print("PC -> PICO:", msg)
                    self._beep_msg_recibido()
                return msg

            # Verificar timeout global del juego
            if time.ticks_diff(time.ticks_ms(), inicio) >= timeout_ms:
                return ''

            # Intentar leer mas datos del socket
            try:
                datos = self._sock.recv(1024)
                if datos:
                    self._buf += datos
                elif datos == b'':
                    # recv retorna b'' cuando el servidor cerro la conexion
                    print("Servidor cerro la conexion")
                    self._beep_desconectado()
                    self.cerrar()
                    return ''
            except OSError:
                # OSError aqui = timeout de 0.5 s sin datos nuevos
                # No es un error; el Pico sigue esperando al jugador
                pass

    # ── Cierre ────────────────────────────────────────────────

    def cerrar(self):
        """Cierra el socket TCP y limpia el buffer."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None
            self._buf  = b''
