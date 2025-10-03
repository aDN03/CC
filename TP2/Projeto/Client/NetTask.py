import json
import struct

def criar_protocolo_udp(n_s, opcao, dados):
    """
    Cria uma mensagem de protocolo para uma conexão UDP.

    Parâmetros:
    ----------
    n_s : int
        O número de sequência da mensagem, usado para identificar a ordem das mensagens.
    opcao : str
        O código ou a identificação da operação a ser realizada (ex: "GET", "POST", etc.).
    dados : str
        Os dados ou informações a serem transmitidos na mensagem.

    Retorno:
    -------
    str
        A mensagem formatada no padrão `"{n_s}|{opcao}|{dados}"`
    """

    if (opcao == "000" or opcao == "101" or opcao == "100" or opcao == "111"):
    
        opcao_inteiro = int(opcao, 2)
        protocolo = struct.pack('!IB', n_s, opcao_inteiro)
        protocolo += b'\0'
    
    elif opcao == "010":
        opcao_inteiro = int(opcao, 2)
        
        FREQUENCY, M_CPU, M_RAM, INTERFACES, M_IS, M_PL, M_JI, tasks = dados.split("-")
        
        latency, bandwidth, jitter, packet_loss = tasks.split("?")
        
        FREQUENCY = int(FREQUENCY)  
        M_CPU = float(M_CPU)        
        M_RAM = float(M_RAM)        
        M_IS = int(M_IS)            
        M_PL = float(M_PL)          
        M_JI = float(M_JI)          
        
        INTERFACES = INTERFACES.strip("[]").replace("'", "").replace(" ", "")

        interfaces_len = len(INTERFACES)
    
        protocolo = struct.pack("!IBI", n_s, opcao_inteiro, FREQUENCY)
        protocolo += struct.pack("!f", M_CPU)
        protocolo += struct.pack("!f", M_RAM)
        
        
        protocolo += struct.pack("!I", interfaces_len)
        
        protocolo += INTERFACES.encode('utf-8')
        
        protocolo += struct.pack("!I", M_IS)
        protocolo += struct.pack("!f", M_PL)
        protocolo += struct.pack("!f", M_JI)


        protocolo += struct.pack("!I", len(latency))
        protocolo += latency.encode('utf-8')
        protocolo += struct.pack("!I", len(bandwidth))
        protocolo += bandwidth.encode('utf-8')
        protocolo += struct.pack("!I", len(jitter))
        protocolo += jitter.encode('utf-8')
        protocolo += struct.pack("!I", len(packet_loss))
        protocolo += packet_loss.encode('utf-8')

        protocolo += b'\0'

    elif opcao == "001":
        opcao_inteiro = int(opcao, 2)
        protocolo = struct.pack('!IB', n_s, opcao_inteiro)
        protocolo += dados.encode('utf-8')
        protocolo += b'\0'

    return protocolo


def interpretar_protocolo_udp(mensagem):
    """
    Interpreta uma mensagem de protocolo recebida em uma conexão UDP.

    Parâmetros:
    ----------
    mensagem : str
        A mensagem recebida.

    Retorno:
    -------
    tuple
        Uma tupla contendo o número de sequência, a opção e os dados da mensagem.
    """
    
    n_s, = struct.unpack("!I", mensagem[:4])
    opcao, = struct.unpack("!B", mensagem[4:5])
    dados = mensagem[5:]
    return n_s, opcao, dados


def preparar_tasks(json_file_path):
    """
    Prepara os dados de tarefas de monitoramento para serem enviados ao servidor.

    Parâmetros:
    ----------
    json_file_path : str

    Retorno:
    -------
    list
        Uma lista de strings contendo os protocolos de tarefas de monitoramento.
    """
    
    with open(json_file_path, 'r') as file:
        tasks_data = json.load(file)

    protocols = []
    
    for task in tasks_data["tasks"]:
        task_id = task["task_id"]
        frequency = task["frequency"]
        
        for device in task["devices"]:
            device_id = device["device_id"]
            device_metrics = device["device_metrics"]
            link_metrics = device["link_metrics"]
            bandwidth = link_metrics["bandwidth"]["iperf"]
            jitter = link_metrics["jitter"]["ping"]
            packet_loss = link_metrics["packet_loss"]["ping"]
            latency = link_metrics["latency"]["ping"]
            alertflow_conditions = link_metrics["alertflow_conditions"]

            device_protocol = f"{device_id};{task_id};{frequency}-"
            
            if device_metrics["cpu_usage"]:
                device_protocol += f"{alertflow_conditions['cpu_usage']}-"
            else:
                device_protocol += "0-"
            
            if device_metrics["ram_usage"]:
                device_protocol += f"{alertflow_conditions['ram_usage']}-"
            else:
                device_protocol += "0-"

            device_protocol += f"{device_metrics['interface_stats']}-"
            device_protocol += f"{alertflow_conditions['interface_stats']}-"
            device_protocol += f"{alertflow_conditions['packet_loss']}-"
            device_protocol += f"{alertflow_conditions['jitter']}-"
            device_protocol += f"{latency['destination']}:{latency['packet_count']}:{latency['frequency']}?"
            device_protocol += f"{bandwidth['mode']}:{bandwidth['server_address']}:{bandwidth['duration']}:{bandwidth['transport_type']}:{bandwidth['frequency']}?"
            device_protocol += f"{jitter['destination']}:{jitter['packet_count']}:{jitter['frequency']}?"
            device_protocol += f"{packet_loss['destination']}:{packet_loss['packet_count']}:{packet_loss['frequency']}"

            
            protocols.append(device_protocol)

    return protocols


