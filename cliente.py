import socket
import json
import threading
import tkinter as tk

HOST = '127.0.0.1'
PORT = 8081

# 1. Configuración de conexión
cliente_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
cliente_socket.connect((HOST, PORT))

presentacion = {"tipo_nodo": "cliente"}
cliente_socket.sendall(json.dumps(presentacion).encode('utf-8'))

def escuchar_respuestas():
    while True:
        try:
            datos = cliente_socket.recv(1024)
            if not datos:
                break
            
            respuesta = json.loads(datos.decode('utf-8'))
            respuesta_final = respuesta.get("resultado")
            
            # Mostramos el resultado en la pantalla grande
            pantalla_resultado.config(text=f"{respuesta_final}", fg="#00FF00")
        except Exception as e:
            print("Conexión cerrada:", e)
            break

hilo_escucha = threading.Thread(target=escuchar_respuestas, daemon=True)
hilo_escucha.start()

def enviar_operacion():
    try:
        n1 = float(entrada_num1.get())
        n2 = float(entrada_num2.get())
        operacion = variable_operacion.get()
        
        peticion = {
            "operacion": operacion,
            "num1": n1,
            "num2": n2
        }
        
        cliente_socket.sendall(json.dumps(peticion).encode('utf-8'))
        # Texto amarillo mientras espera
        pantalla_resultado.config(text="CALCULANDO...", fg="#FFFF00")
    except ValueError:
        # Texto rojo si hay error
        pantalla_resultado.config(text="ERROR", fg="#FF0000")

# ==========================================
# 2. INTERFAZ: DISEÑO DE CALCULADORA FÍSICA
# ==========================================
ventana = tk.Tk()
ventana.title("Calc_Distribuida")
ventana.geometry("350x450")
ventana.configure(bg="#000000") # Fondo negro puro

fuente_base = ("Consolas", 12)
fuente_titulo = ("Consolas", 14, "bold")

# Título pequeño
titulo = tk.Label(ventana, text="TERMINAL_CALC v1.0", font=fuente_titulo, bg="#000000", fg="#555555")
titulo.pack(pady=(15, 5))

# --- EL CUADRO DE LA PANTALLA ---
frame_pantalla = tk.Frame(ventana, bg="#111111", bd=2, relief="solid")
frame_pantalla.pack(pady=10, padx=20, fill="x")

pantalla_resultado = tk.Label(frame_pantalla, text="0.0", font=("Consolas", 24, "bold"), bg="#050505", fg="#00FF00", anchor="e", padx=15, pady=15)
pantalla_resultado.pack(fill="x")
# --------------------------------

frame_campos = tk.Frame(ventana, bg="#000000")
frame_campos.pack(pady=15)

# Fila 0: Número 1
tk.Label(frame_campos, text="NUM 1:", font=fuente_base, bg="#000000", fg="#FFFFFF").grid(row=0, column=0, padx=10, pady=10, sticky="e")
entrada_num1 = tk.Entry(frame_campos, font=fuente_base, width=14, justify="center", bg="#111111", fg="#FFFFFF", insertbackground="white", relief="solid", bd=1)
entrada_num1.grid(row=0, column=1, padx=10, pady=10)

# Fila 1: Operación
tk.Label(frame_campos, text="OP:", font=fuente_base, bg="#000000", fg="#FFFFFF").grid(row=1, column=0, padx=10, pady=10, sticky="e")
variable_operacion = tk.StringVar(ventana)
variable_operacion.set("suma")
combo_operacion = tk.OptionMenu(frame_campos, variable_operacion, "suma", "resta", "multiplicacion", "division")
combo_operacion.config(bg="#111111", fg="#FFFFFF", font=fuente_base, activebackground="#333333", activeforeground="#FFFFFF", relief="solid", bd=1, highlightthickness=0)
combo_operacion["menu"].config(bg="#111111", fg="#FFFFFF", font=fuente_base)
combo_operacion.grid(row=1, column=1, padx=10, pady=10, sticky="ew")

# Fila 2: Número 2
tk.Label(frame_campos, text="NUM 2:", font=fuente_base, bg="#000000", fg="#FFFFFF").grid(row=2, column=0, padx=10, pady=10, sticky="e")
entrada_num2 = tk.Entry(frame_campos, font=fuente_base, width=14, justify="center", bg="#111111", fg="#FFFFFF", insertbackground="white", relief="solid", bd=1)
entrada_num2.grid(row=2, column=1, padx=10, pady=10)

# Botón Calcular 
boton_calcular = tk.Button(ventana, text="EJECUTAR", font=("Consolas", 14, "bold"), bg="#FFFFFF", fg="#000000", activebackground="#CCCCCC", activeforeground="#000000", relief="flat", cursor="hand2", command=enviar_operacion)
boton_calcular.pack(pady=20, ipadx=30, ipady=5)

ventana.mainloop()