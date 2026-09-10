import socket
import json
import threading
import tkinter as tk
from tkinter import ttk

HOST = '127.0.0.1'
PORT = 8081

# conexión con el middleware
cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente_socket.connect((HOST, PORT))

presentacion = {"tipo_nodo": "cliente"}
cliente_socket.sendall(json.dumps(presentacion).encode('utf-8'))

def escuchar_respuestas():
    while True:
        try:
            datos_respuesta = cliente_socket.recv(1024)
            if not datos_respuesta:
                break

            respuesta = json.loads(datos_respuesta.decode('utf-8'))
            respuesta_final = respuesta.get("respuesta")


            etiqueta_resultado.config(text=f"Respuesta: {respuesta_final}")
        except Exception as e:
            print(f"Error al recibir respuesta: {e}")
            break

hilo_escucha = threading.Thread(target=escuchar_respuestas, daemon=True)
hilo_escucha.start()

#funcion para el clic de calcular
def enviar_operacion():

    n1 = float(entrada_num1.get())
    n2 = float(entrada_num2.get())
    operacion = combo_operacion.get()

    peticion = {
        "operacion": operacion,
        "num1": n1,
        "num2": n2
    }

    cliente_socket.sendall(json.dumps(peticion).encode('utf-8'))
    etiqueta_resultado.config(text="calculandoo...")


ventana = tk.Tk()
ventana.title("Calculadora Distribuida")
ventana.geometry("300x250")

# Elementos de la interfaz
tk.Label(ventana, text="Número 1:").pack(pady=5)
entrada_num1 = tk.Entry(ventana)
entrada_num1.pack()

tk.Label(ventana, text="Operación:").pack(pady=5)
combo_operacion = ttk.Combobox(ventana, values=["suma", "resta", "multiplicacion", "division"], state="readonly")
combo_operacion.set("suma") # Valor por defecto
combo_operacion.pack()

tk.Label(ventana, text="Número 2:").pack(pady=5)
entrada_num2 = tk.Entry(ventana)
entrada_num2.pack()

tk.Button(ventana, text="Calcular", command=enviar_operacion).pack(pady=15)

etiqueta_resultado = tk.Label(ventana, text="Resultado: ", font=("Arial", 12, "bold"))
etiqueta_resultado.pack(pady=5)

# Arrancamos la ventana
ventana.mainloop()

