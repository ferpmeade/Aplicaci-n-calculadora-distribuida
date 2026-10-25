import socket
import json
import sqlite3

HOST = '127.0.0.1'
PORT = 8081

# Función para inicializar la base de datos local del servidor
def inicializar_bd():
    conexion_db = sqlite3.connect("historial_servidor.db")
    cursor = conexion_db.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operacion TEXT,
            resultado REAL
        )
    ''')
    conexion_db.commit()
    conexion_db.close()

# Llamamos a la función al arrancar
inicializar_bd()

# Configuración del socket
servidor_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
print("intentando conectar con el middleware...")
servidor_socket.connect((HOST, PORT))

# Presentación
presentacion = {"tipo_nodo": "servidor"}
servidor_socket.sendall(json.dumps(presentacion).encode('utf-8'))
print("presentacion enviada al middleware")

# Ciclo infinito para escuchar y procesar tareas
while True:
    datos_tarea = servidor_socket.recv(1024)
    if not datos_tarea:
        break
    
    tarea = json.loads(datos_tarea.decode('utf-8'))
    print(f"tarea recibida: {tarea}")
    
    # 1. Extraemos los datos
    op = tarea.get("operacion")
    n1 = tarea.get("num1")
    n2 = tarea.get("num2")
    
    # 2. Hacemos el cálculo
    resultado = 0
    if op == "suma":
        resultado = n1 + n2
    elif op == "resta":
        resultado = n1 - n2
    elif op == "multiplicacion":
        resultado = n1 * n2
    elif op == "division":
        resultado = n1 / n2 if n2 != 0 else "Error: División por cero"
        
    print(f"Resultado calculado: {resultado}")
    
    # 3. Guardamos en SQLite (Persistencia)
    conexion_db = sqlite3.connect("historial_servidor.db")
    cursor = conexion_db.cursor()
    cursor.execute("INSERT INTO operaciones (operacion, resultado) VALUES (?, ?)", (f"{n1} {op} {n2}", str(resultado)))
    conexion_db.commit()
    conexion_db.close()
    print("Resultado guardado en SQLite exitosamente.")
    
    # 4. Enviamos la respuesta de regreso al middleware
    respuesta = {"resultado": resultado}
    servidor_socket.sendall(json.dumps(respuesta).encode('utf-8'))