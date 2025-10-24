#recebe conexoes e trata comandos
import socket
import json
import struct
from datetime import datetime
import threading
import os

HOST = '0.0.0.0'
PORT = 50000

clientes = []  # Lista de conexões ativas
mural = []     # Lista de mensagens
mural_file = "mural.json"

# Carrega mural de arquivo, se existir
if os.path.exists(mural_file):
    with open(mural_file, "r", encoding="utf-8") as f:
        mural = json.load(f)

# Funções auxiliares
def receber_mensagem(conn):
    try:
        cabecalho = conn.recv(4)
        if not cabecalho:
            return None, None
        comando, versao, tamanho_payload = struct.unpack('>BBH', cabecalho)
        payload_bytes = conn.recv(tamanho_payload)
        payload = json.loads(payload_bytes.decode('utf-8'))
        return comando, payload
    except:
        return None, None

def enviar_mensagem(conn, comando, payload):
    payload_bytes = json.dumps(payload).encode('utf-8')
    cabecalho = struct.pack('>BBH', comando, 1, len(payload_bytes))
    try:
        conn.sendall(cabecalho + payload_bytes)
    except:
        pass

def salvar_mural():
    with open(mural_file, "w", encoding="utf-8") as f:
        json.dump(mural, f, ensure_ascii=False, indent=2)

def handle_cliente(conn, addr):
    global mural
    print(f"Conectado com {addr}")
    username = None
    clientes.append(conn)
    try:
        while True:
            comando, payload = receber_mensagem(conn)
            if comando is None:
                break

            if comando == 1:  # LOGIN
                username = payload.get("username", "Anonimo")
                enviar_mensagem(conn, 101, {"message": "Login realizado com sucesso!"})
                print(f"{username} fez login")

            elif comando == 2:  # POST_MESSAGE
                msg = {
                    "author": username,
                    "message": payload["message"],
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
                mural.append(msg)
                salvar_mural()
                # Envia para todos os clientes conectados
                for c in clientes:
                    enviar_mensagem(c, 102, msg)
                print(f"[{username}] postou: {payload['message']}")

            elif comando == 3:  # GET_HISTORY
                enviar_mensagem(conn, 103, {"messages": mural})

            elif comando == 4:  # LOGOUT
                print(f"{username} saiu.")
                break

    finally:
        conn.close()
        if conn in clientes:
            clientes.remove(conn)
        print(f"Conexão encerrada com {addr}")

def servidor():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Servidor escutando em {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            thread = threading.Thread(target=handle_cliente, args=(conn, addr))
            thread.start()

if __name__ == "__main__":
    servidor()
