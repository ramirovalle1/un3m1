import os
from datetime import datetime
import base64
from io import BytesIO
import qrcode
from PIL import Image, ImageDraw, ImageFont
from endesive.pdf import cms
from endesive.signer import cert2asn
from cryptography.hazmat import backends
from settings import BASE_DIR
from cryptography.hazmat.primitives.serialization import pkcs12


def get_archivo_firmado_base64(codigoDocumentoFirmado):
    archivoBase64, arch_codi = None, None
    if codigoDocumentoFirmado:
        registro_archivo = ArchivoFirmaEc.objects.filter(nombre__istartswith=f"{codigoDocumentoFirmado}.").order_by('-fecha_creacion').first()
        arch_codi = registro_archivo.arch_codi
        if registro_archivo:
            archivo_firmado = ArchivoFirmaEc0001.objects.filter(
                arch_codi=arch_codi
            ).union(
                ArchivoFirmaEc0002.objects.filter(
                    arch_codi=arch_codi
                )
            ).order_by('-arch_codi').first()
            if archivo_firmado:
                archivoBase64 = archivo_firmado.archivo
    return archivoBase64, arch_codi


def cargarCertificadoPkcs12(certificado, password):
    return pkcs12.load_key_and_certificates(certificado.read(), password.encode("ascii"), backends.default_backend())


def firmarPdf(request, archivo, passwordCertificado, certificadoPkcs12, numPagina=1, x=0, y=0, width=0, height=0,
              razon=""):
    persona = request.session['persona']
    date = (datetime.utcnow()).strftime("D:%Y%m%d%H%M%S+00'00'")
    certList = [certificadoPkcs12[1]] + certificadoPkcs12[2]
    certDateValid = False
    certValid = None
    currentDate = datetime.now()

    for c in certList:
        if c.not_valid_before <= currentDate <= c.not_valid_after:
            certDateValid = True
            certValid = c
            break

    # VALIDACION DE FIRMA
    cert = cert2asn(certValid)
    entevalidador = cert.issuer.native
    sujeto = cert.subject.native
    nombrefirmante_ = cert.subject.native['common_name']
    if not certDateValid:
        raise ValueError(f'Certificado ya caducó')
    imgFirma = qrImgFirma(request, persona, "png")[1]
    dct = {
        "aligned": 0,
        "sigflags": 1,
        "sigflagsft": 132,
        "sigpage": numPagina,
        "auto_sigfield": True,
        "sigandcertify": True,
        "signaturebox": (x, y + 10, x + width, y + height),  # UBICACION X, Y, TAMAÑO X, Y
        "signature_img_distort": False,
        "signature_img": imgFirma,
        "contact": persona.emailinst,
        "location": "",
        "signingdate": date,
        "reason": razon or "",
        "password": passwordCertificado,
    }
    datau = archivo.read() if type(archivo).__name__.lower() != "bytes" else archivo
    p12 = certificadoPkcs12
    datas = cms.sign(datau, dct, p12[0], cert, p12[2], "sha512")
    return datau, datas


def firmaEcToken(sistema, hashKey, cedula, documentos):
    from settings import FIRMAEC_URL
    import requests

    jsonRequest = {
        "sistema": sistema,
        "cedula": cedula,
        "documentos": documentos
    }

    REST_SERVICE_URL = f"{FIRMAEC_URL}/servicio/documentos"
    session = requests.Session()

    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": hashKey
    }

    response = session.post(
        REST_SERVICE_URL,
        json=jsonRequest,
        headers=headers
    )

    return response


def getFirmaEcLink(cedula, documento: str, pagina: int, x, y, razon="", extensionArchivo="pdf"):
    from settings import FIRMAEC_APIKEY, FIRMAEC_SISTEMA
    import urllib.parse
    nombre_documento = datetime.now().strftime("%Y%m%d%H%M%S%f")
    documentos = [
        {"nombre": nombre_documento, "documento": documento}
    ]
    response = firmaEcToken(FIRMAEC_SISTEMA, FIRMAEC_APIKEY, cedula, documentos)
    if response.status_code == 201:
        token = response.text
        link_firma_ec = f"firmaec://firmaec/firmar?token={token}&tipo_certificado=2&llx={x}&lly={y}&estampado=QR&pagina={pagina}&razon={urllib.parse.quote(razon)}&url=https://firmaec.unae.edu.ec/api"
        return (link_firma_ec, nombre_documento)
    return None, None


def firmaEc(password, base64Str, pathFile, pathCert):
    import requests
    import base64
    import json
    from settings import FIRMAEC_URL
    pdf = open(pathFile, "rb")
    documento = base64.b64encode(pdf.read())

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
    return response


