# Maneja la conexion WiFi del Pico W.
# Las credenciales se cargan desde config.txt para no
# guardar contrasenas directamente en el codigo fuente.
# ============================================================

import network
import time

# Objeto global de la interfaz WiFi
_wlan = None


def _leer_config():
    """
    Lee SSID y PASSWORD desde el archivo config.txt.
    El archivo debe tener el formato:
        SSID=NombreDeLaRed
        PASSWORD=LaContrasena
        SERVER_IP=192.168.X.X
        SERVER_PORT=8001
    Devuelve un diccionario con los valores leidos.
    """
    config = {}
    try:
        with open('config.txt', 'r') as f:
            for linea in f:
                linea = linea.strip()  # quitar espacios y saltos de linea
                if '=' in linea:
                    clave, valor = linea.split('=', 1)  # separar en clave y valor
                    config[clave.strip()] = valor.strip()
    except Exception as e:
        print("Error leyendo config.txt:", e)
    return config


def conectar_wifi(timeout_seg=20):
    """
    Conecta el Pico W a la red WiFi especificada en config.txt.
    Devuelve True si la conexion fue exitosa, False si no.
    """
    global _wlan
    config = _leer_config()  # leer credenciales del archivo

    ssid     = config.get('SSID', '')
    password = config.get('PASSWORD', '')

    if not ssid:
        print("Error: SSID no encontrado en config.txt")
        return False

    try:
        _wlan = network.WLAN(network.STA_IF)  # modo estacion (cliente)
        _wlan.active(True)                     # activar interfaz WiFi

        if _wlan.isconnected():
            # Ya hay conexion previa activa
            print("Ya conectado a WiFi. IP:", _wlan.ifconfig()[0])
            return True

        _wlan.connect(ssid, password)  # iniciar conexion
        print("Conectando a", ssid, "...")

        t_inicio = time.time()  # registrar tiempo de inicio
        while not _wlan.isconnected():
            if time.time() - t_inicio > timeout_seg:
                # Se acabo el tiempo de espera
                print("Timeout: no se pudo conectar al WiFi")
                return False
            print("  Esperando conexion WiFi...")
            time.sleep(1)

        print("WiFi conectado. IP:", _wlan.ifconfig()[0])
        return True

    except Exception as e:
        print("Error en WiFi:", e)
        return False


def obtener_ip():
    """Devuelve la IP asignada al Pico, o '0.0.0.0' si no hay conexion."""
    if _wlan and _wlan.isconnected():
        return _wlan.ifconfig()[0]
    return '0.0.0.0'


def obtener_servidor():
    """
    Lee la IP y puerto del servidor desde config.txt.
    Devuelve una tupla (ip, puerto).
    """
    config = _leer_config()
    ip     = config.get('SERVER_IP', '192.168.1.100')
    puerto = int(config.get('SERVER_PORT', '8001'))
    return (ip, puerto)
