import os
import re
import socket
import struct
import NetTask
import time
import threading
import subprocess
import sys
import AlertFlow
import execute_tasks

n_s = 0
MAX_ATTEMPTS = 5 
array_n_s = []  

udp_host = '127.0.0.1'  
udp_port = 65433        

tcp_host = '127.0.0.1' 
tcp_port = 65432       


def send_via_socket(udp_socket, host, port, data):
    """
    Envia uma mensagem via socket UDP.

    Parâmetros:
    ----------
    udp_socket : socket
        Socket UDP para enviar mensagens.
    host : str
        Endereço do servidor.
    port : int
        Porta do servidor.
    data : str
        Dados a serem enviados.

    Retorno:
    -------
    None
    """

    global n_s, array_n_s
    n_s += 1
    message = NetTask.criar_protocolo_udp(n_s, "001", data)
    array_n_s.append([n_s, message, time.time(), 0])
    udp_socket.sendto(message, (host, port))

def set_limits(ns, task, udp_socket, host, port):
    """
    Define os limites de monitoramento para um dispositivo.

    Parâmetros:
    ----------
    ns : int
        Número de sequência do pacote.
    task : str
        Dados da tarefa no formato `"{FREQUENCY}-{CPU}-{M_CPU}-{RAM}-{M_RAM}-{INTERFACES}-{M_IS}-{M_PL}-{M_JI}-{tasks}"`.
    udp_socket : socket
        Socket UDP para enviar mensagens.
    host : str
        Endereço do servidor.
    port : int
        Porta do servidor.

    Retorno:
    -------
    None
    """

    FREQUENCY, = struct.unpack("!I", task[:4])
    M_CPU, = struct.unpack("!f", task[4:8])
    M_RAM, = struct.unpack("!f", task[8:12])
    INTERFACES_LEN, = struct.unpack("!I", task[12:16])
    INTERFACES = task[16:16+INTERFACES_LEN].decode('utf-8')
    M_IS, = struct.unpack("!I", task[16+INTERFACES_LEN:20+INTERFACES_LEN])
    M_PL, = struct.unpack("!f", task[20+INTERFACES_LEN:24+INTERFACES_LEN])
    M_JI, = struct.unpack("!f", task[24+INTERFACES_LEN:28+INTERFACES_LEN])
    LEN_LATENCY, = struct.unpack("!I", task[28+INTERFACES_LEN:32+INTERFACES_LEN])
    latency = task[32+INTERFACES_LEN:32+INTERFACES_LEN+LEN_LATENCY].decode('utf-8')
    LEN_BANDWIDTH, = struct.unpack("!I", task[32+INTERFACES_LEN+LEN_LATENCY:36+INTERFACES_LEN+LEN_LATENCY])
    bandwidth = task[36+INTERFACES_LEN+LEN_LATENCY:36+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH].decode('utf-8')
    LEN_JITTER, = struct.unpack("!I", task[36+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH:40+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH])
    jitter = task[40+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH:40+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH+LEN_JITTER].decode('utf-8')
    LEN_PACKET_LOSS, = struct.unpack("!I", task[40+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH+LEN_JITTER:44+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH+LEN_JITTER])
    packet_loss = task[44+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH+LEN_JITTER:44+INTERFACES_LEN+LEN_LATENCY+LEN_BANDWIDTH+LEN_JITTER+LEN_PACKET_LOSS].decode('utf-8')

    thread = threading.Thread(target=execute_tasks.execute_ping, args=(ns, latency, udp_socket, host, port))
    thread.daemon = True
    thread.start()

    thread = threading.Thread(target=execute_tasks.execute_packet_loss, args=(ns, packet_loss, udp_socket, host, port))
    thread.daemon = True
    thread.start()

    thread = threading.Thread(target=execute_tasks.execute_jitter, args=(ns, jitter, udp_socket, host, port))
    thread.daemon = True
    thread.start()

    thread = threading.Thread(target=execute_tasks.execute_bandwidth, args=(ns, bandwidth, udp_socket, host, port))
    thread.daemon = True
    thread.start()


    thread = threading.Thread(target=AlertFlow.control_hardware, args=(FREQUENCY, M_CPU, M_RAM, INTERFACES, M_IS, M_PL, M_JI))
    thread.daemon = True
    thread.start()



