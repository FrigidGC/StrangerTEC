# Cliente TCP que mantiene la conexion con el servidor PC.
# Todos los mensajes son texto plano en UTF-8 terminados en \n.

import socket
import time


class ServerComm:
    """Conexion TCP con el servidor en la PC."""

    TAM_BUFFER = 1024  # bytes maximos por mensaje

    def __init__(self, ip, puerto):
        self._ip     = ip      # IP del servidor PC
        self._puerto = puerto  # puerto TCP del servidor
        self._sock   = None    # socket de conexion (None = desconectado)

    def conectar(self, reintentos=3):
        """
        Intenta conectarse al servidor.
        Devuelve True si logra conectarse, False si falla.
        """
        for intento in range(1, reintentos + 1):
            try:
                # Crear nuevo socket TCP
                self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self._sock.connect((self._ip, self._puerto))  # conectar al servidor
                print("Conectado al servidor", self._ip, ":", self._puerto)
                return True
            except Exception as e:
                print("Intento", intento, "/", reintentos, "fallido:", e)
                self.cerrar()   # limpiar socket fallido
                time.sleep(1)   # esperar 1 segundo antes de reintentar
        return False

    def enviar(self, mensaje):
        """
        Envia un mensaje de texto al servidor.
        Se agrega \n al final como terminador de linea.
        Devuelve True si el envio fue exitoso.
        """
        if self._sock is None:
            print("Error: no hay conexion activa")
            return False
        try:
            # Codificar el mensaje a bytes y enviarlo
            self._sock.sendall((mensaje + '\n').encode('utf-8'))
            return True
        except Exception as e:
            print("Error al enviar:", e)
            return False

    def recibir(self, timeout_ms=8000):
        """
        Espera un mensaje del servidor con timeout.
        Devuelve el texto recibido (sin el \n), o '' si falla.
        """
        if self._sock is None:
            return ''
        try:
            # Configurar timeout en segundos
            self._sock.settimeout(timeout_ms / 1000.0)
            datos = self._sock.recv(self.TAM_BUFFER)  # recibir datos
            if datos: #Si la variable datos tiene datos sucede, en caso contrario es como un False
                return datos.decode('utf-8').strip()  # decodificar y limpiar
            return ''
        except OSError:
            return ''  # timeout o socket cerrado
        except Exception as e:
            print("Error al recibir:", e)
            return ''

    def cerrar(self):
        """Cierra el socket de forma segura."""
        if self._sock:
            try:
                self._sock.close()
            except Exception:
                pass  # ignorar errores al cerrar
            self._sock = None
