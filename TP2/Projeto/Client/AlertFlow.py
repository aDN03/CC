import subprocess
import datetime
import re
from NMS_AGENT import *
import platform
import psutil

def control_hardware(FREQUENCY, M_CPU, M_RAM, INTERFACES, M_IS, M_PL, M_JI):
    i = 0
    INTERFACES = INTERFACES.split(',')
    while True:
        i += 1
        message = ""
        if int(M_CPU) != 0:
            cpu_usage = psutil.cpu_percent()
            message += f"CPU usage: {cpu_usage}%\n"
            if cpu_usage > int(M_CPU):
                tcp_send(f"ALERT!!!: CPU usage: {cpu_usage}%")

        if int(M_RAM) != 0:
            ram_usage = psutil.virtual_memory().percent
            message += f"RAM usage: {ram_usage}%\n"
            if ram_usage > int(M_RAM):
                tcp_send(f"ALERT!!!: RAM usage: {ram_usage}%")

        if platform.system() == "Darwin":
            cmd = ["ping", "-c", str(FREQUENCY), tcp_host]

        else:
            cmd = ["ping", tcp_host, "-w", str(FREQUENCY)]

        try:
            pings = subprocess.check_output(cmd).decode("utf-8")
            lines = pings.splitlines()

            
            avg = float(lines[-1].split("=")[1].split("/")[1])
            message += f"Jitter: {avg}ms\n"
            if avg > float(M_JI):
                tcp_send(f"ALERT!!!: Jitter is {avg}ms")

            loss = int(re.search(r'\d+(?=%)', lines[-2]).group())
            message += f"Packet loss: {loss}%\n"
            if loss > int(M_PL):
                tcp_send(f"ALERT!!!: Packet loss is {loss}%")
        except subprocess.CalledProcessError as e:
                tcp_send(f"ERROR: Unable to execute ping. Command: {' '.join(cmd)}, Error: {str(e)}")

        if int(M_IS) != 0:
            stats = psutil.net_io_counters(pernic=True)
            for interface in INTERFACES:
                if interface in stats:
                    interface_stats = stats[interface]
                    packets = interface_stats.packets_recv + interface_stats.packets_sent
                    message += f"Packets on {interface}: {packets}\n"
                    if packets > int(M_IS):
                        tcp_send(f"ALERT!!!: Packets in interface '{interface}': {packets}")
                else:
                    message += f"Interface '{interface}' not found.\n"

        if i == 10:
            i = 0
            tcp_send(message)



def calc_ping(pingTo, pingAmount = 1, pingInterval = 1):
    '''
    Função auxiliar para calcular ping do cliente

    Param:
    ----------
    pingTo:
        IP de onde o cliente deve mandar o ping
    ----------
    '''

    cmd = ["ping", pingTo, "-c", str(pingAmount), "-q", "-i", str(pingInterval)]
    ping = subprocess.check_output(cmd).decode("utf-8").split()[-1].split("/")[4] 
    return ping



def calc_bandwidth(ipTo, udp=False, testTime=10):
    """
    Mede a largura de banda usando o iperf.
    
    Parâmetros:
    ----------
    ipTo : str
        Endereço IP ou hostname do destino.
    udp : bool, opcional
        Define se o teste deve ser feito em UDP. Padrão é False (TCP).
    testTime : int, opcional
        Tempo de duração do teste em segundos. Padrão é 10 segundos.
    
    Retorno:
    -------
    float
        Largura de banda medida em Mbits/s.
    """
    cmd = ["iperf", "-c", ipTo, "-t", str(testTime)]
    
    if udp:
        cmd.append("-u")
    
    try:
        result = subprocess.check_output(cmd, stderr=subprocess.STDOUT).decode("utf-8")
        
        for line in result.splitlines():
            if "Mbits/sec" in line:
                bandwidth = float(line.split()[-2])
                return bandwidth
        
        raise ValueError("Não foi possível determinar a largura de banda na saída.")
    
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Erro ao executar iperf: {e.output.decode('utf-8')}")
    except Exception as e:
        raise RuntimeError(f"Erro inesperado: {str(e)}")

    
    


