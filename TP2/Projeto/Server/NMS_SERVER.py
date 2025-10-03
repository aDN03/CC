import socket
import os
import time
import threading
import json
from datetime import datetime, timedelta
import NetTask
import struct

MAX_ATTEMPTS = 3  
RETRY_TIMEOUT = 2
INACTIVITY_LIMIT = 15
CHECK_INACTIVE_INTERVAL = 10

tasks = []
array_n_s = []
tasks_n_s = []

tcp_host = '127.0.0.1'
tcp_port = 65432

udp_host = '127.0.0.1'
udp_port = 65433

def listar_arquivos_monitorizacao(diretorio):
    """
    Lista os arquivos de monitorização no diretório especificado e permite visualizar o conteúdo de cada arquivo.

    Parâmetros:
    ----------
    diretorio : str
        O diretório onde os arquivos de monitorização estão localizados.

    Retorno:
    -------
    list
        Uma lista de strings contendo os nomes dos arquivos de monitorização no diretório especificado.
    """

    arquivos_monitorizacao = []
    
    if not os.path.isdir(diretorio):
        print("Diretório inválido.")
        return []
    
    for arquivo in os.listdir(diretorio):
        if arquivo.startswith("monitorizacao-"):
            arquivos_monitorizacao.append(arquivo)
    
    print("\n--- Arquivos de Monitorização ---")
    print("-------------------------")
    print("| Número |    Arquivo   |")
    print("-------------------------")
    i = 0
    for arquivo in arquivos_monitorizacao:
        i += 1
        print(f"|   {i}    | {arquivo} |")
        print("-------------------------")
    
    opcao = input("\nDigite 'q' para sair ou selecione um arquivo para visualizar: ")
    while(opcao != "q"):
        if opcao.isdigit() and int(opcao)-1 < len(arquivos_monitorizacao):
            print("\n\n\n")
            print("\n-----------------------------------------------------")
            print(f"\nConteúdo do arquivo '{arquivos_monitorizacao[int(opcao)-1]}':\n")
            with open(arquivos_monitorizacao[int(opcao)-1], "r") as file:
                print(file.read())
            print("\n-----------------------------------------------------")
            print("\n\n\n")
            opcao = input("Digite 'q' para sair ou selecione outro arquivo.")
            
        else:
            opcao = input("Opção inválida. Tente novamente.")

def listar_arquivos_task(diretorio):
    """
    Lista os arquivos task no diretório especificado e permite visualizar o conteúdo de cada arquivo.

    Parâmetros:
    ----------
    diretorio : str
        O diretório onde os arquivos task estão localizados.

    Retorno:
    -------
    list
        Uma lista de strings contendo os nomes dos arquivos task no diretório especificado.
    """

    arquivos_task = []
    
    if not os.path.isdir(diretorio):
        print("Diretório inválido.")
        return []
    
    for arquivo in os.listdir(diretorio):
        if arquivo.startswith("task-"):
            arquivos_task.append(arquivo)
    
    print("\n--- Arquivos Task ---")
    print("-------------------------")
    print("| Número |    Arquivo   |")
    print("-------------------------")
    i = 0
    for arquivo in arquivos_task:
        i += 1
        print(f"|   {i}    | {arquivo} |")
        print("-------------------------")
    
    opcao = input("\nDigite 'q' para sair ou selecione um arquivo para visualizar: ")
    while(opcao != "q"):
        if opcao.isdigit() and int(opcao)-1 < len(arquivos_task):
            print("\n\n\n")
            print("\n-----------------------------------------------------")
            print(f"\nConteúdo do arquivo '{arquivos_task[int(opcao)-1]}':\n")
            with open(arquivos_task[int(opcao)-1], "r") as file:
                print(file.read())
            print("\n-----------------------------------------------------")
            print("\n\n\n")
            opcao = input("Digite 'q' para sair ou selecione outro arquivo.")
            
        else:
            opcao = input("Opção inválida. Tente novamente.")

    

def resend_unacknowledged_packets(udp_socket, host, port):
    """
    Reenvia pacotes não confirmados após um determinado tempo.

    Parâmetros:
    ----------
    udp_socket : socket
        O socket UDP.
    host : str
        O endereço IP do host.
    port : int
        A porta do host.

    Retorno:
    -------
    None
    """

    global array_n_s
    current_time = time.time()

    for packet_info in array_n_s[:]: 
        packet_n_s, message, timestamp, attempts, addr = packet_info

        if current_time - timestamp > RETRY_TIMEOUT and attempts < MAX_ATTEMPTS:
            print(f"Reenviando pacote: n_s = {packet_n_s}, tentativa {attempts + 1}.")
            udp_socket.sendto(message, addr)
            
            packet_info[2] = current_time
            packet_info[3] += 1

        
        if attempts >= MAX_ATTEMPTS:
            print(f"Pacote {packet_n_s} não recebeu confirmação após {MAX_ATTEMPTS} tentativas. Removendo.")
            array_n_s.remove(packet_info)



