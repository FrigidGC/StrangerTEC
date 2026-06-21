# sumador_local_pico.py — StrangerTEC Morse Translator (Proyecto II)
#
# Prueba local del circuito incrementador en 5.
# Corre en el Pico desde Thonny, sin el juego ni WiFi.
#
# Aplica los valores de INICIO a 15 a los pines del circuito.
# La primera entrada dura PAUSA_INICIAL_MS para poder observarla,
# luego avanza de una en una con PAUSA_ENTRE_MS.
# La consola muestra que deben mostrar los LEDs en cada paso.
#
# Para probar desde un valor especifico cambiar INICIO:
#   0  -> recorre todo (0-15)
#   7  -> empieza en la mitad
#   11 -> solo los 5 casos de overflow
#
# Pines: GP0=A3(MSB)  GP13=A2  GP6=A1  GP4=A0(LSB)
# ============================================================

from machine import Pin
import time

# ── Cambiar antes de correr ───────────────────────────────────
INICIO           = 0
PAUSA_INICIAL_MS = 3000
PAUSA_ENTRE_MS   = 1000
# ─────────────────────────────────────────────────────────────

A3 = Pin(0,  Pin.OUT)
A2 = Pin(13, Pin.OUT)
A1 = Pin(6,  Pin.OUT)
A0 = Pin(4,  Pin.OUT)


def apagar():
    A3.value(0); A2.value(0); A1.value(0); A0.value(0)

def aplicar(v):
    A3.value((v >> 3) & 1)
    A2.value((v >> 2) & 1)
    A1.value((v >> 1) & 1)
    A0.value((v >> 0) & 1)

def correr():
    apagar()
    print()
    print("=" * 48)
    print("  Sumador local | Inicio={} | Pausa1={}ms | Entre={}ms".format(
        INICIO, PAUSA_INICIAL_MS, PAUSA_ENTRE_MS))
    print("  Entrada | A3 A2 A1 A0 | Salida | S3 S2 S1 S0")
    print("  " + "-" * 43)
    for v in range(INICIO, 16):
        s  = (v + 5) % 16
        bi = "{:04b}".format(v)
        bs = "{:04b}".format(s)
        aplicar(v)
        print("    {:2d}    |  {} {} {} {}  |   {:2d}   |  {} {} {} {}".format(
            v, bi[0],bi[1],bi[2],bi[3], s, bs[0],bs[1],bs[2],bs[3]))
        time.sleep_ms(PAUSA_INICIAL_MS if v == INICIO else PAUSA_ENTRE_MS)
    apagar()
    print("  Listo.")
    print("=" * 48)

correr()
