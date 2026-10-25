# celula_gui.py
# Celula cliente con interfaz grafica (la calculadora)
#
# Uso:
#   python celula_gui.py <host:puerto del nodo> [nombre]
#
# Ejemplo:
#   python celula_gui.py 127.0.0.1:5001 GUI-N1
#
# Tambien se puede usar el teclado: numeros, + - * /, Enter, Backspace y Esc.

import tkinter as tk
from tkinter import ttk
import socket
import json
import sys
import threading
import queue
import uuid

CODIGOS = {
    "+": "SUM_REQ",
    "-": "SUB_REQ",
    "x": "MUL_REQ",
    "/": "DIV_REQ",
}

NOMBRES = {
    "+": "suma",
    "-": "resta",
    "x": "multiplicacion",
    "/": "division",
}

SIMBOLOS = {
    "+": "+",
    "-": "−",
    "x": "×",
    "/": "÷",
}

# colores
FONDO = "#1c1c1e"
NUMERO = "#333336"
NUMERO_HOVER = "#4a4a4e"
OPERADOR = "#ff9f0a"
OPERADOR_HOVER = "#ffb340"
FUNCION = "#a5a5aa"
FUNCION_HOVER = "#c5c5ca"
TEXTO = "#ffffff"
GRIS = "#8e8e93"

# segundos que esperamos una respuesta antes de avisar que no llego
TIEMPO_ESPERA = 4


def enviar(sock, mensaje):
    texto = json.dumps(mensaje) + "\n"
    sock.sendall(texto.encode("utf-8"))


def bonito(numero):
    # para que 5.0 se vea como 5 y 0.1+0.2 no se vea feo
    try:
        if numero == int(numero):
            return str(int(numero))
    except (ValueError, OverflowError):
        return str(numero)
    texto = "%.10f" % numero
    return texto.rstrip("0").rstrip(".")


