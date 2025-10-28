import socket
import json
import struct
import threading
import tkinter as tk
from tkinter import scrolledtext, messagebox


# ----------------------- Funções de rede -----------------------

def enviar_mensagem(sock, comando, payload):
    """Envia uma mensagem com cabeçalho e JSON codificado."""
    payload_bytes = json.dumps(payload).encode('utf-8')
    cabecalho = struct.pack('>BBH', comando, 1, len(payload_bytes))
    sock.sendall(cabecalho + payload_bytes)


def receber_mensagem(sock):
    """Recebe mensagens do servidor (protocolo: cabeçalho + JSON)."""
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


# ----------------------- Classe principal -----------------------

class ClienteMural:
    def __init__(self, root):
        self.root = root
        self.root.title("💬 Mural de Recados - Cliente")
        self.root.geometry("600x520")

        self.sock = None
        self.username = None
        self.ativo = [False]

        # Telas
        self.frame_login = tk.Frame(root)
        self.frame_chat = tk.Frame(root)

        self.criar_tela_login()
        self.criar_tela_chat()

        self.frame_login.pack(fill="both", expand=True)

    # ----------------------- Tela de login -----------------------

    def criar_tela_login(self):
        tk.Label(self.frame_login, text="💬 Conectar ao Mural de Recados", font=("Arial", 14, "bold")).pack(pady=10)

        # Campo para IP
        form_ip = tk.Frame(self.frame_login)
        form_ip.pack(pady=5)
        tk.Label(form_ip, text="Endereço IP:").grid(row=0, column=0, padx=5)
        self.entry_ip = tk.Entry(form_ip, font=("Arial", 11), width=20)
        self.entry_ip.insert(0, "146.164.2.101")  # Valor padrão
        self.entry_ip.grid(row=0, column=1, padx=5)

        # Campo para Porta
        tk.Label(form_ip, text="Porta:").grid(row=0, column=2, padx=5)
        self.entry_port = tk.Entry(form_ip, font=("Arial", 11), width=8)
        self.entry_port.insert(0, "50000")
        self.entry_port.grid(row=0, column=3, padx=5)

        # Campo para Nome de Usuário
        tk.Label(self.frame_login, text="Nome de usuário:", font=("Arial", 12)).pack(pady=10)
        self.entry_username = tk.Entry(self.frame_login, font=("Arial", 12))
        self.entry_username.pack(pady=5)

        # Botão de Conexão
        self.btn_conectar = tk.Button(self.frame_login, text="Conectar", font=("Arial", 12), command=self.conectar_servidor)
        self.btn_conectar.pack(pady=10)

    # ----------------------- Tela principal -----------------------

    def criar_tela_chat(self):
        tk.Label(self.frame_chat, text="💬 Mural de Mensagens", font=("Arial", 14, "bold")).pack(pady=10)

        self.text_area = scrolledtext.ScrolledText(self.frame_chat, wrap=tk.WORD, width=70, height=20, font=("Arial", 11))
        self.text_area.pack(padx=10, pady=5)
        self.text_area.config(state=tk.DISABLED)

        form = tk.Frame(self.frame_chat)
        form.pack(pady=10)
        tk.Label(form, text="Destinatário:").grid(row=0, column=0, padx=5)
        self.entry_dest = tk.Entry(form, width=15)
        self.entry_dest.grid(row=0, column=1, padx=5)

        tk.Label(form, text="Mensagem:").grid(row=0, column=2, padx=5)
        self.entry_msg = tk.Entry(form, width=30)
        self.entry_msg.grid(row=0, column=3, padx=5)

        tk.Button(form, text="Enviar", command=self.enviar_msg).grid(row=0, column=4, padx=5)
        tk.Button(self.frame_chat, text="📜 Ver histórico", command=self.pedir_historico).pack(pady=5)
        tk.Button(self.frame_chat, text="🚪 Sair", command=self.logout).pack(pady=5)

    # ----------------------- Conexão -----------------------

    def conectar_servidor(self):
        self.username = self.entry_username.get().strip()
        host = self.entry_ip.get().strip()
        port_text = self.entry_port.get().strip()

        if not self.username:
            messagebox.showwarning("Atenção", "Digite um nome de usuário!")
            return
        if not host:
            messagebox.showwarning("Atenção", "Digite o endereço IP do servidor!")
            return
        if not port_text.isdigit():
            messagebox.showwarning("Atenção", "Porta inválida! Use apenas números.")
            return

        port = int(port_text)
        self.btn_conectar.config(state=tk.DISABLED)

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((host, port))
            self.ativo[0] = True
            enviar_mensagem(self.sock, 1, {"username": self.username})

            threading.Thread(target=self.escutar_servidor, daemon=True).start()
            self.frame_login.pack_forget()
            self.frame_chat.pack(fill="both", expand=True)

        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao conectar: {e}")
        finally:
            self.btn_conectar.config(state=tk.NORMAL)

    # ----------------------- Escuta do servidor -----------------------

    def escutar_servidor(self):
        while self.ativo[0]:
            cmd, payload = receber_mensagem(self.sock)
            if cmd is None:
                self.adicionar_texto("\n❌ Conexão encerrada pelo servidor.\n")
                self.ativo[0] = False
                break

            if cmd == 101:
                self.adicionar_texto(f"\n✅ {payload.get('message', 'Login efetuado com sucesso.')}\n")
            elif cmd == 102:
                autor = payload.get("author", "Anônimo")
                msg = payload.get("message", "")
                self.adicionar_texto(f"[{autor}]: {msg}\n")
            elif cmd == 103:
                self.adicionar_texto("\n📜 Histórico de mensagens:\n")
                for m in payload.get("messages", []):
                    self.adicionar_texto(f"[{m['author']}]: {m['message']}\n")
                self.adicionar_texto("📜 --- Fim do histórico ---\n")

    # ----------------------- Envio e logout -----------------------

    def enviar_msg(self):
        if not self.ativo[0]:
            return
        msg = self.entry_msg.get().strip()
        dest = self.entry_dest.get().strip()
        if not msg:
            return
        conteudo = msg if not dest else f"@{dest}: {msg}"
        enviar_mensagem(self.sock, 2, {"message": conteudo})
        self.entry_msg.delete(0, tk.END)

    def pedir_historico(self):
        if self.ativo[0]:
            enviar_mensagem(self.sock, 3, {})

    def logout(self):
        if self.ativo[0]:
            try:
                enviar_mensagem(self.sock, 4, {})
            except:
                pass
            self.ativo[0] = False
            self.sock.close()
            messagebox.showinfo("Logout", "Você saiu do mural.")
            self.root.destroy()

    # ----------------------- Utilitários -----------------------

    def adicionar_texto(self, texto):
        """Adiciona texto na área de mensagens."""
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, texto)
        self.text_area.yview(tk.END)
        self.text_area.config(state=tk.DISABLED)


# ----------------------- Execução principal -----------------------

if __name__ == "__main__":
    root = tk.Tk()
    app = ClienteMural(root)
    root.mainloop()
