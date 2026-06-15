# prueba_incremento5.py
# Proyecto II - StrangerTEC Morse Translator
#
# Programa aparte para probar el circuito incrementador en 5
# sin tener que jugar una partida completa.
#
# Lo que hace este programa es nada mas escribir los 4 bits de
# entrada (A3 A2 A1 A0) en los pines GP0-GP3, que van conectados
# al circuito de compuertas logicas. Ese circuito hace la cuenta
# de +5 en hardware y prende sus propios 4 LEDs de salida.
#
# El Pico NO lee esos LEDs. La persona que esta probando los ve
# directamente en la maqueta y los compara con lo que este
# programa imprime en pantalla.
#
# Como usarlo:
#   1. Conectar el circuito (entradas a GP0-GP3, salidas a sus
#      propios LEDs, fuera del Pico).
#   2. Abrir este archivo en Thonny y darle Run.
#   3. Elegir una opcion del menu y comparar los LEDs con lo
#      que dice la consola.
#
# Pines de entrada:
#   GP0 = A3 (MSB)   GP1 = A2   GP2 = A1   GP3 = A0 (LSB)
#
# Tabla de verdad (Salida = Entrada + 5, modulo 16):
#   0000 -> 0101 (0  -> 5)     1000 -> 1101 (8  -> 13)
#   0001 -> 0110 (1  -> 6)     1001 -> 1110 (9  -> 14)
#   0010 -> 0111 (2  -> 7)     1010 -> 1111 (10 -> 15)
#   0011 -> 1000 (3  -> 8)     1011 -> 0000 (11 -> 0)
#   0100 -> 1001 (4  -> 9)     1100 -> 0001 (12 -> 1)
#   0101 -> 1010 (5  -> 10)    1101 -> 0010 (13 -> 2)
#   0110 -> 1011 (6  -> 11)    1110 -> 0011 (14 -> 3)
#   0111 -> 1100 (7  -> 12)    1111 -> 0100 (15 -> 4)
# ============================================================

import machine

PINES_ENTRADA = [0, 1, 2, 3]   # GP0..GP3 = A3 A2 A1 A0
pines = [machine.Pin(p, machine.Pin.OUT) for p in PINES_ENTRADA]


def tabla_verdad(entrada):
    """Devuelve la salida esperada para una entrada de 0 a 15."""
    return (entrada + 5) % 16


def apagar():
    """Pone las 4 entradas en 0."""
    for pin in pines:
        pin.value(0)


def aplicar(valor):
    """
    Manda el numero (0-15) a los pines A3 A2 A1 A0 y devuelve
    los 4 bits que se aplicaron, por si se quieren mostrar.
    """
    a3 = (valor >> 3) & 1
    a2 = (valor >> 2) & 1
    a1 = (valor >> 1) & 1
    a0 = valor & 1

    pines[0].value(a3)
    pines[1].value(a2)
    pines[2].value(a1)
    pines[3].value(a0)

    return a3, a2, a1, a0


def mostrar(valor):
    """Aplica el valor y muestra en consola que se debe ver en los LEDs."""
    a3, a2, a1, a0 = aplicar(valor)
    salida = tabla_verdad(valor)

    print()
    print("Entrada A3 A2 A1 A0 = {} {} {} {}  ->  {:04b} ({})".format(
        a3, a2, a1, a0, valor, valor))
    print("LEDs deberian mostrar S3 S2 S1 S0 = {:04b}  ({})".format(
        salida, salida))
    print("(revisa los LEDs del circuito y compara con lo de arriba)")


# ── Opciones del menu ─────────────────────────────────────────

def opcion_bit_a_bit():
    print("\nIngresa cada bit (0 o 1):")
    nombres = ["A3 (MSB)", "A2", "A1", "A0 (LSB)"]
    bits = []
    for nombre in nombres:
        while True:
            dato = input("  {} = ".format(nombre)).strip()
            if dato in ("0", "1"):
                bits.append(int(dato))
                break
            print("  -> escribe 0 o 1")

    valor = (bits[0] << 3) | (bits[1] << 2) | (bits[2] << 1) | bits[3]
    mostrar(valor)


def opcion_decimal():
    dato = input("\nValor decimal (0-15): ").strip()
    try:
        valor = int(dato)
    except ValueError:
        print("-> eso no es un numero")
        return
    if not (0 <= valor <= 15):
        print("-> debe estar entre 0 y 15")
        return
    mostrar(valor)


def opcion_binario():
    dato = input("\nBits A3A2A1A0 (ej. 1011): ").strip()
    if len(dato) != 4 or any(c not in "01" for c in dato):
        print("-> deben ser exactamente 4 bits, por ejemplo 1011")
        return
    mostrar(int(dato, 2))


def opcion_automatica():
    print("\nRecorriendo las 16 combinaciones, una cada 2 segundos...")
    print("Observa los LEDs del circuito en cada paso.\n")
    for valor in range(16):
        mostrar(valor)
        time_sleep(2)
    apagar()
    print("\nListo, se probaron las 16 combinaciones.")


def opcion_tabla():
    print("\n A3 A2 A1 A0 | Dec | S3 S2 S1 S0 | Dec")
    print("-" * 38)
    for i in range(16):
        salida = tabla_verdad(i)
        print(" {:04b}      | {:3d} | {:04b}        | {:3d}".format(
            i, i, salida, salida))


# pequeño wrapper para no importar "time" si no se usa la opcion automatica
def time_sleep(segundos):
    import time
    time.sleep(segundos)


def menu():
    print("=" * 50)
    print(" Prueba del circuito incrementador en 5")
    print("=" * 50)
    print("El Pico solo escribe A3 A2 A1 A0 en GP0-GP3.")
    print("Los LEDs de salida los maneja el circuito, no el Pico.")

    while True:
        print("\n1) Ingresar bit por bit")
        print("2) Ingresar valor decimal (0-15)")
        print("3) Ingresar binario (ej. 1011)")
        print("4) Probar las 16 combinaciones automaticamente")
        print("5) Ver tabla de verdad")
        print("0) Salir")

        opcion = input("\nOpcion: ").strip()

        if opcion == "1":
            opcion_bit_a_bit()
        elif opcion == "2":
            opcion_decimal()
        elif opcion == "3":
            opcion_binario()
        elif opcion == "4":
            opcion_automatica()
        elif opcion == "5":
            opcion_tabla()
        elif opcion == "0":
            apagar()
            print("\nEntradas en 0. Listo.")
            break
        else:
            print("Opcion no valida")


apagar()
menu()
