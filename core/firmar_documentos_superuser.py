# *-* coding: utf-8 *-*
import datetime
import io
import os
import sys

from cryptography.hazmat import backends
from cryptography.hazmat.primitives.serialization import pkcs12
from django.contrib import messages
from endesive.pdf import cms
from PIL import Image
import random
import pyqrcode
from endesive.signer import cert2asn
from pdf2image import convert_from_bytes

from core.firmar_documentos import verificarFirmasPDF
from settings import SITE_STORAGE, SITE_POPPLER, MEDIA_URL, MEDIA_ROOT, DEBUG
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado_generico, conviert_html_to_pdf
from sga.models import Persona, unicode


def generarfirmaimagenfecha(request, persona, nombrefirmante, fecha):
    try:
        data = {}
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicapdf', ''))
        folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmaelectronicaimages', ''))
        os.makedirs(folder_pdf, exist_ok=True)
        os.makedirs(folder_images, exist_ok=True)
        qrname = 'qr_firma_{}'.format(persona.id)
        rutapdf = '{}{}.pdf'.format(folder_pdf, qrname)
        rutaimg = '{}{}.png'.format(folder_images, qrname)
        url = pyqrcode.create(f'FIRMADO POR: {nombrefirmante}\nRAZON:\nLOCALIZACION:\nFECHA: {fecha}\nVALIDAR CON: www.firmadigital.gob.ec\n2.10.1')
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


def firmarfecha(request, fecha, password, certificado, pdf, numPagina=1, x=0, y=0, width=0, height=0):
    # pass
    persona = request.session['persona']
    date = (fecha + datetime.timedelta(hours=5)).strftime("D:%Y%m%d%H%M%S+00'00'")
    p12 = pkcs12.load_key_and_certificates(certificado.read(), password.encode("ascii"), backends.default_backend())
    # VALIDACION DE FIRMA
    cert = cert2asn(p12[1])
    entevalidador = cert.issuer.native
    sujeto = cert.subject.native
    nombrefirmante_ = cert.subject.native['common_name']
    # if entevalidador['common_name'] == 'AC BANCO CENTRAL DEL ECUADOR':
    #     return False, f'Fallo al generar firma, entidad certificadora no valida {entevalidador["common_name"]}'
    # if not nombrefirmante_ == persona.nombre_completo():
    #     return False, f'Propietario de la firma ({nombrefirmante_}) no coincide con el usuario de la sesión actual {persona.nombre_completo()}'
    # if datetime.datetime.now().date() >= p12[1].not_valid_after.date():
    #     return False, f'Firma caduco el {p12[1].not_valid_after.date()}'
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
    url_img, resp_img, msg_img = generarfirmaimagenfecha(request, persona, nombrefirmante_, fecha)
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
        "location": f"",
        "signingdate": date,
        "reason": "",
        "password": password,
    }
    datau = pdf.read() if type(pdf).__name__.lower() != "bytes" else pdf
    datas = cms.sign(datau, dct, p12[0], p12[1], p12[2], "sha256")
    generar_archivo_firmado = io.BytesIO()
    generar_archivo_firmado.write(datau)
    generar_archivo_firmado.write(datas)
    generar_archivo_firmado.seek(0)
    valido, msg, datos = verificarFirmasPDF(generar_archivo_firmado)
    if not valido:
        return False, f'Fallo al generar firma, {msg}'
    return datau, datas
