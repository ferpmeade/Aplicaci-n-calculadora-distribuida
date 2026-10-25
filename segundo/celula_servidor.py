# celula_servidor.py
# Celula servidor: atiende un servicio (suma, resta, multiplicacion o division)
#
# Uso:
#   python celula_servidor.py <servicio> <host:puerto del nodo> [nombre]
#
# Ejemplo:
#   python celula_servidor.py suma 127.0.0.1:5001 SUM-N1

import socket
import json
import sys
import time
import uuid

# servicio -> (codigo de solicitud, codigo de respuesta)
SERVICIOS = {
    "suma": ("SUM_REQ", "SUM_RES"),
    "resta": ("SUB_REQ", "SUB_RES"),
    "multiplicacion": ("MUL_REQ", "MUL_RES"),
    "division": ("DIV_REQ", "DIV_RES"),
}


def enviar(sock, mensaje):
    texto = json.dumps(mensaje) + "\n"
    sock.sendall(texto.encode("utf-8"))


def log(nombre, texto):
    hora = time.strftime("%H:%M:%S")
    print("[" + hora + "] [" + nombre + "] " + texto, flush=True)


def calcular(servicio, a, b):
    # regresa (resultado, error)
    if servicio == "suma":
        return a + b, None
    if servicio == "resta":
        return a - b, None
    if servicio == "multiplicacion":
        return a * b, None
    if servicio == "division":
        if b == 0:
            return None, "No se puede dividir entre cero"
        return a / b, None


if len(sys.argv) < 3:
    print("Uso: python celula_servidor.py <suma|resta|multiplicacion|division> <host:puerto> [nombre]")
    sys.exit()

servicio = sys.argv[1]
if servicio not in SERVICIOS:
    print("Servicio no valido: " + servicio)
    sys.exit()

host, puerto = sys.argv[2].split(":")
if len(sys.argv) > 3:
    nombre = sys.argv[3]
else:
    nombre = servicio + "-" + uuid.uuid4().hex[:4]

codigo_req, codigo_res = SERVICIOS[servicio]

# nos conectamos al nodo y mandamos el HELLO
sock = socket.create_connection((host, int(puerto)))
enviar(sock, {"tipo": "HELLO", "entidad": "SERVIDOR", "nombre": nombre, "servicio": servicio})
lector = sock.makefile("r", encoding="utf-8")

respuesta = json.loads(lector.readline())
if respuesta.get("tipo") != "BIENVENIDA":
    print("El nodo rechazo la conexion: " + str(respuesta))
    sys.exit()

mi_nodo = respuesta["nodo"]
log(nombre, "Servidor de " + servicio + " conectado al nodo " + mi_nodo)

for linea in lector:
    try:
        mensaje = json.loads(linea)
    except ValueError:
        continue

    # solo nos interesan las solicitudes de nuestro servicio
    if mensaje.get("codigo") != codigo_req:
        continue

    # Para evitar respuestas duplicadas: de todos los servidores del mismo
    # tipo que reciben la solicitud, solo contesta el que esta conectado al
    # mismo nodo por donde entro la solicitud (nodo_origen).
    if mensaje.get("nodo_origen") != mi_nodo:
        log(nombre, "Solicitud " + mensaje["id"][:8] + " la atiende el servidor del nodo " + str(mensaje.get("nodo_origen")) + ", la ignoro")
        continue

    a, b = mensaje["operandos"]
    resultado, error = calcular(servicio, a, b)
    log(nombre, "Atendiendo " + codigo_req + " id=" + mensaje["id"][:8] + ": " + str(a) + " , " + str(b) + " = " + str(resultado))

    # la respuesta lleva su propio id y una referencia a la solicitud
    nueva = {
        "id": str(uuid.uuid4()),
        "id_solicitud": mensaje["id"],
        "codigo": codigo_res,
        "origen": nombre,
        "resultado": resultado,
        "error": error,
    }
    enviar(sock, nueva)

log(nombre, "Se cerro la conexion con el nodo")