import socket
import threading
import json

HOST = '127.0.0.1'
PORT = 8081

clientes_conectados = []
servidores_conectados = []

def manejar_conexion(conexion, direccion):
    print(f"Nuevo hilo creado para atender a {direccion}")
    try:
        # 1. Presentación
        datos_brutos = conexion.recv(1024)
        if not datos_brutos:
            return
        
        mensaje = json.loads(datos_brutos.decode('utf-8'))
        tipo_nodo = mensaje.get("tipo_nodo")
        
        if tipo_nodo == "cliente":
            clientes_conectados.append(conexion)
            print(f"-> Cliente registrado exitosamente desde {direccion}")
        elif tipo_nodo == "servidor":
            servidores_conectados.append(conexion)
            print(f"-> Servidor registrado exitosamente desde {direccion}")
        else:
            print(f"-> Tipo de nodo desconocido desde {direccion}")
            return

        # 2. EL PUENTE (Ruteo de mensajes)
        while True:
            datos = conexion.recv(1024)
            if not datos:
                break
            
            # Si el mensaje viene de un cliente, lo mandamos al servidor
            if tipo_nodo == "cliente":
                if len(servidores_conectados) > 0:
                    servidor_destino = servidores_conectados[0]
                    servidor_destino.sendall(datos)
                else:
                    print("Mensaje ignorado: No hay servidores conectados.")
            
            # Si el mensaje viene de un servidor, lo mandamos al cliente
            elif tipo_nodo == "servidor":
                if len(clientes_conectados) > 0:
                    cliente_destino = clientes_conectados[0]
                    cliente_destino.sendall(datos)
                else:
                    print("Mensaje ignorado: No hay clientes conectados.")

    except Exception as e:
        print(f"Error procesando la conexión de {direccion}: {e}")
    finally:
        if conexion in clientes_conectados:
            clientes_conectados.remove(conexion)
        if conexion in servidores_conectados:
            servidores_conectados.remove(conexion)
        conexion.close()

# Configuración del socket principal
servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
servidor_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
servidor_socket.bind((HOST, PORT))
servidor_socket.listen()

print("Middleware encendido y escuchando...")

while True:
    conexion, direccion = servidor_socket.accept()
    print(f"Se conectó alguien desde {direccion}")
    hilo = threading.Thread(target=manejar_conexion, args=(conexion, direccion))
    hilo.start()