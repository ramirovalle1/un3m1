# -*- coding: latin-1 -*-
# from settings import DEBUG
from requests.auth import HTTPBasicAuth
from requests import Session
from zeep import Client
from zeep.transports import Transport


"""
VER OBJECTOS Y FUNCIONES

python -mzeep https://interoperabilidad.dinardap.gob.ec/interoperador-v2?wsdl

"""


def clientSoap():
    try:
        USERNAME = 'UneMIntErOp'
        PASSWORD = 'Q&S-ud1L&%C4Zb'
        session = Session()
        session.auth = HTTPBasicAuth(USERNAME, PASSWORD)
        client = Client('https://interoperabilidad.dinardap.gob.ec/interoperador-v2?wsdl', transport=Transport(session=session))
        return client
    except ConnectionError as ex:
        return None