def verificarFirmasPdf(path):
    from endesive import verifier
    from asn1crypto import cms
    pdfdata = open(path, 'rb').read()
    results = []
    firmas = []
    n = pdfdata.find(b"/ByteRange")
    while n != -1:
        start = pdfdata.find(b"[", n)
        stop = pdfdata.find(b"]", start)
        assert n != -1 and start != -1 and stop != -1
        br = [int(i, 10) for i in pdfdata[start + 1: stop].split()]
        contents = pdfdata[br[0] + br[1] + 1: br[2] - 1]
        bcontents = bytes.fromhex(contents.decode("utf8"))
        data1 = pdfdata[br[0]: br[0] + br[1]]
        data2 = pdfdata[br[2]: br[2] + br[3]]
        signedData = data1 + data2

        result = verifier.verify(bcontents, signedData, [])
        firmas.append(dict(
            dict(dict(cms.ContentInfo.load(bcontents)['content']['certificates'].native[-1])["tbs_certificate"])[
                "subject"])["common_name"])
        results.append(result)
        n = pdfdata.find(b"/ByteRange", br[2] + br[3])
    return results, firmas


def firmarXml(request, archivo, p12):
    from endesive import signer
    datau = archivo.read() if type(archivo).__name__.lower() != "bytes" else archivo
    datas = signer.sign(
        datau, p12[0], p12[1], p12[2], "sha256"
    )
    return datas, datas.hex().encode("utf-8")


def qrImgFirma(request, persona, format="jpeg", paraMostrar=False):
    text1 = 'Firmado electrónicamente por:'
    nombres = f"{persona.nombres} {persona.apellido1} {persona.apellido2}"

    qr = qrcode.QRCode(
        box_size=8,
        border=1
    )

    qr.add_data(
        f"FIRMADO POR: {nombres}\nRAZON:\nLOCALIZACION:\nFECHA:{datetime.now().isoformat()}-05:00\nVALIDAR CON: www.firmadigital.gob.ec\n3.0.0")

    fontsPath = os.path.join(BASE_DIR, "static", "font", "fonts_firmaelectronica")
    qr.make(fit=True)
    img = qr.make_image()
    img_w, img_h = img.size
    img_w += 5
    backcolor = (255, 255, 255, 0)
    mode = "RGBA"
    if format == "jpeg":
        backcolor = (255, 255, 255)
        mode = "RGB"
    result = Image.new(mode, (1100, img_h), color=backcolor)
    result.paste(img, (0, 0))
    draw = ImageDraw.Draw(result, mode=mode)

    draw.text((img_w, 60 - 2), text1, font=ImageFont.truetype(os.path.join(fontsPath, "CourierPSRegular.ttf"), 40),
              fill=(0, 0, 0))
    draw.text((img_w, 120 - 2), f"{(persona.nombres or '').upper()}",
              font=ImageFont.truetype(os.path.join(fontsPath, "CourierNewOSBold.ttf"), 80), fill=(0, 0, 0))
    draw.text((img_w, 200 - 2), f"{(persona.apellido1 or '').upper()} {(persona.apellido2 or '').upper()}",
              font=ImageFont.truetype(os.path.join(fontsPath, "CourierNewOSBold.ttf"), 80), fill=(0, 0, 0))

    # if paraMostrar:
    #     draw.text((img_w, 60 - 2), "PUEDES MOVER EL SELLO", font=ImageFont.truetype(os.path.join(fontsPath, "NotoSansMono-Bold.ttf"), 12),
    #               fill=(0, 0, 0))
    #     draw.text((img_w, 80 - 2), f"DOBLE CLIC PARA QUITAR",
    #               font=ImageFont.truetype(os.path.join(fontsPath, "NotoSansMono-Bold.ttf"), 12), fill=(255,0,0))
    # else:
    #     draw.text((img_w, 30 - 2), text1, font=ImageFont.truetype(os.path.join(fontsPath, "NotoSansMono-Bold.ttf"), 18),
    #               fill=(0, 0, 0))
    #     draw.text((img_w, 60 - 2), f"{(persona.nombres or '').upper()}",
    #               font=ImageFont.truetype(os.path.join(fontsPath, "Prompt-Regular.ttf"), 24), fill=(0, 0, 0))
    #     draw.text((img_w, 90 - 2), f"{(persona.apellido1 or '').upper()} {(persona.apellido2 or '').upper()}",
    #               font=ImageFont.truetype(os.path.join(fontsPath, "Prompt-Regular.ttf"), 24), fill=(0, 0, 0))
    buffered = BytesIO()
    result.save(buffered, format=format)
    return "data:image/{};base64, {}".format(format, base64.b64encode(buffered.getvalue()).decode()), Image.open(
        buffered)
