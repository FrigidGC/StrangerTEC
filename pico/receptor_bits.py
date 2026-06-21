# receptor_bits.py — StrangerTEC Proyecto II
#
# Servidor TCP del Pico para el circuito incrementador en 5.
# Espera mensajes "BITS:xxxx\n" del PC y aplica esos 4 bits
# a los pines del circuito de compuertas logicas.
#
# El PC ya calculo los bits (ver sumador_pc.py). El Pico no
# decide nada, solo los escribe en los pines.
#
# Formato del mensaje:  "BITS:0011\n"  -> A3=0 A2=0 A1=1 A0=1
#
# Pines: GP0=A3(MSB)  GP13=A2  GP6=A1  GP4=A0(LSB)
#
# COMO ACTIVAR ESTE MODO EN EL PICO:
#   Este archivo se ejecuta aparte del juego (main.py).
#   Para activarlo, subirlo a Thonny y darle Run directamente
#   (no hace falta tocar main.py ni renombrar nada).
#   Mientras este programa corre, el juego normal no esta activo.
# ============================================================

from machine import Pin
import network, socket, time

WIFI_SSID = "StrangerTEC_Red"
WIFI_PASS = "morse1234"
PUERTO    = 9002

A3 = Pin(0,  Pin.OUT)
A2 = Pin(13, Pin.OUT)
A1 = Pin(6,  Pin.OUT)
A0 = Pin(4,  Pin.OUT)


def apagar():
    A3.value(0); A2.value(0); A1.value(0); A0.value(0)

def aplicar(bits):
    """bits: string de 4 caracteres '0'/'1', ej. '0011'"""
    A3.value(int(bits[0]))
    A2.value(int(bits[1]))
    A1.value(int(bits[2]))
    A0.value(int(bits[3]))


def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(WIFI_SSID, WIFI_PASS)
    print("Conectando a WiFi...")
    t = time.time()
    while not wlan.isconnected():
        if time.time() - t > 15:
            print("Sin WiFi")
            return False
        time.sleep_ms(200)
    print("WiFi OK, IP del Pico:", wlan.ifconfig()[0])
    return True


def escuchar():
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('', PUERTO))
    srv.listen(5)
    print("Modo circuito activo. Escuchando en puerto", PUERTO)

    while True:
        conn, addr = srv.accept()
        print("PC conectado:", addr)
        buf = b''
        try:
            while True:
                dato = conn.recv(32)
                if not dato:
                    break
                buf += dato
                while b'\n' in buf:
                    linea, buf = buf.split(b'\n', 1)
                    msg = linea.decode('utf-8', errors='replace').strip()
                    if msg.startswith("BITS:") and len(msg) == 9 \
                            and all(b in '01' for b in msg[5:]):
                        bits = msg[5:]
                        aplicar(bits)
                        print("Bits aplicados:", bits)
                    else:
                        print("Mensaje invalido:", msg)
        except Exception as e:
            print("Error de conexion:", e)
        finally:
            conn.close()
            apagar()


apagar()
if conectar_wifi():
    escuchar()