def start_tcp_server():
    """
    Inicia o servidor TCP e aguarda por conexões de clientes.
    
    Parâmetros:
    ----------
    None
    
    Retorno:
    -------
    None
    """

    global tcp_host
    global tcp_port
    

    tcp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp_server_socket.bind((tcp_host, tcp_port))
    tcp_server_socket.listen()

    print(f"Servidor TCP escutando em {tcp_host}:{tcp_port}...")

    while True:
        conn, addr = tcp_server_socket.accept()
        handle_tcp_client(conn, addr)



def handle_tcp_client(conn, addr):
    """
    Manipula a conexão de um cliente TCP.

    Parâmetros:
    ----------
    conn : socket
        O socket da conexão do cliente.

    Retorno:
    -------
    None
    """

    while True:
        data = conn.recv(1024)
        if not data:
            break
        with open (f"monitorizacao-{addr[0]}.txt", "a") as file:
            file.write("-------------------------\n") 
            file.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + data.decode() + "\n\n")

    conn.close()



def start_udp_server():
    """
    Inicia o servidor UDP e aguarda por mensagens de clientes.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    global udp_host
    global udp_port
    global tasks

    udp_server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_server_socket.bind((udp_host, udp_port))

    print(f"Servidor UDP escutando em {udp_host}:{udp_port}...")
    tasks = NetTask.preparar_tasks("configuration_server.json")

    while True:
        global array_n_s
        global tasks_n_s

        resend_unacknowledged_packets(udp_server_socket, udp_host, udp_port)

        data = b''
        while True:
            chunk, addr = udp_server_socket.recvfrom(1024)
            data += chunk

            if b'\0' in data:
                break

        n_s, opcao, dados = NetTask.interpretar_protocolo_udp(data)

        if opcao == 0:
            with open("connections.txt", "a") as file:
                connection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                file.write(f"{addr[0]}|{addr[1]}|{connection_time}\n")

            response = NetTask.criar_protocolo_udp(n_s, "100", "Ok")
            udp_server_socket.sendto(response, addr)

            
            for task in tasks:
                ip, task_id, dados = task.split(";")
                if ip == addr[0]:
                    tasks_n_s.append((n_s, task_id))
                    response = NetTask.criar_protocolo_udp(n_s, "010", dados)
                    udp_server_socket.sendto(response, addr)
                    array_n_s.append([n_s, response, time.time(), 0, addr])

        elif opcao == 5:
            update_connection_time(addr[0], addr[1])
            response = NetTask.criar_protocolo_udp(n_s, "100", "Keep Alive OK")
            udp_server_socket.sendto(response, addr)

        elif opcao == 4:
            for packet_info in array_n_s:
                if packet_info[0] == int(n_s):
                    array_n_s.remove(packet_info)
                    break
            
        elif opcao == 1:
            resposta = NetTask.criar_protocolo_udp(n_s, "100", "")
            udp_server_socket.sendto(resposta, addr)
            task_id = None
            ns, data = dados.decode().split("€")

            
            for task in tasks_n_s:
                if task[0] == int(ns):
                    task_id = task[1]
                    break
            
            if task_id is not None:
                filename = f"{task_id}.txt" 

                with open(filename, 'a') as file:
                    file.write("-----------------------------------------------------\n")
                    file.write(time.strftime("%Y-%m-%d %H:%M:%S") + "\n" + data + "\n")


            else:
                print("task_id não encontrado.")

        elif opcao == 7:
            with open("connections.txt", "r") as file:
                lines = file.readlines()

            with open("connections.txt", "w") as file:
                for line in lines:
                    conn_ip, conn_port, _ = line.strip().split("|")
                    if conn_ip != addr[0] or conn_port != str(addr[1]):
                        file.write(line)

            response = NetTask.criar_protocolo_udp(n_s, "100", "Conexão encerrada.")
            udp_server_socket.sendto(response, addr)            
            
        if len(array_n_s) > 10:
            array_n_s.pop(0)
       




def update_connection_time(ip, port):
    """
    Atualiza o horário da última conexão ativa de um cliente.

    Parâmetros:
    ----------
    ip : str
        O endereço IP do cliente.
    port : int
        A porta do cliente.

    Retorno:
    -------
    None
    """

    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    updated = False

    with open("connections.txt", "r") as file:
        lines = file.readlines()

    with open("connections.txt", "w") as file:
        for line in lines:
            conn_ip, conn_port, _ = line.strip().split("|")
            if conn_ip == ip and conn_port == str(port):
                file.write(f"{ip}|{port}|{current_time}\n")
                updated = True
            else:
                file.write(line)


def remove_inactive_connections():
    """
    Remove conexões inativas por mais de 15 segundos.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    while True:
        time.sleep(CHECK_INACTIVE_INTERVAL)

        current_time = datetime.now()
        with open("connections.txt", "r") as file:
            lines = file.readlines()

        with open("connections.txt", "w") as file:
            for line in lines:
                ip, port, connection_time_str = line.strip().split("|")
                connection_time = datetime.strptime(connection_time_str, "%Y-%m-%d %H:%M:%S")

                if current_time - connection_time <= timedelta(seconds=INACTIVITY_LIMIT):
                    file.write(line)



