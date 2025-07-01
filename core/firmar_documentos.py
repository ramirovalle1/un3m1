# *-* coding: utf-8 *-*
import datetime
import io
import os
import sys
import base64
import PyPDF2
import fitz.utils

from cryptography.hazmat import backends
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.serialization import pkcs12
from django.contrib import messages
from endesive.pdf import cms
from PIL import Image
import random
import pyqrcode
from endesive.signer import cert2asn
from pdf2image import convert_from_bytes

from settings import SITE_STORAGE, SITE_POPPLER, MEDIA_URL, MEDIA_ROOT, DEBUG
from sga.funciones import remover_caracteres_especiales_unicode, remover_caracteres_tildes_unicode, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado_generico, conviert_html_to_pdf
from sga.models import Persona, unicode
from django.core.files.storage import default_storage

URL_VALIDADOR='https://ws.firmadigital.gob.ec'


def obtener_posicion_x_y_saltolinea(urlpdf, palabras, ultima_pagina=True, exacta=False, horizontal=False):
    # COORDENADAS QUE SE OBTIENE ES X Y SUPERIOR IZQUIERDO
    pdf = SITE_STORAGE + urlpdf
    documento = fitz.open(pdf)
    numpaginafirma = int(documento.page_count) - 1
    with fitz.open(pdf) as document:
        words_dict = {}
        for page_number, page in enumerate(document):
            if page_number == numpaginafirma or not ultima_pagina:
                words_blocks = page.get_text("blocks")
                words_text = list(page.get_text("dict").values())
                words_dict[page_number] = words_blocks + words_text
    valor = x = y = None
    for page_number, page_text in words_dict.items():
        for cadena in page_text:
            try:
                if palabras in cadena[4].replace('\n', ' '):
                    valor = cadena
                    if valor:
                        x = int(valor[0])
                        if horizontal:
                            y = words_text[1]-int(valor[3])+70
                        else:
                            y = 890 - int(valor[3])
                    if exacta:
                        t_saltos = cadena[4].count('\n')
                        if not horizontal:
                            y += int(f'{t_saltos}0')
                        # Dividir la cadena en líneas usando '\n' como delimitador
                        lineas, palabra_l = cadena[4].split('\n'), ''
                        for linea in lineas:
                            if len(linea) > len(palabra_l):
                                palabra_l = linea
                        x += len(palabra_l) + 10
                    return x, y, page_number
            except Exception as ex:
                break
    return x, y, numpaginafirma

def obtener_posicion_x_y_saltolinea_firmapagina(urlpdf, palabras):
    # COORDENADAS QUE SE OBTIENE ES X Y SUPERIOR IZQUIERDO
    pdf = SITE_STORAGE + urlpdf
    documento = fitz.open(pdf)
    numpaginafirma = int(documento.page_count) - 1
    numpaginafirmapenultima = numpaginafirma - 1
    paginafirmar = 0
    with fitz.open(pdf) as document:
        words_dict = {}
        for page_number, page in enumerate(document):
            if page_number == numpaginafirma:
                words_blocks = page.get_text("blocks")
                words_text = list(page.get_text("dict").values())
                words_dict[0] = words_blocks + words_text
                paginafirmar = numpaginafirma
                valor = x = y = None
                for cadena in words_dict[0]:
                    try:
                        if palabras in cadena[4].replace('\n', ' '):
                            valor = cadena
                            if valor:
                                x = int(valor[0])
                                y = 5000 - int(valor[3]) - 4125
                            return x, y, paginafirmar
                    except Exception as ex:
                        break
            if page_number == numpaginafirmapenultima:
                words_blocks = page.get_text("blocks")
                words_text = list(page.get_text("dict").values())
                words_dict[0] = words_blocks + words_text
                paginafirmar = numpaginafirmapenultima
                valor = x = y = None
                for cadena in words_dict[0]:
                    try:
                        if palabras in cadena[4].replace('\n', ' '):
                            valor = cadena
                            if valor:
                                x = int(valor[0])
                                y = 5000 - int(valor[3]) - 4125
                            return x, y, paginafirmar
                    except Exception as ex:
                        break

    return x, y, paginafirmar

