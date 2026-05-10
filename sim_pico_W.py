"""
sim_pico.py  —  Simulador de Pico W para pruebas en PC (Windows/Linux)
Simula el lado del Pico: conecta a 127.0.0.1:8001 y ejecuta el protocolo
completo de ambos modos de juego, imprimiendo cada paso en consola.

Uso:
    1) Abrir pc_server.py (o sim_server.py para pruebas sin GUI).
    2) Correr: python sim_pico.py [simple|escucha]
"""

import socket
import time
import sys
import random

HOST   = "127.0.0.1"
PUERTO = 8001

MORSE_A_CHAR = {
    '.-':'A',  '-...':'B', '-.-.':'C', '-..':'D',  '.':'E',
    '..-.':'F','--.' :'G', '....':'H', '..':'I',   '.---':'J',
    '-.-':'K', '.-..':'L', '--':'M',   '-.':'N',   '---':'O',
    '.--.':'P','--.-':'Q', '.-.':'R',  '...':'S',  '-':'T',
    '..-':'U', '...-':'V', '.--':'W',  '-..-':'X', '-.--':'Y',
    '--..':'Z',
    '.----':'1','..---':'2','...--':'3','....-':'4','......':'5',  # noqa
    '-....':'6','--...':'7','---..':'8','----.':'9','-----':'0',
    '.-.-.':'+', '-....-':'-',
}
CHAR_A_MORSE = {v: k for k, v in MORSE_A_CHAR.items()}

FRASES = ["SOS","SI","NO","HOLA3","S+E","TEST","MORSE","TEC CR","8 PICO","ADIOS-1"]


def encode_morse(frase):
    """Codifica una frase a la secuencia de puntos/rayas como string."""
    return ''.join(CHAR_A_MORSE.get(c, '?') for c in frase.upper()
                   if c != ' ')


class SimPico:
    def __init__(self, modo_simple):
        self.modo_simple = modo_simple
        self.sock = None
        self.buf  = b''

    # ── TCP ──────────────────────────────────────────────────

    def conectar(self, reintentos=10, espera=2):
        for i in range(1, reintentos + 1):
            if self.sock:
                try: self.sock.close()
                except: pass
                self.sock = None
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.connect((HOST, PUERTO))
                s.settimeout(0.5)
                self.sock = s
                self.buf  = b''
                print("[PICO] TCP conectado a {}:{}".format(HOST, PUERTO))
                return True
            except Exception as e:
                print("[PICO] intento {}/{}: {}".format(i, reintentos, e))
                if i < reintentos:
                    time.sleep(espera)
        return False

    def tx(self, msg):
        time.sleep(0.05); self.sock.sendall((msg + '\n').encode())
        print("[PICO --> PC]", msg)

    def rx(self, timeout=15):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if b'\n' in self.buf:
                line, self.buf = self.buf.split(b'\n', 1)
                msg = line.decode().strip()
                print("[PC --> PICO]", msg)
                return msg
            try:
                data = self.sock.recv(1024)
                if data == b'':
                    return ''
                self.buf += data
            except OSError:
                pass
        print("[PICO] timeout esperando PC")
        return ''

    # ── Modos de juego ───────────────────────────────────────

    def ronda_simple(self):
        """Pico elige frase → muestra → espera INICIO → captura resp B."""
        self.tx("LISTO")
        self.tx("MODO:SIMPLE")

        frase = random.choice(FRASES)
        print("[PICO] Frase elegida:", frase)
        self.tx("MORSE:" + frase)

        msg = self.rx()
        if msg != "INICIO":
            print("[PICO] Error: esperaba INICIO, recibi:", msg)
            return

        # Simular respuesta B (correcta con 80% de chars)
        resp = _simular_resp(frase, aciertos=0.8)
        print("[PICO] Jugador B transmitio:", resp)
        self.tx("RESP:" + resp)

        puntaje = self.rx(timeout=10)
        print("[PICO] Puntaje recibido:", puntaje)

    def ronda_escucha(self):
        """PC elige frase → Pico la presenta → espera INICIO → resp B."""
        self.tx("LISTO")
        self.tx("MODO:ESCUCHA")

        msg = self.rx()
        if not msg.startswith("FRASE:"):
            print("[PICO] Error: esperaba FRASE:, recibi:", msg)
            return
        frase = msg[6:]
        print("[PICO] Frase del PC:", frase)

        msg = self.rx(timeout=60)   # esperar F1 del jugador A
        if msg != "INICIO":
            print("[PICO] Error: esperaba INICIO, recibi:", msg)
            return

        resp = _simular_resp(frase, aciertos=0.8)
        print("[PICO] Jugador B transmitio:", resp)
        self.tx("RESP:" + resp)

        puntaje = self.rx(timeout=10)
        print("[PICO] Puntaje recibido:", puntaje)

    def run(self, rondas=2):
        if not self.conectar():
            print("[PICO] Sin conexion, abortando")
            return
        for r in range(1, rondas + 1):
            print("\n[PICO] ===== Ronda {} =====".format(r))
            if self.modo_simple:
                self.ronda_simple()
            else:
                self.ronda_escucha()
            time.sleep(2)
        self.sock.close()
        print("[PICO] Simulacion terminada")


def _simular_resp(frase, aciertos=1.0):
    """Genera una respuesta simulada con 'aciertos' fraccion de chars correctos."""
    clean = frase.upper().replace(' ', '')
    res   = []
    for c in clean:
        if random.random() < aciertos:
            res.append(c)
        else:
            res.append(random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
    return ''.join(res)


if __name__ == "__main__":
    modo = sys.argv[1] if len(sys.argv) > 1 else "escucha"
    simple = (modo.lower() == "simple")
    print("[PICO] Modo:", "SIMPLE" if simple else "ESCUCHA")
    SimPico(simple).run(rondas=2)
