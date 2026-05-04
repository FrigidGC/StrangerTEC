# Controla los 13 LEDs de columna via dos registros de
# corrimiento 74HC164 encadenados, mas los 3 LEDs de fila
# conectados directamente al Pico.
#
# Cableado de los 74HC164 (segun diagrama):
#   GP27 --> A y B del IC1  (entrada de datos)
#   GP26 --> CLK del IC1 y IC2 (en paralelo)
#   CLR  --> VCC (siempre activo, no se controla por software)
#   QH del IC1 --> A y B del IC2 (cadena en serie)
#
# LEDs de columna (13 en total):
#   IC1: QA=LED1, QB=LED2, QC=LED3, QD=LED4, QE=LED5,
#        QF=LED6, QG=LED7, QH=LED8
#   IC2: QA=LED9, QB=LED10, QC=LED11, QD=LED12, QE=LED13
#
# LEDs de fila (3 en total, pines directos del Pico):
#   GP13 = LED14 = Fila 1 (A,C,E,G,I,K,M,O,Q,S,U,W,Y)
#   GP14 = LED15 = Fila 2 (B,D,F,H,J,L,N,P,R,T,V,X,Z)
#   GP15 = LED16 = Fila 3 (0,1,2,3,4,5,6,7,8,9,-,+)
#
# Para encender un LED especifico se activa la columna
# (registro de corrimiento) y la fila (GPIO directo).
# ============================================================

import machine
import time

# --- Tabla de caracteres ---
# Cada entrada es (columna, fila):
#   columna = indice de bit en el registro (0=LED1 ... 12=LED13)
#   fila    = 0 (GP13), 1 (GP14) o 2 (GP15)
CHAR_MAP = {
    # Fila 1 - GP13
    'A':(0,0),  'C':(1,0),  'E':(2,0),  'G':(3,0),
    'I':(4,0),  'K':(5,0),  'M':(6,0),  'O':(7,0),
    'Q':(8,0),  'S':(9,0),  'U':(10,0), 'W':(11,0), 'Y':(12,0),
    # Fila 2 - GP14
    'B':(0,1),  'D':(1,1),  'F':(2,1),  'H':(3,1),
    'J':(4,1),  'L':(5,1),  'N':(6,1),  'P':(7,1),
    'R':(8,1),  'T':(9,1),  'V':(10,1), 'X':(11,1), 'Z':(12,1),
    # Fila 3 - GP15
    '0':(0,2),  '1':(1,2),  '2':(2,2),  '3':(3,2),
    '4':(4,2),  '5':(5,2),  '6':(6,2),  '7':(7,2),
    '8':(8,2),  '9':(9,2),  '-':(10,2), '+':(11,2),
}


class PanelLEDs:
    """Maneja los registros de corrimiento y los LEDs de fila."""

    NUM_COLS = 13  # columnas controladas por los dos ICs

    def __init__(self, pin_clk, pin_data, pin_row1, pin_row2, pin_row3):
        # Configurar pin de reloj del registro de corrimiento
        self._clk  = machine.Pin(pin_clk,  machine.Pin.OUT)
        # Configurar pin de datos del registro de corrimiento
        self._data = machine.Pin(pin_data, machine.Pin.OUT)
        # Configurar los tres pines de fila como salida
        self._rows = [
            machine.Pin(pin_row1, machine.Pin.OUT),  # Fila 1
            machine.Pin(pin_row2, machine.Pin.OUT),  # Fila 2
            machine.Pin(pin_row3, machine.Pin.OUT),  # Fila 3
        ]
        # Inicializar todo en bajo
        self._clk.off()
        self._data.off()
        for r in self._rows:
            r.off()

    # ── Bajo nivel ───────────────────────────────────────

    def _pulso_clk(self):
        # Genera un pulso corto de reloj para avanzar el registro
        self._clk.on()
        time.sleep_us(2)  # 2 microsegundos es suficiente
        self._clk.off()
        time.sleep_us(2)

    def _enviar_columnas(self, col_bits):
        # Envia 13 bits al registro de corrimiento
        # El 74HC164 es SIPO: el primer bit que entra queda en QH
        # Por eso se envia en orden inverso (del bit 12 al 0)
        # asi el bit 0 queda en QA (LED1) al final
        for i in range(self.NUM_COLS - 1, -1, -1):
            # Poner el bit i en la linea de datos
            self._data.value(col_bits[i])
            self._pulso_clk()

    # ── API publica ──────────────────────────────────────

    def apagar_todo(self):
        """Apaga todos los LEDs (columnas y filas)."""
        # Enviar ceros a todos los bits del registro
        self._enviar_columnas([0] * self.NUM_COLS)
        # Apagar todos los pines de fila
        for r in self._rows:
            r.off()

    def encender_letra(self, letra):
        """
        Enciende el LED correspondiente a la letra indicada.
        El LED queda encendido hasta llamar apagar_todo().
        """
        c = letra.upper()  # convertir a mayuscula
        if c not in CHAR_MAP:
            return  # caracter no soportado, no hacer nada
        col, fila = CHAR_MAP[c]  # obtener columna y fila
        bits = [0] * self.NUM_COLS  # empezar con todos apagados
        bits[col] = 1               # encender solo la columna correcta
        self.apagar_todo()           # apagar lo anterior
        self._enviar_columnas(bits)  # activar la columna
        self._rows[fila].on()        # activar la fila

    def mostrar_frase_leds(self, frase, unidad_ms):
        """
        Muestra la frase en el panel LED letra por letra,
        encendiendo cada LED por 3 unidades de tiempo Morse.
        """
        pausa_letra  = 3 * unidad_ms  # tiempo entre letras
        pausa_espacio = 7 * unidad_ms  # tiempo para espacios entre palabras

        for c in frase.upper():
            if c == ' ':
                # Espacio entre palabras: apagar y esperar 7 unidades
                self.apagar_todo()
                time.sleep_ms(pausa_espacio)
                continue
            if c in CHAR_MAP:
                self.encender_letra(c)       # encender LED de la letra
                time.sleep_ms(pausa_letra)   # mantenerlo encendido
                self.apagar_todo()           # apagar
                time.sleep_ms(unidad_ms)     # pausa entre letras (1 unidad)

    def animacion_inicio(self):
        """Barre todos los LEDs de izquierda a derecha al encender."""
        for i in range(self.NUM_COLS):
            bits = [0] * self.NUM_COLS
            bits[i] = 1             # encender columna i
            self._enviar_columnas(bits)
            for r in self._rows:    # encender todas las filas
                r.on()
            time.sleep_ms(50)
            self.apagar_todo()
        time.sleep_ms(200)
