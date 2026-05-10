# pc_server.py  —  StrangerTEC Morse Translator
# Servidor TCP + interfaz Tkinter para Windows.
# Protocolo (texto plano terminado en \n):
#   PICO->PC  LISTO | MODO:SIMPLE | MODO:ESCUCHA | MORSE:<f> | RESP:<r>
#   PC->PICO  FRASE:<f> | INICIO | PUNTAJE:<n>
# ============================================================

import socket, threading, time, random, tkinter as tk, winsound

# ── Constantes ────────────────────────────────────────────────
HOST, PUERTO = "0.0.0.0", 8001
UNIDAD_MS    = 200

FRASES = ["SOS","SI","NO","HOLA3","S+E","TEST","MORSE","TEC CR","8 PICO","ADIOS-1"]

MORSE = {
    'A':'.-','B':'-...','C':'-.-.','D':'-..','E':'.','F':'..-.','G':'--.','H':'....','I':'..','J':'.---',
    'K':'-.-','L':'.-..','M':'--','N':'-.','O':'---','P':'.--.','Q':'--.-','R':'.-.','S':'...','T':'-',
    'U':'..-','V':'...-','W':'.--','X':'-..-','Y':'-.--','Z':'--..',
    '0':'-----','1':'.----','2':'..---','3':'...--','4':'....-',
    '5':'.....','6':'-....','7':'--...','8':'---..', '9':'----.',
    '+':'.-.-.', '-':'-....-',
}
MORSE_INV = {v:k for k,v in MORSE.items()}
BONUS     = [(2000,5),(4000,3),(999999,1)]

BG,AM,RJ,VD,GR,BL,AZ = "black","yellow","red","lime","#444","white","#4fc3f7"
FILAS = [list("ACEGIKMOQSUWY"), list("BDFHJLNPRTVXZ"), list("0123456789-+")]

# ── Audio ─────────────────────────────────────────────────────
def _beep(*seq):
    threading.Thread(target=lambda:[winsound.Beep(h,m) for h,m in seq], daemon=True).start()

punto    = lambda: _beep((880, 80))
raya     = lambda: _beep((660,210))
ok_snd   = lambda: _beep((660,60),(880,80))
err_snd  = lambda: _beep((300,110),(220,130))
enviada  = lambda: _beep((523,80),(659,80),(784,80))
victoria = lambda: _beep((523,80),(659,80),(784,80),(1047,180))
empate   = lambda: _beep((440,110),(440,110))

# ── Puntuacion ────────────────────────────────────────────────
def _puntos(orig, resp):
    o,r = orig.upper().replace(' ',''), resp.upper().replace(' ','')
    return sum(o[i]==r[i] for i in range(min(len(o),len(r))))

def _bonus(ms, nc):
    msc = ms/nc if nc else 9999
    for lim,pts in BONUS:
        if msc < lim: return pts
    return 1

