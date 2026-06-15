# inc5_panel.py
# Proyecto II - StrangerTEC Morse Translator
#
# Esta es la parte del PC para el circuito incrementador en 5.
#
# Hace dos cosas:
#   1. Levanta un servidor TCP que escucha al Pico por WiFi.
#   2. Abre una ventanita que muestra el numero que se mando,
#      sus 4 bits de entrada y el resultado de sumarle 5
#      (calculado aqui en software, en binario y decimal).
#      Ese resultado debe coincidir con los LEDs del circuito.
#
# El PC tambien detecta solo, segun los mensajes que llegan,
# si el switch del Pico esta en ON o en OFF, y lo muestra
# en la ventana ("Modo Sumar 5: activo / inactivo").
#
# Mensajes que se esperan del Pico (TCP, una linea por \n):
#   "INC5:SW:1:CHAR:3:ASCII:51:ENTRADA:0011"
#   "INC5:SW:0"
#
# Para usar esto junto con el juego principal, ver main_p2.py
# ============================================================

import socket
import threading
import tkinter as tk

PUERTO = 9001

# Colores reutilizados del tema del juego
NEGRO   = "Black"
AMARILLO = "Yellow"
ROJO    = "Red"
VERDE   = "Green"
GRIS    = "#444"
BLANCO  = "White"
AZUL    = "#4fc3f7"
NARANJA = "#ff9800"


def mas_cinco(valor):
    """El calculo que hace el PC: (valor + 5) mod 16."""
    return (valor + 5) % 16


def a_binario(valor):
    return "{:04b}".format(valor & 0xF)