def obtener_posicion_y(urlpdf, palabras):
    pdf = SITE_STORAGE + urlpdf
    documento = fitz.open(pdf)
    numpaginafirma = int(documento.page_count) - 1
    with fitz.open(pdf) as document:
        for page_number, page in enumerate(document):
            if page_number == numpaginafirma:
                posicion = page.search_for(palabras)
    valor = posicion[0][1] if posicion else None
    y = None
    if valor:
        y = 5000 - int(valor) - 4110
    return y, numpaginafirma


def obtener_posicion_x_y(urlpdf, palabras):  # posiscion Y, la obtiene correctamente--- posicion X, falta ajustar
    pdf = SITE_STORAGE + urlpdf
    documento = fitz.open(pdf)
    numpaginafirma = int(documento.page_count) - 1
    with fitz.open(pdf) as document:
        words_dict = {}
        for page_number, page in enumerate(document):
            if page_number == numpaginafirma:
                words = page.get_text("blocks")
                words_dict[0] = words
    valor = xx = y = None
    for cadena in words_dict[0]:
        if palabras in cadena[4]:
            valor = cadena
            if valor:
                y = 5000 - int(valor[3]) - 4120
                xx = 5000 - int(valor[1]) - 4100
            return xx, y, numpaginafirma
    return xx, y, numpaginafirma


def generarfirmaimagen(request, persona, nombrefirmante):
    try:
        data = {}
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicapdf', ''))
        folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicaimages', ''))
        os.makedirs(folder_pdf, exist_ok=True)
        os.makedirs(folder_images, exist_ok=True)
        qrname = 'qr_firma_{}'.format(persona.id)
        rutapdf = '{}{}.pdf'.format(folder_pdf, qrname)
        rutaimg = '{}{}.png'.format(folder_images, qrname)
        url = pyqrcode.create(f'FIRMADO POR: {nombrefirmante}\nRAZON:\nLOCALIZACION:firmado desde https://sga.unemi.edu.ec\nFECHA: {datetime.datetime.now()}\nVALIDAR CON: www.firmadigital.gob.ec\n2.10.1')
        url.png('{}/{}.png'.format(folder_pdf, qrname), 16, '#000000')  # '#1C3247'
        url_path = request.build_absolute_uri('/')[:-1].strip("/")
        data['url_path'] = url_path
        data['qrname'] = '{}'.format(qrname)
        data['persona'] = persona
        data['nombrefirmante'] = nombrefirmante
        valida = conviert_html_to_pdf('adm_archivosdepartamentales/firma/vistapreviafirma.html', {'data': data})
        if valida:
            images = convert_from_bytes(valida.content,
                                        output_folder=folder_images,
                                        poppler_path=SITE_POPPLER,
                                        output_file=f'{qrname}_firma',
                                        fmt="png")  # dpi=95, size=(150, 45)
            return images[0].filename, True, ''
        else:
            return f'', False, f'Intentelo nuevamente'
    except Exception as ex:
        linea_ = sys.exc_info()[-1].tb_lineno
        print(ex, linea_)
        messages.warning(request, str(ex))
        return f'/static/firmaelectronica/firma_position.jpg', False, f'{ex} - Linea: {linea_}'


def firmaEc(password, base64Str, documento, pathCert):
    import requests
    import base64
    import json
    FIRMAEC_URL = f"https://ws.firmadigital.gob.ec"
    # pdf = open(pathFile, "rb")
    import fileinput

    with open(documento, 'rb') as file:
        for line in fileinput.input(documento):
            # Realiza las operaciones deseadas con cada línea del archivo
            print(line)

    # documento = pdf
    #
    # documento = base64.b64encode(pdf.read())

    pkcs12 = open(pathCert, "rb")
    REST_SERVICE_URL = f"{FIRMAEC_URL}/servicio/appfirmardocumento"
    session = requests.Session()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    pkcs12 = base64.b64encode(pkcs12.read())
    jsonData = json.dumps(
        {
            "versionFirmaEC": "3.0.0",
            "formatoDocumento": "pdf",
            "pagina": "1"
        }
    )
    b64 = base64.b64encode(
        json.dumps(
            {
                "sistemaOperativo": "linux",
                "versionApp": "3.0.0",
                "aplicacion": "FirmaEc",
                "sha": "256"
            }
        ).encode('utf-8')
    ).decode()
    response = session.post(
        REST_SERVICE_URL,
        data={
            "pkcs12": pkcs12,
            "password": password,
            "documento": documento,
            "json": jsonData,
            "base64": b64
        },
        headers=headers
    )
    print(response)
    return response


