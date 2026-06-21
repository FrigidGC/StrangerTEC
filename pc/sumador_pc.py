# sumador_pc.py — StrangerTEC Proyecto II
#
# El PC recibe un caracter (cualquiera de los que se pueden
# transmitir en Morse: A-Z, 0-9, + y -), busca sus 4 bits menos
# significativos en una tabla propia, y los manda al Pico por
# WiFi. El Pico solo aplica esos 4 bits al circuito.
#
# Flujo:
#   1. Usuario escribe un caracter (letra, numero, + o -).
#   2. PC busca el caracter en TABLA_MORSE y obtiene sus 4 LSB
#      (ya estan calculados de antemano, no se calculan al vuelo).
#   3. PC calcula (entrada + 5) mod 16 para mostrar en pantalla.
#   4. PC manda "BITS:xxxx\n" al Pico por TCP.
#   5. Pico aplica esos 4 bits a GP0/GP13/GP6/GP4.
#   6. Circuito hace +5 en hardware -> LEDs.
#
# Uso: python sumador_pc.py
# ============================================================

import socket
import tkinter as tk
from tkinter import messagebox

PICO_IP   = "192.168.1.101"   # IP del Pico en la red WiFi
PICO_PORT = 9002               # puerto del servidor en el Pico

# ── Tabla de todos los caracteres que se pueden transmitir ────
# en Morse en este juego, con sus 4 bits menos significativos
# ya escritos directamente (no se calculan en tiempo de ejecucion).
#
# Cada elemento es un dict: {char, ascii, bits}
# 'bits' = los 4 LSB del ASCII de ese caracter, en binario.
TABLA_MORSE = [
    {'char': 'A', 'ascii': 65, 'bits': '0001'},
    {'char': 'B', 'ascii': 66, 'bits': '0010'},
    {'char': 'C', 'ascii': 67, 'bits': '0011'},
    {'char': 'D', 'ascii': 68, 'bits': '0100'},
    {'char': 'E', 'ascii': 69, 'bits': '0101'},
    {'char': 'F', 'ascii': 70, 'bits': '0110'},
    {'char': 'G', 'ascii': 71, 'bits': '0111'},
    {'char': 'H', 'ascii': 72, 'bits': '1000'},
    {'char': 'I', 'ascii': 73, 'bits': '1001'},
    {'char': 'J', 'ascii': 74, 'bits': '1010'},
    {'char': 'K', 'ascii': 75, 'bits': '1011'},
    {'char': 'L', 'ascii': 76, 'bits': '1100'},
    {'char': 'M', 'ascii': 77, 'bits': '1101'},
    {'char': 'N', 'ascii': 78, 'bits': '1110'},
    {'char': 'O', 'ascii': 79, 'bits': '1111'},
    {'char': 'P', 'ascii': 80, 'bits': '0000'},
    {'char': 'Q', 'ascii': 81, 'bits': '0001'},
    {'char': 'R', 'ascii': 82, 'bits': '0010'},
    {'char': 'S', 'ascii': 83, 'bits': '0011'},
    {'char': 'T', 'ascii': 84, 'bits': '0100'},
    {'char': 'U', 'ascii': 85, 'bits': '0101'},
    {'char': 'V', 'ascii': 86, 'bits': '0110'},
    {'char': 'W', 'ascii': 87, 'bits': '0111'},
    {'char': 'X', 'ascii': 88, 'bits': '1000'},
    {'char': 'Y', 'ascii': 89, 'bits': '1001'},
    {'char': 'Z', 'ascii': 90, 'bits': '1010'},
    {'char': '0', 'ascii': 48, 'bits': '0000'},
    {'char': '1', 'ascii': 49, 'bits': '0001'},
    {'char': '2', 'ascii': 50, 'bits': '0010'},
    {'char': '3', 'ascii': 51, 'bits': '0011'},
    {'char': '4', 'ascii': 52, 'bits': '0100'},
    {'char': '5', 'ascii': 53, 'bits': '0101'},
    {'char': '6', 'ascii': 54, 'bits': '0110'},
    {'char': '7', 'ascii': 55, 'bits': '0111'},
    {'char': '8', 'ascii': 56, 'bits': '1000'},
    {'char': '9', 'ascii': 57, 'bits': '1001'},
    {'char': '+', 'ascii': 43, 'bits': '1011'},
    {'char': '-', 'ascii': 45, 'bits': '1101'},
]

# Diccionario para buscar por caracter en O(1)
ASCII_TABLE = {fila['char']: fila for fila in TABLA_MORSE}

def salida_de(bits):
    """Calcula (entrada + 5) mod 16 a partir del string de bits."""
    return (int(bits, 2) + 5) % 16