class ServidorInc5:
    """
    Escucha conexiones del Pico en el puerto 9001 y va
    avisando a la ventana cada vez que llega un dato nuevo
    o cambia el estado del switch.
    """

    def __init__(self, on_dato, on_switch, on_ip):
        self.on_dato = on_dato
        self.on_switch = on_switch
        self.on_ip = on_ip
        self.sock = None
        self.activo = False
        self.switch_actual = None  # None = todavia no sabemos

    def iniciar(self):
        self.activo = True
        threading.Thread(target=self._escuchar, daemon=True).start()
        print("Servidor Inc5 escuchando en el puerto", PUERTO)

    def detener(self):
        self.activo = False
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass

    def _escuchar(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.sock.bind(('', PUERTO))
            self.sock.listen(1)
        except Exception as e:
            print("No se pudo abrir el puerto", PUERTO, ":", e)
            return

        while self.activo:
            try:
                self.sock.settimeout(2.0)
                conexion, direccion = self.sock.accept()
                print("Pico conectado desde", direccion)
                if self.on_ip:
                    self.on_ip(direccion[0])
                self._atender(conexion)
            except socket.timeout:
                continue
            except Exception as e:
                if self.activo:
                    print("Error de conexion:", e)

    def _atender(self, conexion):
        conexion.settimeout(1.0)
        buffer = b''
        while self.activo:
            try:
                datos = conexion.recv(256)
                if not datos:
                    break
                buffer += datos
                while b'\n' in buffer:
                    linea, buffer = buffer.split(b'\n', 1)
                    self._procesar(linea.decode('utf-8', errors='replace').strip())
            except socket.timeout:
                continue
            except Exception as e:
                print("Error leyendo del Pico:", e)
                break
        conexion.close()
        print("Pico desconectado")
        self._avisar_switch(False)  # si se desconecta, asumimos inactivo

    def _procesar(self, linea):
        if not linea.startswith("INC5:"):
            return
        print("Pico ->", linea)

        partes = linea.split(':')

        # "INC5:SW:0" -> switch apagado
        if len(partes) >= 3 and partes[1] == "SW" and partes[2] == "0":
            self._avisar_switch(False)
            return

        # "INC5:SW:1:CHAR:3:ASCII:51:ENTRADA:0011"
        if len(partes) >= 9 and partes[1] == "SW" and partes[2] == "1" \
                and partes[3] == "CHAR" and partes[5] == "ASCII" and partes[7] == "ENTRADA":
            try:
                caracter = partes[4]
                ascii_val = int(partes[6])
                bits_entrada = partes[8]
                entrada = int(bits_entrada, 2)
                salida = mas_cinco(entrada)

                self._avisar_switch(True)

                resultado = {
                    'char': caracter,
                    'ascii': ascii_val,
                    'entrada': entrada,
                    'bits_in': bits_entrada,
                    'salida': salida,
                    'bits_out': a_binario(salida),
                }
                if self.on_dato:
                    self.on_dato(resultado)
            except Exception as e:
                print("No se pudo leer el mensaje:", e)

    def _avisar_switch(self, encendido):
        if self.switch_actual != encendido:
            self.switch_actual = encendido
            if self.on_switch:
                self.on_switch(encendido)


class VentanaInc5(tk.Toplevel):
    """Ventana que muestra el estado del circuito incrementador en 5."""

    MAX_HISTORIAL = 10

    def __init__(self, padre):
        super().__init__(padre)
        self.title("StrangerTEC - Incrementador en 5")
        self.configure(bg=NEGRO)
        self.resizable(False, False)

        self.historial = []
        self._armar_ui()
        self.set_switch(False)
        self.set_ip("Esperando al Pico...")

    def _armar_ui(self):
        f_titulo = ("Courier", 14, "bold")
        f_seccion = ("Courier", 11, "bold")
        f_normal = ("Courier", 10)
        f_bits = ("Courier", 16, "bold")

        tk.Label(self, text="INCREMENTADOR EN 5", font=f_titulo,
                 fg=NARANJA, bg=NEGRO).pack(pady=(12, 2))
        tk.Label(self, text="Proyecto II", font=f_normal,
                 fg=GRIS, bg=NEGRO).pack()

        # Linea de conexion
        fila_wifi = tk.Frame(self, bg="#0a0a0a", relief="sunken", bd=1)
        fila_wifi.pack(padx=16, pady=6, fill=tk.X)
        tk.Label(fila_wifi, text="WiFi:", font=f_normal,
                 fg=GRIS, bg="#0a0a0a").pack(side=tk.LEFT, padx=8)
        self.lbl_ip = tk.Label(fila_wifi, text="", font=f_normal,
                               fg=VERDE, bg="#0a0a0a")
        self.lbl_ip.pack(side=tk.LEFT, padx=4)

        # Linea de modo
        fila_modo = tk.Frame(self, bg="#0a0a0a", relief="sunken", bd=1)
        fila_modo.pack(padx=16, pady=2, fill=tk.X)
        tk.Label(fila_modo, text="Modo Sumar 5:", font=f_normal,
                 fg=GRIS, bg="#0a0a0a").pack(side=tk.LEFT, padx=8)
        self.lbl_modo = tk.Label(fila_modo, text="", font=f_seccion,
                                 fg=ROJO, bg="#0a0a0a")
        self.lbl_modo.pack(side=tk.LEFT, padx=4)

        tk.Frame(self, bg="#333", height=1).pack(fill=tk.X, padx=12, pady=4)

        # Panel principal: entrada -> circuito -> salida
        fila_principal = tk.Frame(self, bg=NEGRO)
        fila_principal.pack(padx=16, pady=4)

        # Entrada
        panel_in = tk.Frame(fila_principal, bg="#0d0d1a", relief="raised", bd=1)
        panel_in.pack(side=tk.LEFT, padx=6, pady=4)
        tk.Label(panel_in, text="ENTRADA", font=f_seccion,
                 fg=AZUL, bg="#0d0d1a").pack(pady=(8, 4))

        tk.Label(panel_in, text="Digito:", font=f_normal,
                 fg=GRIS, bg="#0d0d1a").pack()
        self.lbl_char = tk.Label(panel_in, text="-", font=("Courier", 28, "bold"),
                                 fg=AMARILLO, bg="#0d0d1a")
        self.lbl_char.pack()

        tk.Label(panel_in, text="ASCII:", font=f_normal,
                 fg=GRIS, bg="#0d0d1a").pack()
        self.lbl_ascii = tk.Label(panel_in, text="-", font=f_seccion,
                                  fg=BLANCO, bg="#0d0d1a")
        self.lbl_ascii.pack()

        tk.Label(panel_in, text="4 bits al circuito:", font=f_normal,
                 fg=GRIS, bg="#0d0d1a").pack(pady=(8, 2))
        self.lbl_bits_in = tk.Label(panel_in, text="????", font=f_bits,
                                    fg=AZUL, bg="#0d0d1a")
        self.lbl_bits_in.pack()
        tk.Label(panel_in, text="A3 A2 A1 A0", font=("Courier", 8),
                 fg=GRIS, bg="#0d0d1a").pack(pady=(0, 8))

        # Flecha y circuito
        panel_circuito = tk.Frame(fila_principal, bg=NEGRO)
        panel_circuito.pack(side=tk.LEFT, padx=8, pady=4)
        tk.Label(panel_circuito, text="->", font=("Courier", 18),
                 fg=NARANJA, bg=NEGRO).pack(pady=(20, 4))
        tk.Label(panel_circuito,
                 text="+5\n(mod 16)\nhardware",
                 font=("Courier", 11), fg=NARANJA, bg=NEGRO,
                 justify=tk.CENTER).pack()
        tk.Label(panel_circuito, text="->", font=("Courier", 18),
                 fg=NARANJA, bg=NEGRO).pack(pady=4)

        # Salida
        panel_out = tk.Frame(fila_principal, bg="#0d1a0d", relief="raised", bd=1)
        panel_out.pack(side=tk.LEFT, padx=6, pady=4)
        tk.Label(panel_out, text="RESULTADO (PC)", font=f_seccion,
                 fg=VERDE, bg="#0d1a0d").pack(pady=(8, 4))
        tk.Label(panel_out, text="debe coincidir con\nlos LEDs del circuito",
                 font=("Courier", 8), fg=GRIS, bg="#0d1a0d",
                 justify=tk.CENTER).pack(pady=(0, 6))

        self.lbl_bits_out = tk.Label(panel_out, text="????", font=f_bits,
                                     fg=VERDE, bg="#0d1a0d")
        self.lbl_bits_out.pack()
        tk.Label(panel_out, text="S3 S2 S1 S0", font=("Courier", 8),
                 fg=GRIS, bg="#0d1a0d").pack()

        # 4 LEDs virtuales
        fila_leds = tk.Frame(panel_out, bg="#0d1a0d")
        fila_leds.pack(pady=8)
        self.leds = []
        for i in range(4):
            col = tk.Frame(fila_leds, bg="#0d1a0d")
            col.pack(side=tk.LEFT, padx=4)
            led = tk.Label(col, text="●", font=("Courier", 18),
                           fg=GRIS, bg="#0d1a0d")
            led.pack()
            tk.Label(col, text="S{}".format(3 - i), font=("Courier", 8),
                     fg=GRIS, bg="#0d1a0d").pack()
            self.leds.append(led)

        tk.Label(panel_out, text="Decimal:", font=f_normal,
                 fg=GRIS, bg="#0d1a0d").pack(pady=(8, 0))
        self.lbl_dec = tk.Label(panel_out, text="-", font=("Courier", 22, "bold"),
                                fg=VERDE, bg="#0d1a0d")
        self.lbl_dec.pack(pady=(0, 4))

        self.lbl_cuenta = tk.Label(panel_out, text="", font=f_normal,
                                   fg=BLANCO, bg="#0d1a0d")
        self.lbl_cuenta.pack(pady=(0, 8))

        # Historial
        tk.Frame(self, bg="#333", height=1).pack(fill=tk.X, padx=12, pady=4)
        tk.Label(self, text="Ultimos digitos:", font=f_seccion,
                 fg=NARANJA, bg=NEGRO).pack(anchor="w", padx=16)

        marco_hist = tk.Frame(self, bg="#050505", relief="sunken", bd=1)
        marco_hist.pack(padx=16, pady=4, fill=tk.BOTH)

        cabecera = "  Dig | ASCII | Entrada      | Salida (+5)   | Decimal"
        tk.Label(marco_hist, text=cabecera, font=("Courier", 9),
                 fg=GRIS, bg="#050505", anchor="w").pack(fill=tk.X, padx=4)
        tk.Frame(marco_hist, bg="#222", height=1).pack(fill=tk.X)

        self.filas_hist = []
        for _ in range(self.MAX_HISTORIAL):
            fila = tk.Label(marco_hist, text="", font=("Courier", 9),
                            fg=BLANCO, bg="#050505", anchor="w")
            fila.pack(fill=tk.X, padx=4)
            self.filas_hist.append(fila)

        # Tabla de verdad
        tk.Frame(self, bg="#333", height=1).pack(fill=tk.X, padx=12, pady=4)
        marco_tabla_titulo = tk.Frame(self, bg=NEGRO)
        marco_tabla_titulo.pack(padx=16, pady=4)
        tk.Label(marco_tabla_titulo, text="Tabla de verdad (entrada + 5, mod 16):",
                 font=f_seccion, fg=NARANJA, bg=NEGRO).pack(anchor="w")

        marco_tabla = tk.Frame(marco_tabla_titulo, bg="#080808", relief="sunken", bd=1)
        marco_tabla.pack()

        tk.Label(marco_tabla, text=" A3A2A1A0 | S3S2S1S0 | Dec",
                 font=("Courier", 8), fg=GRIS, bg="#080808").grid(
                 row=0, column=0, columnspan=2, sticky="w", padx=4)

        self.filas_tabla = {}
        for i in range(16):
            col = i // 8
            fila = (i % 8) + 1
            salida = mas_cinco(i)
            texto = " {}  |  {}  | {:2d}".format(
                a_binario(i), a_binario(salida), salida)
            etiqueta = tk.Label(marco_tabla, text=texto, font=("Courier", 8),
                                fg=GRIS, bg="#080808", anchor="w")
            etiqueta.grid(row=fila, column=col, sticky="w", padx=6)
            self.filas_tabla[i] = etiqueta

        tk.Frame(self, bg=NEGRO, height=8).pack()

    # ── Lo que se llama desde afuera ──────────────────────────

    def set_switch(self, encendido):
        """Cambia el cartel de 'Modo Sumar 5' segun el switch del Pico."""
        if encendido:
            self.lbl_modo.config(text="ACTIVO", fg=VERDE)
        else:
            self.lbl_modo.config(text="INACTIVO (switch en OFF)", fg=ROJO)
            self.lbl_char.config(text="-")
            self.lbl_ascii.config(text="-")
            self.lbl_bits_in.config(text="????")
            self.lbl_bits_out.config(text="????")
            self.lbl_dec.config(text="-")
            self.lbl_cuenta.config(text="")
            for led in self.leds:
                led.config(fg=GRIS)

    def set_ip(self, texto):
        self.lbl_ip.config(text=texto)

    def mostrar_resultado(self, r):
        """r es el dict que manda ServidorInc5 con entrada/salida ya calculadas."""
        self.lbl_char.config(text=r['char'])
        self.lbl_ascii.config(text="{} ({})".format(r['ascii'], hex(r['ascii'])))
        self.lbl_bits_in.config(text=r['bits_in'])
        self.lbl_bits_out.config(text=r['bits_out'])
        self.lbl_dec.config(text=str(r['salida']))
        self.lbl_cuenta.config(text="{} + 5 = {} (mod 16)".format(
            r['entrada'], r['salida']))

        for i, led in enumerate(self.leds):
            led.config(fg=VERDE if r['bits_out'][i] == '1' else GRIS)

        for i, etiqueta in self.filas_tabla.items():
            if i == r['entrada']:
                etiqueta.config(fg=NARANJA, bg="#1a1000")
            else:
                etiqueta.config(fg=GRIS, bg="#080808")

        self.historial.insert(0, r)
        self.historial = self.historial[:self.MAX_HISTORIAL]
        self._refrescar_historial()

    def _refrescar_historial(self):
        for i, fila in enumerate(self.filas_hist):
            if i < len(self.historial):
                r = self.historial[i]
                texto = "   {}  |  {:3d}  | {} ({:2d})  | {} ({:2d})  |  {:2d}".format(
                    r['char'], r['ascii'],
                    r['bits_in'], r['entrada'],
                    r['bits_out'], r['salida'],
                    r['salida'])
                fila.config(text=texto)
            else:
                fila.config(text="")
