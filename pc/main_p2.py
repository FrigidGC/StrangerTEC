# main_p2.py
# Proyecto II - StrangerTEC Morse Translator
#
# Arranca el juego (pc_server.py, Proyecto I) y, junto con el,
# abre la ventana del incrementador en 5 (Proyecto II).
#
# Para correrlo:
#   python main_p2.py
#
# Esto deja:
#   - La ventana del juego normal (todo igual que en Proyecto I).
#   - Una segunda ventana a un lado, con el panel del circuito
#     incrementador en 5, alimentada por WiFi desde el Pico.
# ============================================================

import tkinter as tk

from pc_server import AppStrangerTEC
from inc5_panel import VentanaInc5, ServidorInc5, PUERTO


def main():
    raiz = tk.Tk()
    juego = AppStrangerTEC(raiz)

    panel = VentanaInc5(raiz)
    panel.geometry("+900+50")

    def cuando_llega_dato(resultado):
        raiz.after(0, lambda: panel.mostrar_resultado(resultado))

    def cuando_cambia_switch(encendido):
        raiz.after(0, lambda: panel.set_switch(encendido))

    def cuando_se_conecta(ip):
        raiz.after(0, lambda: panel.set_ip("Pico conectado: " + ip))

    servidor = ServidorInc5(cuando_llega_dato, cuando_cambia_switch, cuando_se_conecta)
    servidor.iniciar()

    print("StrangerTEC - Proyecto II")
    print("Servidor del incrementador en 5 escuchando en el puerto", PUERTO)

    try:
        raiz.mainloop()
    finally:
        servidor.detener()


if __name__ == "__main__":
    main()