# ── Conexion al Pico ─────────────────────────────────────────

def mandar_al_pico(bits_str):
    """Manda "BITS:xxxx\n" al Pico por TCP. Devuelve True/False."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        s.connect((PICO_IP, PICO_PORT))
        s.send(("BITS:" + bits_str + "\n").encode())
        s.close()
        return True
    except Exception as e:
        print("Error al conectar con el Pico:", e)
        return False


# ── Interfaz grafica ─────────────────────────────────────────

NEGRO   = "Black"; BLANCO  = "White"; GRIS  = "#555"
VERDE   = "#00cc44"; ROJO  = "#ff4444"; AZUL = "#4fc3f7"
NARANJA = "#ff9800"; AMAR  = "Yellow"

CARACTERES_VALIDOS = set(ASCII_TABLE.keys())   # A-Z, 0-9, +, -


class VentanaSumador(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("Sumador +5 — Proyecto II")
        self.configure(bg=NEGRO)
        self.resizable(False, False)
        self._build()

    def _lbl(self, p, t, f=("Courier",10), fg=BLANCO, bg=None, **kw):
        return tk.Label(p, text=t, font=f, fg=fg, bg=bg or p["bg"], **kw)

    def _sep(self):
        tk.Frame(self, bg="#333", height=1).pack(fill=tk.X, padx=12, pady=4)

    def _build(self):
        F  = ("Courier", 10)
        FB = ("Courier", 11, "bold")
        FT = ("Courier", 14, "bold")
        FL = ("Courier", 20, "bold")

        self._lbl(self, "CIRCUITO INCREMENTADOR EN 5", FT, NARANJA).pack(pady=(12,2))
        self._lbl(self, "Ingresa un caracter Morse (A-Z, 0-9, + o -)",
                  ("Courier",9), GRIS).pack(pady=(0,6))

        self._sep()

        fe = tk.Frame(self, bg=NEGRO); fe.pack(pady=6)
        self._lbl(fe, "Caracter:", FB, AZUL).pack(side=tk.LEFT, padx=8)
        self.entrada = tk.Entry(fe, font=("Courier",18,"bold"), width=3,
                                bg="#111", fg=AMAR, insertbackground=AMAR,
                                justify=tk.CENTER)
        self.entrada.pack(side=tk.LEFT, padx=4)
        self.entrada.bind("<Return>", lambda e: self._procesar())
        self.entrada.bind("<KeyRelease>", self._validar)
        self.entrada.focus()

        self.btn = tk.Button(fe, text="Enviar al Pico →",
                             font=FB, bg=NARANJA, fg=NEGRO,
                             activebackground="#cc7a00",
                             relief="flat", padx=10,
                             command=self._procesar)
        self.btn.pack(side=tk.LEFT, padx=8)

        self._sep()

        centro = tk.Frame(self, bg=NEGRO); centro.pack(padx=16, pady=4)

        pi = tk.Frame(centro, bg="#0d0d1a", relief="raised", bd=1)
        pi.pack(side=tk.LEFT, padx=6, pady=4)
        self._lbl(pi, "CALCULO (PC)", FB, AZUL).pack(pady=(8,6))

        rows = [
            ("Caracter:",        "lbl_dig",  AMAR),
            ("ASCII decimal:",   "lbl_asc",  BLANCO),
            ("4 LSB (entrada):", "lbl_lsb",  AZUL),
            ("Salida +5 (bin):", "lbl_sal",  VERDE),
            ("Salida +5 (dec):", "lbl_dec",  VERDE),
        ]
        for texto, nombre, color in rows:
            f = tk.Frame(pi, bg="#0d0d1a"); f.pack(fill=tk.X, padx=10, pady=1)
            self._lbl(f, texto, F, GRIS).pack(side=tk.LEFT)
            lbl = self._lbl(f, "—", F, color); lbl.pack(side=tk.RIGHT)
            setattr(self, nombre, lbl)

        tk.Frame(pi, bg="#0d0d1a", height=4).pack()
        self._lbl(pi, "4 LSB en detalle:", F, GRIS).pack(pady=(4,2))

        fila_bits = tk.Frame(pi, bg="#0d0d1a"); fila_bits.pack(pady=(0,8))
        self.leds_in = []
        for i in range(4):
            col = tk.Frame(fila_bits, bg="#0d0d1a"); col.pack(side=tk.LEFT, padx=6)
            led = self._lbl(col, "●", ("Courier",20), GRIS); led.pack()
            self._lbl(col, "A{}".format(3-i), ("Courier",8), GRIS).pack()
            self.leds_in.append(led)

        pm = tk.Frame(centro, bg=NEGRO); pm.pack(side=tk.LEFT, padx=10)
        self._lbl(pm, "→", ("Courier",22), NARANJA, NEGRO).pack(pady=(24,2))
        self._lbl(pm, "WiFi\nal Pico", ("Courier",9), NARANJA, NEGRO,
                  justify=tk.CENTER).pack()
        self._lbl(pm, "→", ("Courier",22), NARANJA, NEGRO).pack(pady=2)

        ps = tk.Frame(centro, bg="#0d1a0d", relief="raised", bd=1)
        ps.pack(side=tk.LEFT, padx=6, pady=4)
        self._lbl(ps, "PICO / CIRCUITO", FB, VERDE).pack(pady=(8,4))
        self._lbl(ps, "El Pico aplica estos\nbits a GP0/GP13/GP6/GP4",
                  ("Courier",8), GRIS, justify=tk.CENTER).pack()
        self._lbl(ps, "El circuito hace +5\nen hardware -> LEDs",
                  ("Courier",8), GRIS, justify=tk.CENTER).pack(pady=(2,6))

        self.lbl_estado = self._lbl(ps, "En espera", FB, GRIS)
        self.lbl_estado.pack(pady=4)

        self.lbl_bits_env = self._lbl(ps, "????", FL, VERDE)
        self.lbl_bits_env.pack()
        self._lbl(ps, "bits enviados al Pico", ("Courier",8), GRIS).pack(pady=(0,8))

        self._sep()

        self._lbl(self, "Tabla de referencia — todos los caracteres Morse",
                  FB, NARANJA).pack(anchor="w", padx=14)
        mt = tk.Frame(self, bg="#080808", relief="sunken", bd=1)
        mt.pack(padx=14, pady=4)
        self._lbl(mt, "  Car | ASCII | 4 LSB  | +5 bin | +5 dec",
                  ("Courier",9), GRIS, "#080808", anchor="w").grid(
                  row=0, column=0, columnspan=3, sticky="w", padx=4)
        tk.Frame(mt, bg="#333", height=1).grid(
                  row=1, column=0, columnspan=3, sticky="ew")

        self.filas_tabla = {}
        # 38 caracteres repartidos en 3 columnas de ~13 filas
        por_columna = 13
        for idx, fila in enumerate(TABLA_MORSE):
            col = idx // por_columna
            row = (idx % por_columna) + 2
            sal = salida_de(fila['bits'])
            texto = " {}  | {:3d}  | {}   | {:04b}   | {:2d}".format(
                fila['char'], fila['ascii'], fila['bits'], sal, sal)
            lbl = self._lbl(mt, texto, ("Courier",9), GRIS, "#080808", anchor="w")
            lbl.grid(row=row, column=col, sticky="w", padx=10)
            self.filas_tabla[fila['char']] = lbl

        tk.Frame(self, bg=NEGRO, height=8).pack()

    # ── Logica ───────────────────────────────────────────────

    def _validar(self, event=None):
        """Permite solo un caracter, y solo si es valido (A-Z, 0-9, + o -)."""
        v = self.entrada.get().upper()
        if len(v) > 1:
            v = v[-1]
        if v and v not in CARACTERES_VALIDOS:
            v = ""
        self.entrada.delete(0, tk.END)
        self.entrada.insert(0, v)

    def _procesar(self):
        c = self.entrada.get().strip().upper()
        if c not in ASCII_TABLE:
            messagebox.showwarning(
                "Entrada invalida",
                "Ingresa un caracter Morse valido: A-Z, 0-9, + o -")
            return

        info  = ASCII_TABLE[c]
        bits  = info['bits']
        salida = salida_de(bits)

        self.lbl_dig.config(text=info['char'])
        self.lbl_asc.config(text=str(info['ascii']))
        self.lbl_lsb.config(text="{} ({})".format(bits, int(bits, 2)))
        self.lbl_sal.config(text="{:04b}".format(salida))
        self.lbl_dec.config(text=str(salida))

        for i, led in enumerate(self.leds_in):
            led.config(fg=AZUL if bits[i] == '1' else GRIS)

        for k, fila in self.filas_tabla.items():
            fila.config(fg=NARANJA if k == c else GRIS,
                        bg="#1a0f00" if k == c else "#080808")

        self.lbl_bits_env.config(text=bits)
        ok = mandar_al_pico(bits)
        if ok:
            self.lbl_estado.config(text="Enviado OK", fg=VERDE)
        else:
            self.lbl_estado.config(text="Sin conexion al Pico", fg=ROJO)

        print("'{}' ASCII={} -> 4LSB={} -> enviado={} -> salida esperada={} ({:04b})".format(
            c, info['ascii'], bits, "OK" if ok else "FALLO", salida, salida))


if __name__ == "__main__":
    VentanaSumador().mainloop()
