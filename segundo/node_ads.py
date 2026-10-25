# nodo.py
# Nodo del Campo de Datos (arquitectura ADS)
#
# Uso:
#   python nodo.py <nombre> <puerto> [vecino1 vecino2 ...]
#
# Ejemplos:
#   python nodo.py N1 5001
#   python nodo.py N2 5002 127.0.0.1:5001
#   python nodo.py N3 5003 127.0.0.1:5001 127.0.0.1:5002
#
# Cada nodo se conecta a los vecinos que le pasemos y acepta conexiones
# de otros nodos y de celulas (GUI y servidores). No hay nodo maestro:
# todos los nodos corren exactamente el mismo programa.

import socket
import threading
import json
import sys
import time

# cuantos segundos guardamos los ids de mensajes ya vistos
TIEMPO_VISTOS = 120


def enviar(sock, mensaje):
    # cada mensaje es un JSON en una linea
    texto = json.dumps(mensaje) + "\n"
    sock.sendall(texto.encode("utf-8"))


class Nodo:
    def __init__(self, nombre, puerto):
        self.nombre = nombre
        self.puerto = puerto
        self.conexiones = {}   # nombre -> {"sock": ..., "tipo": ...}
        self.vistos = {}       # id del mensaje -> hora en que lo vimos
        self.candado = threading.RLock()
        self.archivo_log = "bitacora_" + nombre + ".txt"

    # ---------------- bitacora ----------------
    def log(self, texto):
        hora = time.strftime("%H:%M:%S")
        linea = "[" + hora + "] [" + self.nombre + "] " + texto
        with self.candado:
            print(linea, flush=True)
            archivo = open(self.archivo_log, "a", encoding="utf-8")
            archivo.write(linea + "\n")
            archivo.close()

    # ---------------- arranque ----------------
    def iniciar(self):
        self.servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.servidor.bind(("0.0.0.0", self.puerto))
        self.servidor.listen()
        self.log("Nodo iniciado, escuchando en el puerto " + str(self.puerto))
        hilo = threading.Thread(target=self.aceptar_conexiones, daemon=True)
        hilo.start()

    def aceptar_conexiones(self):
        while True:
            sock, direccion = self.servidor.accept()
            hilo = threading.Thread(target=self.recibir_conexion, args=(sock,), daemon=True)
            hilo.start()

    # ---------------- protocolo de conexion ----------------
    # Quien se conecta manda un HELLO con su tipo (NODO, GUI o SERVIDOR)
    # y su nombre. El nodo contesta con BIENVENIDA y su propio nombre.

    def recibir_conexion(self, sock):
        lector = sock.makefile("r", encoding="utf-8")
        try:
            hola = json.loads(lector.readline())
            nombre = hola["nombre"]
            tipo = hola["entidad"]
        except (ValueError, KeyError, OSError):
            sock.close()
            return

        with self.candado:
            if nombre in self.conexiones:
                enviar(sock, {"tipo": "ERROR", "detalle": "nombre repetido"})
                sock.close()
                self.log("Conexion rechazada, el nombre " + nombre + " ya existe")
                return

        enviar(sock, {"tipo": "BIENVENIDA", "nodo": self.nombre})
        self.registrar(nombre, tipo, sock)
        self.leer_mensajes(nombre, lector)

    def conectar_vecino(self, host, puerto):
        try:
            sock = socket.create_connection((host, puerto), timeout=5)
            sock.settimeout(None)
        except OSError:
            self.log("No pude conectarme a " + host + ":" + str(puerto))
            return

        enviar(sock, {"tipo": "HELLO", "entidad": "NODO", "nombre": self.nombre})
        lector = sock.makefile("r", encoding="utf-8")
        try:
            respuesta = json.loads(lector.readline())
            nombre_vecino = respuesta["nodo"]
        except (ValueError, KeyError, OSError):
            self.log("El vecino " + host + ":" + str(puerto) + " no respondio bien")
            sock.close()
            return

        self.registrar(nombre_vecino, "NODO", sock)
        hilo = threading.Thread(target=self.leer_mensajes, args=(nombre_vecino, lector), daemon=True)
        hilo.start()

    def registrar(self, nombre, tipo, sock):
        with self.candado:
            self.conexiones[nombre] = {"sock": sock, "tipo": tipo}
        self.log("Conectado: " + nombre + " (" + tipo + "). Conexiones activas: " + str(len(self.conexiones)))

    def quitar(self, nombre):
        with self.candado:
            if nombre in self.conexiones:
                self.conexiones[nombre]["sock"].close()
                del self.conexiones[nombre]
        self.log("Desconectado: " + nombre)

    # ---------------- protocolo de comunicacion ----------------
    def leer_mensajes(self, nombre, lector):
        try:
            for linea in lector:
                linea = linea.strip()
                if linea == "":
                    continue
                try:
                    mensaje = json.loads(linea)
                except ValueError:
                    continue
                self.procesar(mensaje, nombre)
        except OSError:
            pass
        self.quitar(nombre)

    def limpiar_vistos(self):
        ahora = time.time()
        viejos = []
        for id_mensaje in self.vistos:
            if ahora - self.vistos[id_mensaje] > TIEMPO_VISTOS:
                viejos.append(id_mensaje)
        for id_mensaje in viejos:
            del self.vistos[id_mensaje]

    def procesar(self, mensaje, de):
        id_mensaje = mensaje.get("id")
        if id_mensaje is None:
            return

        with self.candado:
            # prevencion de ciclos: si ya vimos este id, no lo retransmitimos
            if id_mensaje in self.vistos:
                self.log("DUPLICADO descartado id=" + id_mensaje[:8] + " (llego de " + de + ")")
                return
            self.vistos[id_mensaje] = time.time()
            self.limpiar_vistos()
            conexion = self.conexiones.get(de)

        if conexion is None:
            return

        # si el mensaje viene de una GUI, marcamos en que nodo entro al campo
        if conexion["tipo"] == "GUI":
            mensaje["nodo_origen"] = self.nombre

        self.log("RECIBIDO " + str(mensaje.get("codigo")) + " id=" + id_mensaje[:8] + " de " + de)
        self.difundir(mensaje, de)

    def difundir(self, mensaje, excepto):
        # broadcast: lo mandamos a todos menos a quien nos lo mando
        enviados = []
        with self.candado:
            for nombre in list(self.conexiones):
                if nombre == excepto:
                    continue
                try:
                    enviar(self.conexiones[nombre]["sock"], mensaje)
                    enviados.append(nombre)
                except OSError:
                    self.log("Error al enviar a " + nombre)
        self.log("   REENVIADO id=" + mensaje["id"][:8] + " a: " + ", ".join(enviados))


# ---------------- programa principal ----------------
if len(sys.argv) < 3:
    print("Uso: python nodo.py <nombre> <puerto> [vecino1 vecino2 ...]")
    print("Ejemplo: python nodo.py N2 5002 127.0.0.1:5001")
    sys.exit()

nodo = Nodo(sys.argv[1], int(sys.argv[2]))
nodo.iniciar()

for vecino in sys.argv[3:]:
    host, puerto = vecino.split(":")
    nodo.conectar_vecino(host, int(puerto))

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("Nodo cerrado")