def view_connections():
    """
    Exibe a lista de conexões ativas.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    print("\n--- Lista de Conexões ---")

    if os.path.exists("connections.txt"):
        with open("connections.txt", "r") as file:
            i = 1
            print("-------------------------------------------------------")
            print(f"| Número ||    IP     || Porta ||   Hora de Conexão   |")
            print("-------------------------------------------------------")
            for line in file:
                ip, port, connection_time = line.strip().split("|")
                print(f"|   {i}    || {ip} || {port} || {connection_time} |")
                print("-------------------------------------------------------")
                i += 1
    else:
        print("O arquivo 'connections.txt' não existe.")



def main():
    """
    Função principal do programa que exibe um menu de opções.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    while True:
        print("""
        ⢀⣤⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣶⣤⡀
        ⢸⣿⣿⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⠛⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⢀⣀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⠀⠀⣠⣦⡀⠀⠀⢀⣿⡟⠀⢀⣴⣄⠀⠀⠀⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⣠⣾⡿⠋⠀⠀⠀⢸⣿⠇⠀⠀⠙⢿⣷⣄⠀⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠘⢿⣿⣄⠀⠀⠀⢀⣿⡟⠀⠀⠀⠀⣠⣿⡿⠃⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⠀⠙⢿⣷⠄⠀⢸⣿⠇⠀⠀⠠⣾⡿⠋⠀⠀⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⠀⠀⠀⠁⠀⠀⠿⠟⠀⠀⠀⠀⠈⠀⠀⠀⠀⠀⠀⣿⣿⡇
        ⢸⣿⣿⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⠀⣿⣿⡇
        ⠸⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⣿⠇
        ⠀⠈⠉⠉⠉⠉⠉⠉⠉⠉⠉⢹⣿⣿⣿⣿⡏⠉⠉⠉⠉⠉⠉⠉⠉⠉⠁⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⣤⣤⣼⣿⣿⣿⣿⣧⣤⣤⠀⠀⠀⠀⠀⠀⠀⠀⠀
        ⠀⠀⠀⠀⠀⠀⠀⠀⠀⠿⠿⠿⠿⠿⠿⠿⠿⠿⠿⠀⠀⠀⠀⠀⠀⠀⠀⠀
        """)
        print("""
                === Menu ===
            1. Ver Lista de Conexões
            2. Ver Tasks recebidas
            3. Ver Monitoramento de Hardware
            4. Sair
        """)
        
        choice = input("Escolha uma opção (1, 2, 3, 4): ")
        
        if choice == '1':
            view_connections()
        elif choice == '2':
            listar_arquivos_task(os.getcwd())
        elif choice == '3':
            listar_arquivos_monitorizacao(os.getcwd())
        elif choice == '4':
            print("Saindo...")
            break
        else:
            print("Opção inválida! Tente novamente.")


if __name__ == "__main__":
    """
    Função principal do programa que inicia os servidores TCP e UDP em threads separadas e executa a função principal do menu.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    tcp_thread = threading.Thread(target=start_tcp_server, daemon=True)
    tcp_thread.start()

    udp_thread = threading.Thread(target=start_udp_server, daemon=True)
    udp_thread.start()

    cleanup_thread = threading.Thread(target=remove_inactive_connections, daemon=True)
    cleanup_thread.start()

    main()