def firmar(request, password, certificado, pdf, numPagina=1, x=0, y=0, width=0, height=0):
    # pass
    persona = request.session['persona']
    date = datetime.datetime.now()
    date = (datetime.datetime.now() + datetime.timedelta(hours=5)).strftime("D:%Y%m%d%H%M%S+00'00'")
    cert_bytes = certificado.read()
    p12 = pkcs12.load_key_and_certificates(cert_bytes, password.encode("ascii"), default_backend())
    # VALIDACION DE FIRMA
    cert = cert2asn(p12[1])
    entevalidador = cert.issuer.native
    sujeto = cert.subject.native
    nombrefirmante_ = cert.subject.native['common_name']
    # if entevalidador['common_name'] == 'AC BANCO CENTRAL DEL ECUADOR':
    #     return False, f'Fallo al generar firma, entidad certificadora no valida {entevalidador["common_name"]}'
    # if not nombrefirmante_ == remover_caracteres_especiales_unicode(persona.nombre_completo()):
    #     return False, f'Propietario de la firma ({nombrefirmante_}) no coincide con el usuario de la sesión actual {persona.nombre_completo()}'
    # if datetime.datetime.now().date() >= p12[1].not_valid_after.date():
    fecha_emision = p12[1].not_valid_before
    fecha_expiracion = p12[1].not_valid_after
    if datetime.datetime.now().date() >= fecha_expiracion.date():
        lista = []
        for c in p12[2]:
            if c.not_valid_before >= fecha_emision and c.not_valid_after >= fecha_expiracion:
                lista.append(c.not_valid_after)
        if lista:
            fecha_expiracion = max(lista)
        if datetime.datetime.now().date() >= fecha_expiracion.date():
            return False, f'Firma caduco el {p12[1].not_valid_after.date()}'
    url_img, resp_img, msg_img = generarfirmaimagen(request, persona, nombrefirmante_)
    if not resp_img:
        return False, f'Fallo al generar firma. {msg_img}'
    imgFirma = Image.open(url_img)
    dct = {
        "aligned": 0,
        "sigflags": 1,
        "sigflagsft": 132,
        "sigpage": numPagina,  # NUM PAGINA
        "auto_sigfield": True,
        "sigandcertify": True,  # 612 - width, 792 - height
        "signaturebox": (x, y, x + width, y + height),  # UBICACION X, Y, TAMAÑO X, Y
        # "signature": f'firmado Fecha',
        "signature_img_distort": False,
        "signature_img": imgFirma,
        "contact": persona.emailinst,
        "location": f"firmado desde https://sga.unemi.edu.ec",
        "signingdate": date,
        "reason": "",
        "password": password,
    }
    datau = pdf.read() if type(pdf).__name__.lower() != "bytes" else pdf

    # firmaEc(password, None, pdf, certificado)

    datas = cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")

    generar_archivo_firmado = io.BytesIO()
    generar_archivo_firmado.write(datau)
    generar_archivo_firmado.write(datas)
    generar_archivo_firmado.seek(0)
    valido, msg, datos = verificarFirmasPDF(generar_archivo_firmado)
    if not valido:
        return False, f'Fallo al generar firma, {msg}'
    return datau, datas


