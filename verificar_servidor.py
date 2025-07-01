import os
import socket
import requests
import psutil
import multiprocessing
import platform


def to_gb(bytes):
    return bytes / 1024 ** 3

def verificar_servidor(idcod):
    # CPUFRECUENCIA
    cpu_frequency = psutil.cpu_freq()

    # TIEMPODEVIDAMAQUINA
    with open("/proc/uptime", "r") as f:
        uptime = f.read().split(" ")[0].strip()

    # NUMPROCESOS EJECUTANDOSE
    pids = []
    for subdir in os.listdir('/proc'):
        if subdir.isdigit():
            pids.append(subdir)

    disk_usage = psutil.disk_usage("/")
    disk_usage_storage = psutil.disk_usage("/mnt/nfs/home/storage/")
    URLCONSUMO = f'https://deva.unemi.edu.ec/webhook/'
    data = {}
    data['idcod'] = idcod
    data['cpuporcentaje'] = psutil.cpu_percent(4)
    data['ramporcentaje'] = psutil.virtual_memory()[2]
    data['discoporcentaje'] = disk_usage.percent
    data['storageporcentaje'] = disk_usage_storage.percent
    data['ramtotal'] = to_gb(psutil.virtual_memory().total)
    data['ramusada'] = to_gb(psutil.virtual_memory().used)
    data['ramlibre'] = to_gb(psutil.virtual_memory().free)
    data['ramcached'] = to_gb(psutil.virtual_memory().cached)
    data['ramshared'] = to_gb(psutil.virtual_memory().shared)
    data['ramactive'] = to_gb(psutil.virtual_memory().active)
    data['discototal'] = to_gb(disk_usage.total)
    data['discousada'] = to_gb(disk_usage.used)
    data['discolibre'] = to_gb(disk_usage.free)
    data['storagetotal'] = to_gb(disk_usage_storage.total)
    data['storageusada'] = to_gb(disk_usage_storage.used)
    data['storagelibre'] = to_gb(disk_usage_storage.free)
    data['nombre_equipo'] = socket.gethostname()
    data['direccion_equipo'] = socket.gethostbyname(data['nombre_equipo'])
    data['plataforma'] = platform.platform()
    data['tiempo_vida'] = tiempo_vida_ = int(float(uptime))
    data['tiempo_horas'] = tiempo_vida_ // 3600
    data['tiempo_minuto'] = (tiempo_vida_ % 3600) // 60
    data['numprocesosejecutados'] = len(pids)
    # DATA CORES CPU
    data['cpunucleosfisicos'] = psutil.cpu_count(logical=False)
    data['cpunucleostotales'] = psutil.cpu_count(logical=True)
    data['cpumaxfrecuencia'] = cpu_frequency.max
    data['cpuminfrecuencia'] = cpu_frequency.min
    data['cputipofrecuencia'] = 'Mhz'
    cpuporcentajecores = [] #PORCENTAJE DE USO DE LOS CRES
    for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
        cpuporcentajecores.append(percentage)
    data['cpuporcentajecores'] = cpuporcentajecores
    data['cpuporcentajetotal'] = psutil.cpu_percent()
    resp = requests.post(URLCONSUMO, data=data).json()
    if resp['result']:
        return True
    else:
        return False

verificar_servidor(1)

# 2	ADMISION	admision-instance-group
# 3	POSGRADO	postgrado-instance-group
# 4	PREGRADO	pregrado-instance-group
# 1	SISTEMA DE GESTION ACADEMICO	sga-instance-group
