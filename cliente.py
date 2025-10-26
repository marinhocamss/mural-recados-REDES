import socket
import json
import struct
import threading

HOST = '192.168.0.89'  # ou IP do servidor
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
def escutar_servidor(sock, ativo_flag, pending):
    while ativo_flag[0]:
        cmd, payload = receber_mensagem(sock)
        if cmd is None:
            print("\nServidor desconectado. Encerrando cliente...")
            ativo_flag[0] = False
            try:
                pending['event'].set()
            except:
                pass
            break

        if cmd == 102:
            print(f"\n[{payload['author']}]: {payload['message']}")
            if pending['type'] == 'post' and \
               payload.get('author') == pending.get('username') and \
               payload.get('message') == pending.get('expected'):
                pending['event'].set()

        elif cmd == 103:
            print("\n--- Histórico de mensagens ---")
            for msg in payload['messages']:
                print(f"[{msg['author']}]: {msg['message']}")
            print("--- Fim do histórico ---")
            if pending['type'] == 'history':
                pending['event'].set()

        elif cmd == 101:  # Login OK
            print(payload['message'])

def cliente():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.connect((HOST, PORT))
        except Exception as e:
            print("Não foi possível conectar ao servidor:", e)
            return

        print("Conectado com o servidor!")

        username = input("Digite seu nome de usuário: ")
        enviar_mensagem(s, 1, {"username": username})

        # flag compartilhada entre as threads
        ativo = [True]

        # estrutura para sincronizar POST/HISTORY entre threads
        pending = {
            'type': None,
            'event': threading.Event(),
            'expected': None,      
            'username': username
        }

        listener = threading.Thread(target=escutar_servidor, args=(s, ativo, pending), daemon=True)
        listener.start()

        while ativo[0]:
            print("\nComandos: 1=POST, 2=HISTÓRICO, 3=LOGOUT")
            cmd = input("Escolha um comando: ").strip()

            if not ativo[0]:
                break

            try:
                if cmd == '1':
                    msg = input("Digite sua mensagem: ")
                    # prepara sincronização e envia
                    pending['type'] = 'post'
                    pending['expected'] = msg
                    pending['event'].clear()
                    enviar_mensagem(s, 2, {"message": msg})
                    # espera ate receber o broadcast correspondente (ou timeout)
                    recebido = pending['event'].wait(timeout=5)
                    if recebido:
                        print("Mensagem enviada e eco recebida.")
                    else:
                        print("Mensagem enviada (sem confirmação do servidor).")
                    # reset
                    pending['type'] = None
                    pending['expected'] = None

                elif cmd == '2':
                    pending['type'] = 'history'
                    pending['event'].clear()
                    enviar_mensagem(s, 3, {})
                    recebido = pending['event'].wait(timeout=5)
                    if not recebido:
                        print("Histórico solicitado (sem resposta do servidor).")
                    pending['type'] = None

                elif cmd == '3':
                    enviar_mensagem(s, 4, {})
                    print("Logout enviado. Saindo...")
                    ativo[0] = False
                    break
                else:
                    print("Comando inválido.")
            except (ConnectionResetError, OSError):
                print("\nConexão perdida com o servidor. Encerrando cliente...")
                ativo[0] = False
                try:
                    pending['event'].set()
                except:
                    pass
                break

        # espera a thread de escuta encerrar
        listener.join(timeout=1)

if __name__ == "__main__":
    cliente()
