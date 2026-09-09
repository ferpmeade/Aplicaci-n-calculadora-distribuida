import socket
import json
import threading

HOST = '127.0.0.1'
PORT = 8081

#creamos servidor socket
servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("intentando conectar con el middleware...")
servidor_socket.connect((HOST, PORT))

presentacion = {
    "tipo_nodo": "servidor"
}

servidor_socket.sendall(json.dumps(presentacion).encode('utf-8'))
print("presentacion enviada al middleware")


while True:
    datos_tarea= servidor_socket.recv(1024)
    if not datos_tarea:
        break

    tarea = json.loads(datos_tarea.decode('utf-8'))
    print(f"tarea recibida: {tarea}")