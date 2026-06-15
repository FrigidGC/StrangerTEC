# Punto de entrada del sistema empotrado.
# Lee el DIP-switch para elegir el modo de juego,
# inicializa el hardware y arranca el bucle del juego.
#
# Comunicacion con la PC via USB serie (sys.stdin / sys.stdout).
# No se usa WiFi ni conexion TCP.
#
# Pines del hardware (segun diagrama):
#   GP26 --> CLK  de los 74HC164 (en paralelo IC1 e IC2)
#   GP27 --> A/B  del IC1 (entrada de datos)
#   CLR  --> VCC (fijo, no se controla por software)
#   GP13 --> LED14 (fila 1: A,C,E,G,I,K,M,O,Q,S,U,W,Y)
#   GP14 --> LED15 (fila 2: B,D,F,H,J,L,N,P,R,T,V,X,Z)
#   GP15 --> LED16 (fila 3: 0,1,2,3,4,5,6,7,8,9,-,+)
#   GP16 --> Boton Morse S1 (PULL_DOWN, activo en ALTO)
#   GP18 --> DIP-switch S2 (PULL_DOWN, activo en ALTO)
#   GP5  --> Buzzer LS1 (PWM)
#
# Modos de juego (DIP-switch S2):
#   OFF (0) = Modo Transmision Simple
#   ON  (1) = Modo Escucha y Transmision
# ============================================================

import machine
import time

# Modulos propios del proyecto
from led_panel   import PanelLEDs
from morse_input import LectorMorse
from game_logic  import Juego, UNIDAD_A_MS
from server_comm import ServerComm

# ── Asignacion de pines (ajustar si el cableado difiere) ──
PIN_CLK    = 26   # reloj del 74HC164
PIN_DATA   = 27   # datos del 74HC164
PIN_FILA1  = 13   # LED14, fila 1 del panel
PIN_FILA2  = 14   # LED15, fila 2 del panel
PIN_FILA3  = 15   # LED16, fila 3 del panel
PIN_BOTON  = 16   # boton Morse S1
PIN_DIP    = 18   # DIP-switch S2 (modo de juego)
PIN_BUZZER = 5    # buzzer pasivo LS1 (PWM)


def main():
    print("==============================")
    print(" StrangerTEC Morse Translator ")
    print("==============================")

    # ── 1. Leer el modo de juego desde el DIP-switch ──
    dip = machine.Pin(PIN_DIP, machine.Pin.IN, machine.Pin.PULL_DOWN)
    modo_simple = dip.value() == 0  # OFF = Transmision Simple, ON = Escucha
    if modo_simple:
        print("Modo: Transmision Simple (DIP OFF)")
    else:
        print("Modo: Escucha y Transmision (DIP ON)")

    # ── 2. Inicializar panel de LEDs ──
    panel = PanelLEDs(
        pin_clk  = PIN_CLK,
        pin_data = PIN_DATA,
        pin_row1 = PIN_FILA1,
        pin_row2 = PIN_FILA2,
        pin_row3 = PIN_FILA3,
    )
    panel.apagar_todo()  # asegurarse de que todo este apagado

    # ── 3. Inicializar lector Morse y buzzer ──
    morse = LectorMorse(
        pin_boton  = PIN_BOTON,
        pin_buzzer = PIN_BUZZER,
        unidad_ms  = UNIDAD_A_MS,  # se puede cambiar a UNIDAD_B_MS
    )

    # ── 4. Inicializar comunicacion USB serie con la PC ──
    # La conexion USB esta siempre disponible; no se necesita WiFi
    comm = ServerComm()
    comm.conectar()

    # ── 5. Iniciar el juego ──
    juego = Juego(
        panel       = panel,
        morse       = morse,
        comm        = comm,
        modo_simple = modo_simple,
    )
    juego.iniciar()  # bucle infinito del juego


# Ejecutar al arrancar el Pico
# CORRECCION: la llamada a main() debe estar a nivel de modulo,
# sin sangria, para que MicroPython la ejecute al iniciar
main()
