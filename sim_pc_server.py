"""
sim_server.py  —  Servidor TCP de pruebas sin GUI (Windows/Linux/macOS)
Implementa toda la logica de protocolo de pc_server.py en consola pura.
Util para verificar el flujo completo antes de depurar la UI de Tkinter.

Uso:
    python sim_server.py          # corre servidor en 0.0.0.0:8001
"""

import socket
import threading
import random
import time

HOST   = "0.0.0.0"
PUERTO = 8001
FRASES = ["SOS","SI","NO","HOLA3","S+E","TEST","MORSE","TEC CR","8 PICO","ADIOS-1"]
BONUS  = [(2000,5),(4000,3),(999999,1)]

MORSE = {
    'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---',
    'K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-',
    'U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-','5':'.....','6':'-....','7':'--...','8':'---..',
    '9':'----.', '+':'.-.-.', '-':'-....-',
}


def puntaje(original, resp):
    o = original.upper().replace(' ','')
    r = resp.upper().replace(' ','')
    return sum(1 for i in range(min(len(o),len(r))) if o[i]==r[i])


def bonus_vel(ms, nc):
    msc = ms/nc if nc else 9999
    for lim, pts in BONUS:
        if msc < lim: return pts
    return 1


class ServidorPrueba:
    def __init__(self):
        self.cliente = None
        self.buf     = b''
        self.frase   = ""
        self.simple  = False
        self.pts_a = self.pts_b = 0
        self.ronda = 1
        self.resp_a = ""
        self.pts_a_r = self.pts_b_r = 0
        self.t_ini_a = self.t_ini_b = 0.0

    def run(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        srv.bind((HOST, PUERTO))
        srv.listen(1)
        print("[SERVER] Escuchando en {}:{}".format(HOST, PUERTO))
        while True:
            print("[SERVER] Esperando conexion del Pico...")
            self.cliente, addr = srv.accept()
            self.cliente.settimeout(1.0)
            self.buf = b''
            print("[SERVER] Pico conectado desde", addr)
            self._manejar()
            print("[SERVER] Pico desconectado\n")

    def tx(self, msg):
        if self.cliente:
            self.cliente.sendall((msg+'\n').encode())
            print("[PC --> PICO]", msg)

    def rx_loop(self):
        """Lee mensajes del Pico hasta que se desconecta."""
        while True:
            try:
                data = self.cliente.recv(1024)
                if not data:
                    break
                self.buf += data
                while b'\n' in self.buf:
                    line, self.buf = self.buf.split(b'\n',1)
                    msg = line.decode().strip()
                    if msg:
                        print("[PICO --> PC]", msg)
                        self._procesar(msg)
            except OSError:
                pass
            except Exception as e:
                print("[SERVER] Error:", e)
                break
        self.cliente.close()
        self.cliente = None

    def _manejar(self):
        self.rx_loop()

    def _procesar(self, msg):
        if msg == "LISTO":
            pass
        elif msg == "MODO:SIMPLE":
            self.simple = True
            print("[SERVER] Modo SIMPLE activo")
        elif msg == "MODO:ESCUCHA":
            self.simple = False
            print("[SERVER] Modo ESCUCHA activo")
            self._nueva_ronda()
        elif msg.startswith("MORSE:"):
            frase = msg[6:].strip()
            self.frase   = frase
            self.resp_a  = ""
            self.pts_a_r = 0
            self.t_ini_a = time.time()
            print("[SERVER] Frase del Pico: '{}'".format(frase))
            print("[SERVER] >>> Jugador A debe ingresar en Morse. Auto-simulando en 1s...")
            # En prueba: simular que A ingresa correctamente tras 1 s
            threading.Timer(1.0, self._simular_turno_a).start()
        elif msg.startswith("RESP:"):
            resp_b = msg[5:].strip()
            nc     = len(self.frase.replace(' ',''))
            base   = puntaje(self.frase, resp_b)
            bv     = bonus_vel((time.time()-self.t_ini_b)*1000, nc) if self.simple else 1
            self.pts_b_r = base + bv
            self.pts_b  += self.pts_b_r
            self.tx("PUNTAJE:{}".format(self.pts_b_r))
            self._mostrar_resultado(resp_b)

    def _nueva_ronda(self):
        self.frase   = random.choice(FRASES)
        self.resp_a  = ""
        self.pts_a_r = self.pts_b_r = 0
        self.t_ini_a = time.time()
        print("[SERVER] Nueva ronda {}. Frase: '{}'".format(self.ronda, self.frase))
        self.tx("FRASE:" + self.frase)
        print("[SERVER] >>> Jugador A debe ingresar Morse. Auto-simulando en 1s...")
        threading.Timer(1.0, self._simular_turno_a).start()

    def _simular_turno_a(self):
        """Simula que A ingresa la frase correcta (80% aciertos)."""
        clean  = self.frase.upper().replace(' ','')
        chars  = []
        for c in clean:
            chars.append(c if random.random() < 0.8
                         else random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ'))
        self.resp_a  = ''.join(chars)
        nc           = len(clean)
        base         = puntaje(self.frase, self.resp_a)
        bv           = bonus_vel((time.time()-self.t_ini_a)*1000, nc)
        self.pts_a_r = base + bv
        self.pts_a  += self.pts_a_r
        print("[SERVER] Jugador A ingreso: '{}' | puntaje: {}".format(
            self.resp_a, self.pts_a_r))
        self.t_ini_b = time.time()
        self.tx("INICIO")

    def _mostrar_resultado(self, resp_b):
        nc = len(self.frase.replace(' ',''))
        ba = puntaje(self.frase, self.resp_a)
        bb = puntaje(self.frase, resp_b)
        ganador = ("A" if self.pts_a_r > self.pts_b_r else
                   "B" if self.pts_b_r > self.pts_a_r else "EMPATE")
        print("\n[SERVER] ===== Resultado Ronda {} =====".format(self.ronda))
        print("  Frase:     '{}'".format(self.frase))
        print("  Resp A:    '{}' | {}/{} aciertos + bono = {}".format(
            self.resp_a, ba, nc, self.pts_a_r))
        print("  Resp B:    '{}' | {}/{} aciertos + bono = {}".format(
            resp_b, bb, nc, self.pts_b_r))
        print("  Ganador:   Jugador {}".format(ganador))
        print("  Acumulado: A={} B={}".format(self.pts_a, self.pts_b))
        print("==========================================\n")
        self.ronda += 1


if __name__ == "__main__":
    ServidorPrueba().run()
