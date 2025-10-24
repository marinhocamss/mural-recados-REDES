#conecta e envia mensagens

import socket
import json
import struct
import threading

HOST = '127.0.0.1'  # ou IP do servidor
PORT = 50000

def enviar_mensagem(sock, comando, payload):
    payload_bytes = json.dumps(payload).encode('utf-8')
    cabecalho = struct.pack('>BBH', comando, 1, len(payload_bytes))
    sock.sendall(cabecalho + payload_bytes)

def receber_mensagem(sock):
    try:
        cabecalho = sock.recv(4)
        if not cabecalho:
            return None, None
        comando, versao, tamanho_payload = struct.unpack('>BBH', cabecalho)
        payload_bytes = sock.recv(tamanho_payload)
        payload = json.loads(payload_bytes.decode('utf-8'))
        return comando, payload
    except:
        return None, None

# Thread para receber mensagens do servidor continuamente
def escutar_servidor(sock):
    while True:
        cmd, payload = receber_mensagem(sock)
        if cmd is None:
            break
        if cmd == 102:  # Broadcast nova mensagem
            print(f"\n[{payload['author']}]: {payload['message']}")
        elif cmd == 103:  # Histórico
            print("\n--- Histórico de mensagens ---")
            for msg in payload['messages']:
                print(f"[{msg['author']}]: {msg['message']}")
            print("--- Fim do histórico ---")
        elif cmd == 101:  # Login OK
            print(payload['message'])

def cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        print("Conectado com o servidor!")

        username = input("Digite seu nome de usuário: ")
        enviar_mensagem(s, 1, {"username": username})

        # Thread para escutar mensagens
        threading.Thread(target=escutar_servidor, args=(s,), daemon=True).start()

        while True:
            print("\nComandos: 1=POST, 2=HISTÓRICO, 3=LOGOUT")
            cmd = input("Escolha um comando: ").strip()
            if cmd == '1':
                msg = input("Digite sua mensagem: ")
                enviar_mensagem(s, 2, {"message": msg})
            elif cmd == '2':
                enviar_mensagem(s, 3, {})
            elif cmd == '3':
                enviar_mensagem(s, 4, {})
                print("Logout enviado. Saindo...")
                break
            else:
                print("Comando inválido.")

if __name__ == "__main__":
    cliente()
