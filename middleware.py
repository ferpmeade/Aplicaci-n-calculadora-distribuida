import socket
import threading
import json

middleware_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
HOST= '127.0.0.1'
PORT = 8081

#listas
clientes_conectados = []
servidores_conectados = []

def manejar_conexion(conexion, direccion):
    print(f"nuevo hilo creado para atender a {direccion}")
    try:

        datos_brutos = conexion.recv(1024)
        if not datos_brutos:
            return

        #convertir los datos de bytes a string
        mensaje  = json.loads(datos_brutos.decode('utf-8'))
        tipo_nodo = mensaje.get("tipo_nodo")

        #clasificiar el tipo de nodo
        if tipo_nodo == "cliente":
            clientes_conectados.append(conexion)
            print(f"cliente conectado desde {direccion}")
        elif tipo_nodo == "servidor":
            servidores_conectados.append(conexion)
            print(f"servidor conectado desde {direccion}")
        else:
            print(f"tipo de nodo desconocido desde {direccion}")

    except Exception as e:
        print(f"error procesando la conexion desde {direccion}: {e}")
        conexion.close()


def iniciar_middleware():
    middleware_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    middleware_socket.bind((HOST, PORT))

    middleware_socket.listen()
    print("middleware encencido y escuchando...")

    while True:
        connection, direccion = middleware_socket.accept()
        print(f"se conecto alguien desde {direccion}")

        hilo_cliente = threading.Thread(target=manejar_conexion, args=(connection, direccion))
        hilo_cliente.start()


if __name__ == "__main__":
    iniciar_middleware()