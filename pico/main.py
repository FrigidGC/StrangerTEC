# main.py — StrangerTEC Morse Translator
# Punto de entrada del Pico. Lee el DIP-switch, inicializa
# el hardware y arranca el juego.
#
# Pines del Proyecto I:
#   GP26 = CLK  del 74HC164
#   GP27 = DATA del 74HC164
#   GP13 = Fila 1 del panel (A C E G I K M O Q S U W Y)
#   GP14 = Fila 2 del panel (B D F H J L N P R T V X Z)
#   GP15 = Fila 3 del panel (0 1 2 3 4 5 6 7 8 9 - +)
#   GP16 = Boton Morse S1
#   GP18 = DIP-switch S2 (OFF=simple, ON=escucha)
#   GP5  = Buzzer (PWM)
#
# Pines del Proyecto II (circuito incrementador en 5):
#   GP0  = A3 (MSB)   GP13 = A2   GP6 = A1   GP4 = A0 (LSB)
#   GP17 = Switch de habilitacion del circuito
#
# ATENCION: GP13 se usa en ambos proyectos. Verificar que el
# cableado fisico no cause conflicto.
# ============================================================

import machine
from led_panel   import PanelLEDs
from morse_input import LectorMorse
from game_logic  import Juego, UNIDAD_A_MS
from server_comm import ServerComm


def main():
    print("StrangerTEC Morse Translator")

    dip = machine.Pin(18, machine.Pin.IN, machine.Pin.PULL_DOWN)
    modo_simple = dip.value() == 0
    print("Modo:", "Simple" if modo_simple else "Escucha")

    panel = PanelLEDs(pin_clk=26, pin_data=27,
                      pin_row1=13, pin_row2=14, pin_row3=15)
    panel.apagar_todo()

    morse = LectorMorse(pin_boton=16, pin_buzzer=5, unidad_ms=UNIDAD_A_MS)

    comm = ServerComm()
    comm.conectar()

    juego = Juego(panel=panel, morse=morse, comm=comm, modo_simple=modo_simple)
    juego.iniciar()


main()
