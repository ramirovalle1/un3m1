# -*- coding: latin-1 -*-
import xml.etree.ElementTree as ET
from settings import DEBUG
from zeep import Client


def TestConnection(user, password):
    if DEBUG:
        client = Client('http://127.0.0.1:8000/soap/bp/cobro?wsdl')
    else:
        client = Client('https://sga.unemi.edu.ec/soap/bp/cobro?wsdl')
    # response = client.service.testConnection('bancopacifico', 'M@de171020**')
    xml_string = f"<trama><User>{user}</User><Password>{password}</Password></trama>"
    response = client.service.testConnection(xml_string)
    data = {}
    TestResponse = ET.ElementTree(ET.fromstring(response.strip())).getroot()
    CodigoRespuesta = TestResponse.find('CodigoRespuesta')
    data['CodigoRespuesta'] = '0047'
    if not CodigoRespuesta is None:
        data['CodigoRespuesta'] = CodigoRespuesta.text
    MensajeRespuesta = TestResponse.find('MensajeRespuesta')
    data['MensajeRespuesta'] = ''
    if not MensajeRespuesta is None:
        data['MensajeRespuesta'] = MensajeRespuesta.text
    Ambiente = TestResponse.find('Ambiente')
    data['Ambiente'] = 'SIN DEFINIR'
    if not Ambiente is None:
        data['Ambiente'] = Ambiente.text
    # for res in response:
    #     data[res.tag] = res.text
    return data

