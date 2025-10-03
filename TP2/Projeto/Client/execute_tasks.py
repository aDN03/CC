import re
import socket
import time
import subprocess
import sys
import NMS_AGENT
import os
import select



def execute_ping(ns, ping_config, udp_socket, host, port):
    """
    Executa o comando ping com base na configuração fornecida e extrai apenas a latência.

    Parâmetros:
    ----------
    ns : int
        Número de sequência do pacote.
    ping_config : str
        Configuração do ping no formato `"{destination}:{packet_count}:{frequency}"`.
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
    print(ping_config)
    destination, packet_count, frequency = ping_config.split(":")
    command = ["ping", "-c", str(packet_count), destination]

    try:
        while True:
            print(f"Calculando Latência para {destination} com {packet_count} pacotes...")
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout

            latencies = re.findall(r"time=(\d+\.\d+) ms", output)
            
            if latencies:
                average_latency = sum(map(float, latencies)) / len(latencies)
                resposta = f"{ns}€Latência média para {destination}: {average_latency:.2f} ms\n"
            else:
                resposta = f"{ns}€Falha ao obter latência para {destination}\n"

            NMS_AGENT.send_via_socket(udp_socket, host, port, resposta)

            time.sleep(int(frequency))

    except KeyboardInterrupt:
        print("Execução do ping interrompida pelo usuário.")
    except Exception as e:
        error_message = f"Erro ao executar o ping: {str(e)}"
        print(error_message)
        NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)


def execute_packet_loss(ns, ping_config, udp_socket, host, port):
    """
    Executa o comando ping com base na configuração fornecida e extrai a taxa de perda de pacotes.

    Parâmetros:
    ----------
    ns : int
        Número de sequência do pacote.
    ping_config : str
        Configuração do ping no formato `"{destination}:{packet_count}:{frequency}"`.
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
    destination, packet_count, frequency = ping_config.split(":")
    command = ["ping", "-c", str(packet_count), destination]

    try:
        while True:
            print(f"Calculando Perda de Pacotes para {destination} com {packet_count} pacotes...")
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout

            match = re.search(r"(\d+)% packet loss", output)
            if match:
                packet_loss = match.group(1)
                resposta = f"{ns}€Perda de pacotes para {destination}: {packet_loss}%\n"
            else:
                resposta = f"{ns}€Falha ao obter perda de pacotes para {destination}\n"

            NMS_AGENT.send_via_socket(udp_socket, host, port, resposta)

            time.sleep(int(frequency))

    except KeyboardInterrupt:
        print("Execução do ping interrompida pelo usuário.")
    except Exception as e:
        error_message = f"Erro ao executar o ping: {str(e)}"
        print(error_message)
        NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)