def firmarmasivo(request, p12, bandera, password, certificado, pdf, numPagina=1, x=0, y=0, width=0, height=0):
    try:
        # pass
        persona = request.session['persona']
        date = datetime.datetime.now()
        date = (datetime.datetime.now() + datetime.timedelta(hours=5)).strftime("D:%Y%m%d%H%M%S+00'00'")
        if not bandera:
            p12 = pkcs12.load_key_and_certificates(certificado.read(), password.encode("ascii"), backends.default_backend())
        # VALIDACION DE FIRMA
        cert = cert2asn(p12[1])
        entevalidador = cert.issuer.native
        sujeto = cert.subject.native
        nombrefirmante_ = cert.subject.native['common_name']
        # if entevalidador['common_name'] == 'AC BANCO CENTRAL DEL ECUADOR':
        #     return False, f'Fallo al generar firma, entidad certificadora no valida {entevalidador["common_name"]}', None
        # if not nombrefirmante_ == remover_caracteres_especiales_unicode(persona.nombre_completo()):
        #     return 'firmaerror', f'Propietario de la firma ({nombrefirmante_}) no coincide con el usuario de la sesión actual {persona.nombre_completo()}', p12

        # if datetime.datetime.now().date() >= p12[1].not_valid_after.date():
        #     return 'firmaerror', f'Firma caduco el {p12[1].not_valid_after.date()}', p12
        fecha_emision = p12[1].not_valid_before
        fecha_expiracion = p12[1].not_valid_after
        if datetime.datetime.now().date() >= fecha_expiracion.date():
            lista = []
            for c in p12[2]:
                if c.not_valid_before >= fecha_emision and c.not_valid_after >= fecha_expiracion:
                    lista.append(c.not_valid_after)
            if lista:
                fecha_expiracion = max(lista)
            if datetime.datetime.now().date() >= fecha_expiracion.date():
                return False, f'Firma caduco el {p12[1].not_valid_after.date()}', p12
        url_img, resp_img, msg_img = generarfirmaimagen(request, persona, nombrefirmante_)
        if not resp_img:
            return False, f'Fallo al generar firma. {msg_img}', p12
        imgFirma = Image.open(url_img)
        dct = {
            "aligned": 0,
            "sigflags": 1,
            "sigflagsft": 132,
            "sigpage": numPagina,  # NUM PAGINA
            "auto_sigfield": True,
            "sigandcertify": True,  # 612 - width, 792 - height
            "signaturebox": (x, y, x + width, y + height),  # UBICACION X, Y, TAMAÑO X, Y
            # "signature": f'firmado Fecha',
            "signature_img_distort": False,
            "signature_img": imgFirma,
            "contact": persona.emailinst,
            "location": f"firmado desde https://sga.unemi.edu.ec",
            "signingdate": date,
            "reason": "",
            "password": password,
        }
        datau = pdf.read() if type(pdf).__name__.lower() != "bytes" else pdf
        datas = None
        try:
            datas = cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")
        except Exception as ex:
            return False, '', None
        generar_archivo_firmado = io.BytesIO()
        generar_archivo_firmado.write(datau)
        generar_archivo_firmado.write(datas)
        generar_archivo_firmado.seek(0)
        valido, msg, datos = verificarFirmasPDF(generar_archivo_firmado)
        if not valido:
            return False, f'Fallo al generar firma, {msg}',None
        return datau, datas, p12
    except Exception as ex:
        return False, '', None


def firmararchivogenerado(request, password, certificado, url_archivo, destino, namefile, numPagina=1, x=0, y=0, width=0, height=0):
    # pass
    try:
        with open(url_archivo, 'rb') as archivo:
            pdf = archivo.read()
        generar_archivo_firmado = io.BytesIO()
        datau, datas = firmar(request, password, certificado, pdf, numPagina, x, y, width, height)
        if not datau:
            return f"{datas}"
        generar_archivo_firmado.name = f'{destino}{namefile}.pdf'
        generar_archivo_firmado.write(datau)
        generar_archivo_firmado.write(datas)
        generar_archivo_firmado.seek(0)
        file_name = default_storage.save(generar_archivo_firmado.name, generar_archivo_firmado)

        #  Reading file from storage
        file = default_storage.open(file_name)
        file_url = default_storage.url(file_name)
        return True
    except Exception as ex:
        return ex.__str__()


def verificarFirmasPDF(path):
    import base64
    import requests
    import json
    from requests.exceptions import ConnectTimeout
    header = {"Content-Type": "text/plain; charset=UTF-8"}
    WS_VALIDACION_FIRMA_MINTEL = (
        f"{URL_VALIDADOR}/servicio/validacionavanzadapdf"
    )

    # with open(path, "rb") as pdf_file:
    #     encoded_string = base64.b64encode(pdf_file.read())
    encoded_string = base64.b64encode(path.read())

    try:
        response_backup = requests.post(
            url=WS_VALIDACION_FIRMA_MINTEL,
            data=encoded_string.decode("utf-8"),
            headers=header,
        )
        datos = json.loads(response_backup.text)
        valido = datos['firmasValidas']
        msg = 'documento con firmas invalidas' if not valido else ''
        return valido, msg, datos
    except ConnectTimeout as err:
        return False, f"Error WS_FIRMA_MINTEL: {err=}, {type(err)=}", None
    except Exception as err:
        return False, f"Error WS_FIRMA_SERCOP: {err=}, {type(err)=}", None