def resend_unacknowledged_packets(udp_socket, host, port):
    """
    Reenvia pacotes que não receberam ACK após 2 segundos.

    Parâmetros:
    ----------
    udp_socket : socket
        Socket UDP para enviar mensagens.
    host : str
        Endereço do servidor.
    port : int
        Porta do servidor.

    Retorno:
    -------
    None
    """

    global array_n_s
    current_time = time.time()

    for packet_info in array_n_s:
        packet_n_s, message, timestamp, attempts = packet_info

        if current_time - timestamp > 2 and attempts < MAX_ATTEMPTS:
            udp_socket.sendto(message, (host, port))
            
            packet_info[2] = current_time
            packet_info[3] += 1

        if attempts >= MAX_ATTEMPTS:
            n_s, opcao, dados = NetTask.interpretar_protocolo_udp(message)
            if opcao == 0: 
                print("Conexão não estabelecida. Programa Encerrado")
                os._exit(0)
            elif opcao == 5: 
                print("Conexão perdida. Programa Encerrado")
                os._exit(0)
            print(f"Pacote {packet_n_s} não recebeu confirmação após {MAX_ATTEMPTS} tentativas. Removendo.")
            array_n_s.remove(packet_info)


def send_keep_alive(udp_socket, host, port):
    """
    Envia um pacote de keep-alive para manter a conexão ativa.

    Parâmetros:
    ----------
    udp_socket : socket
        Socket UDP para enviar mensagens.
    host : str
        Endereço do servidor.
    port : int
        Porta do servidor.

    Retorno:
    -------
    None
    """

    global n_s
    n_s += 1
    message = NetTask.criar_protocolo_udp(n_s, "101", "")

    array_n_s.append([n_s, message, time.time(), 0]) 

    if len(array_n_s) > 10:
        array_n_s.pop(0)

    udp_socket.sendto(message, (host, port))


def monitor_user_input(terminate_event):
    """
    Monitora a entrada do usuário para sair do programa.

    Parâmetros:
    ----------
    terminate_event : threading.Event
        Evento para encerrar o programa.
    
    Retorno:
    -------
    None
    """

    user_input = ""
    while user_input.lower() != "q":
        user_input = input("Digite 'q' para sair: ")
    terminate_event.set() 



def udp_client():
    """
    Inicia o cliente NMS com comunicação UDP e TCP.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    global n_s, array_n_s, udp_host, udp_port

    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    n_s += 1 
    message = NetTask.criar_protocolo_udp(n_s, "000", "") 
    array_n_s.append([n_s, message, time.time(), 0])
    udp_socket.sendto(message, (udp_host, udp_port))
    last_keep_alive_time = time.time()

    print("NMS_CLIENT Iniciado (UDP e TCP)")

    terminate_event = threading.Event()
    
    input_thread = threading.Thread(target=monitor_user_input, args=(terminate_event,))
    input_thread.start()

    while not terminate_event.is_set():
        current_time = time.time()

        if current_time - last_keep_alive_time >= 5:
            send_keep_alive(udp_socket, udp_host, udp_port)
            last_keep_alive_time = current_time

        resend_unacknowledged_packets(udp_socket, udp_host, udp_port)
        udp_socket.settimeout(0.5)

        try:
            while True:
                data = b''
                chunk, addr = udp_socket.recvfrom(1024) 
                data += chunk

                if b'\0' in data:
                    break

            n_s_response, opcao, dados = NetTask.interpretar_protocolo_udp(data)

            if opcao == 4:
                for packet_info in array_n_s:
                    if packet_info[0] == int(n_s_response):
                        array_n_s.remove(packet_info)
                        break

            elif opcao == 2:
                response = NetTask.criar_protocolo_udp(int(n_s_response), "100", "")
                udp_socket.sendto(response, (udp_host, udp_port))
                set_limits(n_s, dados, udp_socket, udp_host, udp_port)           

        except socket.timeout:
            continue
    
    response = NetTask.criar_protocolo_udp(n_s, "111", "")
    udp_socket.sendto(response, (udp_host, udp_port))

    data = b''
    while True:
        chunk, addr = udp_socket.recvfrom(1024)
        data += chunk

        if b'\0' in data:
            break

        n_s_response, opcao, dados = NetTask.interpretar_protocolo_udp(data)
    
    if opcao == 4 and int(n_s_response) == n_s:
        print("Conexão UDP encerrada com sucesso.")
    else:
        print("Erro ao encerrar conexão UDP.")

    udp_socket.close()
    terminate_event.set()



def tcp_send(message):
    """
    Gerencia a comunicação TCP com o servidor, enviando uma mensagem especificada.

    Parâmetros:
    ----------
    message : str
        A mensagem a ser enviada ao servidor.
    """
    
    global tcp_host, tcp_port

    try:
        with socket.create_connection((tcp_host, tcp_port)) as tcp_socket:
                tcp_socket.sendall(message.encode())

    except Exception as e:
        print(f"Erro na comunicação TCP: {e}")



if __name__ == "__main__":
    """
    Função principal do cliente NMS.

    Parâmetros:
    ----------
    None

    Retorno:
    -------
    None
    """

    udp_client()
