# -*- coding: latin-1 -*-
from __future__ import unicode_literals
import os
import logging
from datetime import datetime
from soap.models import Setting
from settings import SITE_STORAGE, SITE_ROOT
from django.core.exceptions import ObjectDoesNotExist

LOGGING_LEVEL_DEBUG = 0
LOGGING_LEVEL_INFO = 1
LOGGING_LEVEL_WARNING = 2
LOGGING_LEVEL_ERROR = 3
LOGGING_FILE_WEBSERVICE = 1
LOGGING_FILE_PROCESADO = 2
LOGGING_BANCO_PACIFICO = 1
LOGGING_WESTERN_UNION = 2
SERVICE_BANCO_PACIFICO_PK = 1
SERVICE_WESTERN_UNION_PK = 2


def get_setting_soap(tipo, service_id):
    # if Setting.objects.values("id").filter(tipo=tipo, pk=service_id, status=True, activo=True).exists():
    #     return Setting.objects.filter(tipo=tipo,  pk=service_id, status=True, activo=True)[0]
    # return None
    try:
        return Setting.objects.get(tipo=tipo,  pk=service_id, status=True, activo=True)
    except ObjectDoesNotExist:
        return None


def create_storage_logging(entidad, file):
    hoy = datetime.now().date()
    logging_entidad = 'desconocido'
    if entidad == LOGGING_BANCO_PACIFICO:
        logging_entidad = 'bancopacifico'
    elif entidad == LOGGING_WESTERN_UNION:
        logging_entidad = 'westernunion'
    logging_file = 'desconocido'
    if file == LOGGING_FILE_WEBSERVICE:
        logging_file = 'webservice'
    elif file == LOGGING_FILE_PROCESADO:
        logging_file = 'procesado'

    output_folder = os.path.join(SITE_STORAGE, 'media', 'wsdl', 'soap', logging_entidad, logging_file, str(hoy.year), str(hoy.month))
    os.makedirs(output_folder, mode=0o777, exist_ok=True)
    return output_folder


def set_logging(entidad, level, file, msg):
    storage = create_storage_logging(entidad, file)

    logging.config.fileConfig(os.path.join(SITE_ROOT, 'soap', 'logging.conf'))
    logger = logging.getLogger('MainLogger')
    fh = logging.FileHandler(os.path.join(storage, '{:%d}.log'.format(datetime.now())))
    formatter = logging.Formatter('%(asctime)s | %(levelname)-8s | %(lineno)04d | %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    if level == LOGGING_LEVEL_DEBUG:
        logger.debug(msg=msg)
    elif level == LOGGING_LEVEL_INFO:
        logger.info(msg=msg)
    elif level == LOGGING_LEVEL_WARNING:
        logger.warning(msg=msg)
    elif level == LOGGING_LEVEL_ERROR:
        logger.error(msg=msg)


def get_value_data_senescyt(data, campo):
    columnas = data['columnas']
    value = None
    for col in columnas:
        if col['columna']['campo'] == campo:
            value = col['columna']['valor']
    return value


def pull_niveltitulacion_senescyt(data):
    from sga.models import NivelTitulacion
    nombre = get_value_data_senescyt(data, 'nivel')
    if nombre is None:
        return None
    if nombre in ['TECNICO_SUPERIOR', 'Técnico Superior', 'Tercer Nivel Técnico Superior']:
        return NivelTitulacion.objects.get(pk=2)
    if nombre in ['TERCER_NIVEL', 'Tercer Nivel o Pregrado', 'Tercer Nivel', 'Pregrado']:
        return NivelTitulacion.objects.get(pk=3)
    if nombre in ['CUARTO_NIVEL', 'Cuarto Nivel o Posgrado', 'Cuarto Nivel', 'Posgrado']:
        return NivelTitulacion.objects.get(pk=4)
    eNivelTitulaciones = NivelTitulacion.objects.filter(nombre__icontains=nombre, nivel__in=[3, 4, 5])
    if not eNivelTitulaciones.values("id").exists():
        return None
    return eNivelTitulaciones.first()


def pull_areatitulo_senescyt(data):
    from sga.models import AreaTituloSenescyt
    area = get_value_data_senescyt(data, 'area')
    areaCodigo = get_value_data_senescyt(data, 'areaCodigo')
    if not area is None:
        eAreaTituloSenescyts = AreaTituloSenescyt.objects.filter(nombre=area)
        if not eAreaTituloSenescyts.values("id").exists():
            eAreaTituloSenescyt = AreaTituloSenescyt(nombre=area,
                                                     codigo=areaCodigo)
            eAreaTituloSenescyt.save()
        else:
            eAreaTituloSenescyt = eAreaTituloSenescyts.first()
        return eAreaTituloSenescyt
    return None


def pull_subareatitulo_senescyt(data):
    from sga.models import SubareaTituloSenescyt
    subarea = get_value_data_senescyt(data, 'subarea')
    subareaCodigo = get_value_data_senescyt(data, 'subareaCodigo')
    if not subarea is None:
        eSubareaTituloSenescyts = SubareaTituloSenescyt.objects.filter(nombre=subarea)
        if not eSubareaTituloSenescyts.values("id").exists():
            eSubareaTituloSenescyt = SubareaTituloSenescyt(nombre=subarea,
                                                           codigo=subareaCodigo)
            eSubareaTituloSenescyt.save()
        else:
            eSubareaTituloSenescyt = eSubareaTituloSenescyts.first()
        return eSubareaTituloSenescyt
    return None


def pull_titulo_senescyt(data, ePersona):
    from sga.models import Titulo
    eNivelTitulacion = pull_niveltitulacion_senescyt(data)
    nombreTitulo = get_value_data_senescyt(data, 'nombreTitulo')
    eTitulo = None
    if not nombreTitulo is None:
        eTitulos = Titulo.objects.filter(nombre=nombreTitulo)
        if not eTitulos.values("id").exists():
            eTitulo = Titulo(nombre=nombreTitulo,
                             nivel=eNivelTitulacion,
                             senescyt=True)
            eTitulo.save(usuario_id=ePersona.usuario_id)
        else:
            eTitulo = eTitulos.first()
            if not eTitulo.senescyt:
                eTitulo.nivel = eNivelTitulacion
                eTitulo.senescyt = True
                eTitulo.save(usuario_id=ePersona.usuario_id)
    return eTitulo


def titulacion_senescyt(data, ePersona):
    from sga.models import Titulacion
    eAreaTituloSenescyt = pull_areatitulo_senescyt(data)
    eSubareaTituloSenescyt = pull_subareatitulo_senescyt(data)
    fechaGrado = get_value_data_senescyt(data, 'fechaGrado')
    fechaRegistro = get_value_data_senescyt(data, 'fechaRegistro')
    numeroRegistro = get_value_data_senescyt(data, 'numeroRegistro')
    ies = get_value_data_senescyt(data, 'ies')
    tipoTitulo = get_value_data_senescyt(data, 'tipoTitulo')
    eTitulo = pull_titulo_senescyt(data, ePersona)
    eTitulaciones = Titulacion.objects.filter(persona=ePersona, titulo=eTitulo)
    if eTitulaciones.values("id").exists():
        for eTitulacion in eTitulaciones:
            eTitulacion



