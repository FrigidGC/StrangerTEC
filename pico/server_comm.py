# Modulo de comunicacion con la PC via USB serie.
# Reemplaza la conexion TCP/WiFi original.
#
# Todos los mensajes son texto plano en UTF-8 terminados en \n.
# Usa sys.stdin y sys.stdout, que en el Pico W apuntan
# directamente al puerto USB CDC cuando esta conectado a la PC.
#
# Protocolo TCP (mensajes de texto plano):
#   PICO -> PC   "LISTO"              Pico listo para jugar
#   PICO -> PC   "MODO:SIMPLE"        Informa el modo activo
#   PICO -> PC   "MODO:ESCUCHA"       Informa el modo activo
#   PC   -> PICO "FRASE:<texto>"      PC envia la frase
#   PICO -> PC   "MORSE:<texto>"      Pico envia la frase seleccionada
#                                     para Modo Simple
#   PICO -> PC   "RESP:<texto>"       Respuesta del jugador B
#   PC   -> PICO "PUNTAJE:<n>"        Puntaje calculado por el PC
#   PC   -> PICO "INICIO"             Senial de inicio de transmision
# ============================================================

import sys
import select


class ServerComm:
    """Comunicacion USB serie con la PC (reemplaza TCP/WiFi)."""

    def __init__(self):
        # Crear objeto poll reutilizable para lecturas con timeout
        # select.poll() sobre sys.stdin permite esperar datos
        # durante un tiempo maximo sin bloquear el programa
        self._poll = select.poll()
        self._poll.register(sys.stdin, select.POLLIN)

    def conectar(self):
        """
        La conexion USB serie ya esta activa al arrancar el Pico.
        No se requiere ninguna accion adicional.
        Siempre devuelve True.
        """
        print("Comm: USB serie lista")
        return True

    def enviar(self, mensaje):
        """
        Envia un mensaje de texto al PC via USB serie.
        Se agrega \\n al final como terminador de linea.
        Devuelve True si el envio fue exitoso, False si falla.
        """
        try:
            # sys.stdout.write() envia directamente al puerto USB
            sys.stdout.write(mensaje + '\n')
            return True
        except Exception as e:
            print("Comm: error al enviar:", e)
            return False

    def recibir(self, timeout_ms=8000):
        """
        Espera un mensaje del PC con timeout via USB serie.
        Devuelve el texto recibido (sin el \\n), o '' si vence el tiempo.
        El argumento timeout_ms indica cuantos milisegundos esperar.
        """
        try:
            # poll.poll() bloquea hasta que haya datos o se agote el tiempo
            resultado = self._poll.poll(timeout_ms)
            if resultado:
                linea = sys.stdin.readline()  # leer una linea completa
                return linea.strip() if linea else ''
            return ''  # tiempo agotado sin recibir datos
        except Exception as e:
            print("Comm: error al recibir:", e)
            return ''

    def cerrar(self):
        """No hay socket que cerrar en USB serie."""
        pass