# ── App ───────────────────────────────────────────────────────
class App:
    def __init__(self, root):
        self.root = root
        root.title("StrangerTEC — Morse Translator")
        root.configure(bg=BG)
        root.resizable(False, False)

        # Estado
        self.frase = self.resp_a = ""
        self.pts_a = self.pts_b = self.pts_ar = self.pts_br = 0
        self.ronda = 1
        self.simple = self.turno_a = self.a_ok = self.b_ok = False
        self.buf_sym = self.buf_let = ""
        self.pulsado = False
        self.t_press = self.t_a = self.t_b = 0.0
        self.cliente = None
        self.leds    = {}

        self._build_ui()
        self._set_interactivo(False)
        threading.Thread(target=self._tcp_loop, daemon=True).start()

    # ── Bloqueo UI ────────────────────────────────────────────

    def _set_interactivo(self, on):
        st = tk.NORMAL if on else tk.DISABLED
        for w in self._controles:
            try: w.config(state=st)
            except: pass
        if on:
            self.root.bind("<KeyPress-space>",   self._press)
            self.root.bind("<KeyRelease-space>", self._release)
            self.root.bind("<Return>", lambda _: self._confirmar())
            self.root.bind("<F1>",     lambda _: self._enviar_a())
        else:
            for ev in ("<KeyPress-space>","<KeyRelease-space>","<Return>","<F1>"):
                self.root.unbind(ev)

    # ── TCP ───────────────────────────────────────────────────

    def _tcp_loop(self):
        srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            srv.bind((HOST, PUERTO))
        except OSError as e:
            self.root.after(0, lambda: self.lbl_estado.config(
                text="ERROR al abrir puerto {}: {}".format(PUERTO,e), fg=RJ))
            return
        srv.listen(1)
        self._set_estado("Esperando Pico en puerto {}…".format(PUERTO), GR)
        while True:
            try:
                cli, addr = srv.accept()
                if self.cliente:
                    try: self.cliente.close()
                    except: pass
                self.cliente = cli
                cli.settimeout(1.0)
                self.root.after(0, lambda a=addr: [
                    self.lbl_estado.config(
                        text="✔  Pico conectado — {}".format(a[0]), fg=VD),
                    self._set_interactivo(True)])
                self._leer_cliente(cli)
                self.root.after(0, lambda: [
                    self.lbl_estado.config(
                        text="Pico desconectado — esperando…", fg=RJ),
                    self._set_interactivo(False)])
            except Exception as e:
                print("TCP:", e)

    def _leer_cliente(self, cli):
        buf = b''
        while True:
            try:
                data = cli.recv(1024)
                if not data: break
                buf += data
                while b'\n' in buf:
                    line, buf = buf.split(b'\n', 1)
                    msg = line.decode('utf-8','ignore').strip()
                    if msg:
                        print("[PICO]", msg)
                        self.root.after(0, lambda m=msg: self._procesar(m))
            except OSError:
                pass
            except Exception as e:
                print("Error cliente:", e); break
        try: cli.close()
        except: pass
        self.cliente = None

    def _tx(self, msg):
        if self.cliente:
            try:
                self.cliente.sendall((msg+'\n').encode())
                print("[PC]  ", msg)
            except Exception as e:
                print("TX err:", e)

    # ── Protocolo ─────────────────────────────────────────────

    def _procesar(self, msg):
        if   msg == "LISTO":            pass
        elif msg == "MODO:SIMPLE":      self._on_simple()
        elif msg == "MODO:ESCUCHA":     self._on_escucha()
        elif msg.startswith("MORSE:"):  self._on_morse(msg[6:].strip())
        elif msg.startswith("RESP:"):   self._on_resp(msg[5:].strip())

    def _on_simple(self):
        self.simple = True
        self.lbl_modo.config(text="Modo: Transmisión Simple")
        self.lbl_turno.config(text="Esperando frase del Pico…", fg=GR)

    def _on_escucha(self):
        self.simple = False
        self.lbl_modo.config(text="Modo: Escucha y Transmisión")
        self._nueva_ronda()

    def _on_morse(self, frase):
        self.frase = frase
        self._reset_ronda()
        self.lbl_frase.config(text="Frase: " + frase)
        self.lbl_turno.config(text="Turno ➜  Jugador A  (teclado)", fg=VD)
        self._anim(frase, AM)
        self.t_a = time.time()

    def _on_resp(self, resp_b):
        nc = len(self.frase.replace(' ',''))
        bv = _bonus((time.time()-self.t_b)*1000, nc) if self.simple else 1
        self.pts_br = _puntos(self.frase, resp_b) + bv
        self.pts_b += self.pts_br
        self.b_ok   = True
        self._tx("PUNTAJE:" + str(self.pts_br))
        self._upd_pts()
        if self.a_ok and self.b_ok:
            self._resultado(resp_b)

    # ── Ronda ─────────────────────────────────────────────────

    def _nueva_ronda(self):
        self.frase = random.choice(FRASES)
        self._reset_ronda()
        self.lbl_frase.config(text="Frase: " + self.frase)
        self.lbl_turno.config(text="Turno ➜  Jugador A  (teclado)", fg=VD)
        self.lbl_fb.config(text="—"); self.lbl_mb.config(text="")
        self._tx("FRASE:" + self.frase)
        self._anim(self.frase, AM)
        self.t_a = time.time()

    def _reset_ronda(self):
        self.resp_a = self.buf_sym = self.buf_let = ""
        self.a_ok = self.b_ok = False
        self.pts_ar = self.pts_br = 0
        self.turno_a = True
        self._apagar()
        self.lbl_sym.config(text="Símbolos: ")
        self.lbl_let.config(text="Letras:   ")

    def _reiniciar(self):
        self.pts_a = self.pts_b = 0; self.ronda = 1
        self._upd_pts(); self._nueva_ronda()

    # ── Turno A ──────────────────────────────────────────────

    def _press(self, _):
        if not self.pulsado and self.turno_a:
            self.pulsado, self.t_press = True, time.time()

    def _release(self, _):
        if self.pulsado and self.turno_a:
            self.pulsado = False
            s = '-' if (time.time()-self.t_press)*1000 >= 2*UNIDAD_MS else '.'
            self.buf_sym += s
            self.lbl_sym.config(text="Símbolos: " + self.buf_sym)
            (raya if s=='-' else punto)()

    def _confirmar(self):
        if not self.buf_sym or not self.turno_a: return
        letra = MORSE_INV.get(self.buf_sym, '?')
        self.buf_let += letra
        self.buf_sym  = ""
        self.lbl_sym.config(text="Símbolos: ")
        self.lbl_let.config(text="Letras:   " + self.buf_let)
        if letra != '?' and letra in self.leds: self._led(letra, VD, 400); ok_snd()
        else: err_snd()

    def _enviar_a(self):
        if not self.turno_a: return
        nc = len(self.frase.replace(' ',''))
        self.pts_ar = _puntos(self.frase, self.buf_let) + \
                      _bonus((time.time()-self.t_a)*1000, nc)
        self.pts_a += self.pts_ar
        self.resp_a  = self.buf_let.upper()
        self.a_ok = True; self.turno_a = False
        self.buf_sym = self.buf_let = ""
        self.lbl_sym.config(text="Símbolos: ")
        self.lbl_let.config(text="Letras:   ")
        self.lbl_turno.config(text="Turno ➜  Jugador B  (maqueta)", fg=AM)
        self.lbl_fb.config(text=self.frase)
        self.lbl_mb.config(text="  ".join(
            MORSE.get(c,'/') if c!=' ' else '/' for c in self.frase.upper()))
        self._anim(self.frase, AZ)
        self.t_b = time.time()
        self._tx("INICIO"); self._upd_pts(); enviada()

    # ── Resultado ─────────────────────────────────────────────

    def _resultado(self, resp_b):
        nc = len(self.frase.replace(' ',''))
        ba, bb = _puntos(self.frase, self.resp_a), _puntos(self.frase, resp_b)
        if   self.pts_ar > self.pts_br: gan="Jugador A"; victoria()
        elif self.pts_br > self.pts_ar: gan="Jugador B"; victoria()
        else:                           gan="EMPATE";    empate()
        lid = "A" if self.pts_a>self.pts_b else "B" if self.pts_b>self.pts_a else "—"

        p = tk.Toplevel(self.root)
        p.title("Ronda {}".format(self.ronda))
        p.configure(bg=BG); p.resizable(False,False)
        txt = (
            "══════════  Ronda {}  ══════════\n\n"
            "  Frase:       {}\n"
            "  Resp A:      {}  →  {}/{} aciertos\n"
            "  Resp B:      {}  →  {}/{} aciertos\n\n"
            "  Puntaje A:  {}     Puntaje B:  {}\n"
            "  Ganador:    {}\n\n"
            "  Acumulado  A: {}   B: {}   Lidera: {}"
        ).format(self.ronda, self.frase,
                 self.resp_a or "(vacío)", ba, nc,
                 resp_b or "(vacío)",      bb, nc,
                 self.pts_ar, self.pts_br, gan,
                 self.pts_a,  self.pts_b,  lid)
        tk.Label(p, text=txt, font=("Courier New",11), fg=AM, bg=BG,
                 justify=tk.LEFT, padx=20, pady=12).pack()
        tk.Button(p, text="▶  Nueva ronda",
                  command=lambda:[p.destroy(), self._nueva_ronda()],
                  bg="#001a00", fg=VD, font=("Courier New",10),
                  relief="flat", padx=10).pack(pady=8)
        self.ronda += 1

    # ── Panel LED ─────────────────────────────────────────────

    def _led(self, c, color, ms):
        if c in self.leds:
            self.leds[c].config(fg=color, bg=color)
            self.root.after(ms, lambda: self.leds[c].config(fg=GR, bg=GR))

    def _apagar(self):
        for l in self.leds.values(): l.config(fg=GR, bg=GR)

    def _anim(self, frase, color, i=0):
        chars = [c for c in frase.upper() if c != ' ']
        if i < len(chars):
            self._led(chars[i], color, 380)
            self.root.after(430, lambda: self._anim(frase, color, i+1))

    def _upd_pts(self):
        self.lbl_pa.config(text="A: {}".format(self.pts_a))
        self.lbl_pb.config(text="B: {}".format(self.pts_b))

    def _set_estado(self, txt, color):
        self.root.after(0, lambda: self.lbl_estado.config(text=txt, fg=color))

    # ── Build UI ──────────────────────────────────────────────

    def _build_ui(self):
        F  = ("Courier New", 10)
        FB = ("Courier New", 11, "bold")
        FT = ("Courier New", 17, "bold")
        FM = ("Courier New", 13, "bold")

        # Título
        tk.Label(self.root, text="STRANGERTEC  MORSE  TRANSLATOR",
                 font=FT, fg=RJ, bg=BG).pack(pady=(10,4))

        # Estado de conexión — barra prominente siempre visible
        self.lbl_estado = tk.Label(
            self.root, text="Iniciando…",
            font=FB, fg=GR, bg="#111",
            relief="flat", padx=8, pady=6)
        self.lbl_estado.pack(fill=tk.X, padx=12, pady=(0,6))

        # Panel LED virtual
        fp = tk.Frame(self.root, bg=BG); fp.pack(padx=12, pady=2)
        for fila in FILAS:
            ff = tk.Frame(fp, bg=BG); ff.pack()
            for c in fila:
                l = tk.Label(ff, text=c, width=3, font=FB, fg=GR, bg=GR)
                l.pack(side=tk.LEFT, padx=2, pady=2)
                self.leds[c] = l

        # Info de ronda
        fi = tk.Frame(self.root, bg=BG); fi.pack(pady=(4,0))
        self.lbl_frase = tk.Label(fi, text="Frase: —",  font=F,  fg=AM, bg=BG)
        self.lbl_modo  = tk.Label(fi, text="Modo: —",   font=F,  fg=BL, bg=BG)
        self.lbl_turno = tk.Label(fi, text="Turno: —",  font=FB, fg=GR, bg=BG)
        for w in (self.lbl_frase, self.lbl_modo, self.lbl_turno): w.pack()

        # Panel Jugador B
        fb = tk.Frame(self.root, bg="#0a0a18", relief="sunken", bd=1)
        fb.pack(padx=12, pady=6, fill=tk.X)
        tk.Label(fb, text="JUGADOR B — frase a transmitir con el botón Morse:",
                 font=F, fg=AZ, bg="#0a0a18").pack(anchor="w", padx=6, pady=(4,0))
        self.lbl_fb = tk.Label(fb, text="—",
                               font=("Courier New",13,"bold"), fg=AM, bg="#0a0a18")
        self.lbl_fb.pack(anchor="w", padx=10)
        self.lbl_mb = tk.Label(fb, text="", font=F, fg="#666",
                               bg="#0a0a18", wraplength=500, justify=tk.LEFT)
        self.lbl_mb.pack(anchor="w", padx=10, pady=(0,4))

        # Entrada Morse Jugador A
        fe = tk.Frame(self.root, bg="#0d0d0d", relief="sunken", bd=1)
        fe.pack(padx=12, pady=2, fill=tk.X)
        tk.Label(fe,
                 text="JUGADOR A  —  [ESPACIO] Morse  |  [ENTER] letra  |  [F1] enviar",
                 font=F, fg="#555", bg="#0d0d0d").pack(pady=(4,0))
        self.lbl_sym = tk.Label(fe, text="Símbolos: ", font=FM, fg=AM, bg="#0d0d0d")
        self.lbl_let = tk.Label(fe, text="Letras:   ", font=FM, fg=VD, bg="#0d0d0d")
        self.lbl_sym.pack(); self.lbl_let.pack()
        fr = tk.Frame(fe, bg="#0d0d0d"); fr.pack(pady=4)
        self.btn_conf = tk.Button(fr, text="Confirmar [ENTER]",
            command=self._confirmar, bg="#1a0000", fg=AM, font=F, relief="flat")
        self.btn_env  = tk.Button(fr, text="Enviar [F1]",
            command=self._enviar_a,  bg="#001a00", fg=VD, font=F, relief="flat")
        self.btn_conf.pack(side=tk.LEFT, padx=6)
        self.btn_env.pack( side=tk.LEFT, padx=6)

        # Puntajes
        fp2 = tk.Frame(self.root, bg=BG); fp2.pack(pady=4)
        tk.Label(fp2, text="Puntaje  ", font=F, fg=GR, bg=BG).pack(side=tk.LEFT)
        self.lbl_pa = tk.Label(fp2, text="A: 0", font=FB, fg=VD, bg=BG)
        self.lbl_pb = tk.Label(fp2, text="B: 0", font=FB, fg=AM, bg=BG)
        self.lbl_pa.pack(side=tk.LEFT, padx=12)
        self.lbl_pb.pack(side=tk.LEFT, padx=12)

        # Controles
        fc = tk.Frame(self.root, bg=BG); fc.pack(pady=8)
        self.btn_nueva = tk.Button(fc, text="▶ Nueva ronda",
            command=self._nueva_ronda, bg="#002200", fg=VD, font=F, relief="flat")
        self.btn_rein  = tk.Button(fc, text="↺ Reiniciar",
            command=self._reiniciar,   bg="#220000", fg=RJ, font=F, relief="flat")
        self.btn_nueva.pack(side=tk.LEFT, padx=8)
        self.btn_rein.pack( side=tk.LEFT, padx=8)

        self._controles = [self.btn_conf, self.btn_env, self.btn_nueva, self.btn_rein]


if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