class CalculadoraGUI:
    def __init__(self, host, puerto, nombre):
        self.nombre = nombre
        self.pendientes = {}        # id de solicitud -> (a, operador, b)
        self.cola = queue.Queue()   # mensajes que llegan del nodo

        # estado de la calculadora
        self.actual = "0"           # numero que se esta escribiendo
        self.primero = None         # primer operando
        self.operador = None        # + - x /
        self.nuevo = True           # el siguiente digito empieza un numero nuevo
        self.siguiente_op = None    # operador que se pulso mientras se calculaba
        self.esperando = False      # ya mandamos la solicitud y falta la respuesta

        # conexion con el nodo
        self.sock = socket.create_connection((host, puerto))
        enviar(self.sock, {"tipo": "HELLO", "entidad": "GUI", "nombre": nombre})
        self.lector = self.sock.makefile("r", encoding="utf-8")
        respuesta = json.loads(self.lector.readline())
        if respuesta.get("tipo") != "BIENVENIDA":
            print("El nodo rechazo la conexion: " + str(respuesta))
            sys.exit()
        self.mi_nodo = respuesta["nodo"]

        hilo = threading.Thread(target=self.escuchar, daemon=True)
        hilo.start()

        self.crear_ventana()
        self.mostrar()
        self.agregar_registro("Conectada al nodo " + self.mi_nodo + " como " + self.nombre)
        self.ventana.after(100, self.revisar_cola)

    # ---------------- ventana ----------------
    def crear_ventana(self):
        self.ventana = tk.Tk()
        self.ventana.title("Calculadora ADS - " + self.nombre)
        self.ventana.configure(bg=FONDO)
        self.ventana.resizable(False, False)

        # estilos de los botones
        estilo = ttk.Style()
        estilo.theme_use("clam")
        colores = [
            ("Num", NUMERO, NUMERO_HOVER, TEXTO),
            ("Op", OPERADOR, OPERADOR_HOVER, TEXTO),
            ("Fun", FUNCION, FUNCION_HOVER, "#000000"),
        ]
        for clave, fondo, hover, letra in colores:
            estilo.configure(clave + ".TButton", background=fondo, foreground=letra,
                             font=("Arial", 18), borderwidth=0, relief="flat",
                             focusthickness=0, focuscolor=fondo)
            estilo.map(clave + ".TButton", background=[("active", hover)])

        # parte de arriba: nodo y estado de la conexion
        cabecera = tk.Frame(self.ventana, bg=FONDO)
        cabecera.pack(fill="x", padx=14, pady=(10, 0))
        tk.Label(cabecera, text="Nodo " + self.mi_nodo + "  ·  " + self.nombre,
                 bg=FONDO, fg=GRIS, font=("Arial", 10)).pack(side="left")
        self.estado = tk.Label(cabecera, text="● conectado", bg=FONDO, fg="#30d158",
                               font=("Arial", 10))
        self.estado.pack(side="right")

        # pantalla
        self.expresion = tk.Label(self.ventana, text="", bg=FONDO, fg=GRIS,
                                  font=("Arial", 13), anchor="e")
        self.expresion.pack(fill="x", padx=14, pady=(14, 0))
        self.pantalla = tk.Label(self.ventana, text="0", bg=FONDO, fg=TEXTO,
                                 font=("Arial", 40), anchor="e")
        self.pantalla.pack(fill="x", padx=14, pady=(0, 10))

        # botones
        self.botones = tk.Frame(self.ventana, bg=FONDO)
        self.botones.pack(padx=10)
        for columna in range(4):
            self.botones.columnconfigure(columna, weight=1, uniform="col")

        self.boton("C", "Fun", self.limpiar, 0, 0)
        self.boton("⌫", "Fun", self.borrar, 0, 1)
        self.boton("±", "Fun", self.cambiar_signo, 0, 2)
        self.boton("÷", "Op", lambda: self.pulsar_operador("/"), 0, 3)

        self.boton("7", "Num", lambda: self.digito("7"), 1, 0)
        self.boton("8", "Num", lambda: self.digito("8"), 1, 1)
        self.boton("9", "Num", lambda: self.digito("9"), 1, 2)
        self.boton("×", "Op", lambda: self.pulsar_operador("x"), 1, 3)

        self.boton("4", "Num", lambda: self.digito("4"), 2, 0)
        self.boton("5", "Num", lambda: self.digito("5"), 2, 1)
        self.boton("6", "Num", lambda: self.digito("6"), 2, 2)
        self.boton("−", "Op", lambda: self.pulsar_operador("-"), 2, 3)

        self.boton("1", "Num", lambda: self.digito("1"), 3, 0)
        self.boton("2", "Num", lambda: self.digito("2"), 3, 1)
        self.boton("3", "Num", lambda: self.digito("3"), 3, 2)
        self.boton("+", "Op", lambda: self.pulsar_operador("+"), 3, 3)

        self.boton("0", "Num", lambda: self.digito("0"), 4, 0, 2)
        self.boton(".", "Num", self.punto, 4, 2)
        self.boton("=", "Op", self.igual, 4, 3)

        # registro de mensajes (sirve para ver lo que pasa en el Campo de Datos)
        tk.Label(self.ventana, text="Mensajes del Campo de Datos", bg=FONDO, fg=GRIS,
                 font=("Arial", 9)).pack(anchor="w", padx=14, pady=(10, 0))
        self.registro = tk.Text(self.ventana, height=7, width=34, bg="#111113", fg="#d1d1d6",
                                font=("Courier", 9), bd=0, highlightthickness=0,
                                state="disabled")
        self.registro.pack(fill="x", padx=14, pady=(2, 14))

        self.ventana.bind("<Key>", self.tecla)

    def boton(self, texto, estilo, comando, fila, columna, ancho=1):
        b = ttk.Button(self.botones, text=texto, style=estilo + ".TButton",
                       command=comando, width=4, takefocus=False)
        b.grid(row=fila, column=columna, columnspan=ancho, padx=3, pady=3,
               sticky="nsew", ipady=10)

    def tecla(self, evento):
        if evento.keysym == "BackSpace":
            self.borrar()
            return
        if evento.keysym == "Escape":
            self.limpiar()
            return
        if evento.keysym in ("Return", "KP_Enter"):
            self.igual()
            return
        letra = evento.char
        if letra == "":
            return
        if letra in "0123456789":
            self.digito(letra)
        elif letra in (".", ","):
            self.punto()
        elif letra in ("+", "-", "/"):
            self.pulsar_operador(letra)
        elif letra in ("*", "x", "X"):
            self.pulsar_operador("x")
        elif letra == "=":
            self.igual()

    # ---------------- pantalla ----------------
    def poner_pantalla(self, texto):
        tamano = 40
        if len(texto) > 9:
            tamano = 30
        if len(texto) > 13:
            tamano = 20
        self.pantalla.config(text=texto, font=("Arial", tamano))

    def mostrar(self):
        self.poner_pantalla(self.actual)
        if self.operador is not None:
            self.expresion.config(text=bonito(self.primero) + " " + SIMBOLOS[self.operador])

    def agregar_registro(self, texto):
        self.registro.config(state="normal")
        self.registro.insert("end", texto + "\n")
        self.registro.see("end")
        self.registro.config(state="disabled")

    def reiniciar_estado(self):
        self.actual = "0"
        self.primero = None
        self.operador = None
        self.nuevo = True
        self.siguiente_op = None
        self.esperando = False

    # ---------------- botones de la calculadora ----------------
    def digito(self, d):
        if self.esperando:
            return
        if self.nuevo:
            if self.operador is None:
                self.expresion.config(text="")
            self.actual = d
            self.nuevo = False
        elif self.actual == "0":
            self.actual = d
        elif len(self.actual) < 12:
            self.actual += d
        self.mostrar()

    def punto(self):
        if self.esperando:
            return
        if self.nuevo:
            if self.operador is None:
                self.expresion.config(text="")
            self.actual = "0."
            self.nuevo = False
        elif "." not in self.actual:
            self.actual += "."
        self.mostrar()

    def borrar(self):
        if self.esperando or self.nuevo:
            return
        self.actual = self.actual[:-1]
        if self.actual == "" or self.actual == "-":
            self.actual = "0"
        self.mostrar()

    def cambiar_signo(self):
        if self.esperando or self.actual == "0":
            return
        if self.actual.startswith("-"):
            self.actual = self.actual[1:]
        else:
            self.actual = "-" + self.actual
        self.mostrar()

    def limpiar(self):
        self.reiniciar_estado()
        self.pendientes.clear()
        self.expresion.config(text="")
        self.mostrar()

    def pulsar_operador(self, op):
        if self.esperando:
            return
        if self.operador is not None and not self.nuevo:
            # ya habia una operacion con sus dos numeros: se calcula
            # primero y despues seguimos con el operador nuevo
            self.siguiente_op = op
            self.igual()
            return
        self.primero = float(self.actual)
        self.operador = op
        self.nuevo = True
        self.mostrar()

    # ---------------- solicitud y respuesta ----------------
    def igual(self):
        if self.esperando or self.operador is None or self.nuevo:
            return

        a = self.primero
        b = float(self.actual)
        op = self.operador

        solicitud = {
            "id": str(uuid.uuid4()),
            "id_solicitud": None,
            "codigo": CODIGOS[op],
            "origen": self.nombre,
            "operandos": [a, b],
        }
        try:
            enviar(self.sock, solicitud)
        except OSError:
            self.poner_pantalla("Error")
            self.expresion.config(text="No hay conexion con el nodo")
            return

        self.pendientes[solicitud["id"]] = (a, op, b)
        self.esperando = True
        self.expresion.config(text=bonito(a) + " " + SIMBOLOS[op] + " " + bonito(b) + " =")
        self.poner_pantalla("...")
        self.agregar_registro("→ ENVIADA   " + solicitud["codigo"] + "  " + solicitud["id"][:8])
        self.ventana.after(TIEMPO_ESPERA * 1000, lambda: self.revisar_tiempo(solicitud["id"]))

    def revisar_tiempo(self, id_solicitud):
        # si ya paso el tiempo y no llego respuesta, avisamos
        if id_solicitud not in self.pendientes:
            return
        a, op, b = self.pendientes.pop(id_solicitud)
        self.reiniciar_estado()
        self.poner_pantalla("Sin respuesta")
        self.expresion.config(text="¿Hay un servidor de " + NOMBRES[op] + " conectado?")
        self.agregar_registro("! SIN RESPUESTA a " + id_solicitud[:8])

    # este hilo solo lee del socket y mete los mensajes a la cola
    def escuchar(self):
        try:
            for linea in self.lector:
                try:
                    self.cola.put(json.loads(linea))
                except ValueError:
                    pass
        except OSError:
            pass
        self.cola.put({"codigo": "DESCONECTADO"})

    # la ventana revisa la cola cada 100 ms
    def revisar_cola(self):
        while not self.cola.empty():
            mensaje = self.cola.get()
            self.atender(mensaje)
        self.ventana.after(100, self.revisar_cola)

    def atender(self, mensaje):
        codigo = mensaje.get("codigo", "")

        if codigo == "DESCONECTADO":
            self.estado.config(text="● desconectado", fg="#ff453a")
            self.reiniciar_estado()
            self.poner_pantalla("Sin conexion")
            return

        # solo nos importan las respuestas a solicitudes que hicimos nosotros
        if not codigo.endswith("_RES"):
            return
        id_solicitud = mensaje.get("id_solicitud")
        if id_solicitud not in self.pendientes:
            return

        a, op, b = self.pendientes.pop(id_solicitud)
        self.agregar_registro("← RESPUESTA " + codigo + "  de " + str(mensaje.get("origen")))

        siguiente = self.siguiente_op
        self.reiniciar_estado()
        self.expresion.config(text=bonito(a) + " " + SIMBOLOS[op] + " " + bonito(b) + " =")

        if mensaje.get("error"):
            self.poner_pantalla("Error")
            self.expresion.config(text=mensaje["error"])
            return

        self.actual = bonito(mensaje["resultado"])
        self.mostrar()

        # si el usuario ya habia pulsado otro operador, seguimos con el
        if siguiente is not None:
            self.pulsar_operador(siguiente)

    def correr(self):
        self.ventana.mainloop()


if len(sys.argv) < 2:
    print("Uso: python celula_gui.py <host:puerto> [nombre]")
    sys.exit()

host, puerto = sys.argv[1].split(":")
if len(sys.argv) > 2:
    nombre = sys.argv[2]
else:
    nombre = "GUI-" + uuid.uuid4().hex[:4]

app = CalculadoraGUI(host, int(puerto), nombre)
app.correr()