def execute_jitter(ns, ping_config, udp_socket, host, port):
    """
    Executa o comando ping com base na configuração fornecida e calcula o jitter.

    Parâmetros:
    ----------
    ns : int
        Número de sequência do pacote.
    ping_config : str
        Configuração do ping no formato `"{destination}:{packet_count}:{frequency}"`.
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
    destination, packet_count, frequency = ping_config.split(":")
    command = ["ping", "-c", str(packet_count), destination]

    try:
        while True:
            print(f"Calculando Jitter para {destination} com {packet_count} pacotes...")
            result = subprocess.run(command, capture_output=True, text=True)
            output = result.stdout

            latencies = re.findall(r"time=(\d+\.\d+) ms", output)
            if len(latencies) > 1:
                latencies = list(map(float, latencies))
                
                jitter = sum(abs(latencies[i+1] - latencies[i]) for i in range(len(latencies) - 1)) / (len(latencies) - 1)
                
                resposta = f"{ns}€Jitter para {destination}: {jitter:.2f} ms\n"
            else:
                resposta = f"{ns}€Falha ao calcular jitter para {destination} (dados insuficientes).\n"

            NMS_AGENT.send_via_socket(udp_socket, host, port, resposta)

            time.sleep(int(frequency))

    except KeyboardInterrupt:
        print("Execução do cálculo de jitter interrompida pelo usuário.")
    except Exception as e:
        error_message = f"Erro ao executar o cálculo de jitter: {str(e)}"
        print(error_message)
        NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)

def execute_bandwidth(ns, bandwidthConfig, udp_socket, host, port):
    """
    Calcula a bandwidth através do iperf

    Parâmetros:
    ----------
    ns : int
        Número de sequência do pacote.
    bandwidthConfig : str
        Configuração do iperf no formato `"{mode}:{server_address}:{duration}:{transport_type}:{frequency}"`.
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
    heartbeatTimeout = 5

    heartRate = 1

    syncPort = 27182
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    mode, address, duration, transport_type, frequency = bandwidthConfig.split(":")
    if mode == "server":
        
        
        s.bind('0.0.0.0', syncPort)

        bashline = ["iperf", "-s"]
        if transport_type == "UDP":
            bashline.append("-u")

        try:
            while True:
                received, addr = s.recvfrom(8)

                s.sendto(b"ready", addr)
                child = subprocess.Popen(bashline)

                missedbeats = 0
                heart = ""
                while(missedbeats < heartbeatTimeout and (heart == "done" or heart == "cancel")):

                    if select.select([s], [], [], heartRate)[0]:

                        heart, addr = s.recvfrom(8)
                        heart = heart.decode("utf-8")
                        missedbeats = 0
                    
                    else:
                        missedbeats+=heartRate

                    time.sleep(heartRate)
                    

                child.terminate()
                
                if missedbeats == heartbeatTimeout:
                    error_message = f"{ns}€Conexão perdida com o outro agente"
                    NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)
                
                
                '''
                resposta = f"{ns}€Throughtput calculado de {cliIP}: {value}\n"

                NMS_AGENT.send_via_socket(udp_socket, host, port, resposta)
                '''
                time.sleep(int(frequency))
                


        except KeyboardInterrupt:
            print("Teste interrompido pelo utilizador.")
            s.sendto(b"cancel", addr)
        except Exception as e:
            error_message = f"Erro ao executar o cálculo de throughput: {str(e)}"
            print(error_message)
            NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)
        
    if mode == "client":

        bashline = ["iperf", "-c", address, "-t", str(duration)]
        if(transport_type == "UDP"):
            bashline.append("-u")
        
        otherS = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        otherS.connect(("8.8.8.8", 80))
        ownAddress = otherS.getsockname()[0]

        s.settimeout(30)

        try:
            while True:
                s.sendto(b"wassup", (address, syncPort))
                received = s.recv(8).decode('utf-8')
                if(received == "cancel"):
                    print("Interrompido por utilizador no end point")
                else:
                    result = subprocess.Popen(bashline, stdout=subprocess.PIPE)
                    while result.returncode() == None:
                        s.sendto(b"badum", (address, syncPort))
                        time.sleep(heartRate)
                    
                    s.sendto(b"done", (address, syncPort))
                    result.terminate()
                    result = result.stdout.read().decode('utf-8')
                    
                    
                    matches = re.findall(r"\d+\.\d+ [KMG]?bits/sec", result)
                    if len(matches) < 1:
                        print("Algo correu mal com o iperf.")
                        value = "Inválido"
                    
                    else:
                        value = matches[-1]
                    
                    
                    resposta = f"{ns}€Throughput de {ownAddress} para {address}: {value}\n"
                    NMS_AGENT.send_via_socket(udp_socket, host, port, resposta)

                    time.sleep(int(frequency))





        except KeyboardInterrupt:
            print("Teste interrompido pelo utilizador.")
            s.send(b"cancel")
        except Exception as e:
            error_message = f"Erro ao executar o cálculo de throughput: {str(e)}"
            print(error_message)
            NMS_AGENT.send_via_socket(udp_socket, host, port, error_message)


