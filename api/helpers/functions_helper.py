# coding=utf-8
import sys
import subprocess
import os
import json
import unicodedata
import pyqrcode
import shutil
import uuid
import io as StringIO
from datetime import datetime


def read_json():
    from settings import SITE_ROOT
    with open(os.path.join(SITE_ROOT, 'api', 'base.json')) as fileJson:
        dataJson = json.load(fileJson)
    return dataJson


def get_variable(e):
    from settings import DEBUG
    value = None
    dataJson = read_json()
    if DEBUG:
        dev = None
        if 'dev' in dataJson:
            dev = dataJson['dev']
            for key in dev:
                if e == key:
                    value = dev[key]
    else:
        for key in dataJson:
            if e == key:
                value = dataJson[key]
    return value


def fetch_resources(uri, rel):
    from settings import MEDIA_ROOT, MEDIA_URL
    return os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ""))


def remove_accents(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD', str(cadena)) if unicodedata.category(c) != 'Mn'))
    return s


def tipoparametro(tipo):
    if tipo == 1:
        return "string"
    elif tipo == 2:
        return "integer"
    elif tipo == 3:
        return "double"
    elif tipo == 4:
        return "boolean"
    elif tipo == 5:
        return "integer"
    elif tipo == 6:
        return "string"
    elif tipo == 7:
        return "integer"
    return "string"


def fixparametro(tipo, valor):
    if tipo == 6:
        # FECHA
        fm = valor.index("-")
        sm = valor.index("-", fm + 1)
        d = valor[:fm]
        m = valor[fm + 1:sm]
        y = valor[sm + 1:]
        return y + "-" + m + "-" + d
    return valor


def transform(parametro, request):
    return "%s=%s:%s" % (parametro.nombre, tipoparametro(parametro.tipo), fixparametro(parametro.tipo, request.data[parametro.nombre]))


def transform_jasperstarter(parametro, request):
    from sga.templatetags.sga_extras import encrypt
    if parametro.tipo == 1 or parametro.tipo == 6:
        return u'%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, request.data[parametro.nombre]))
    elif parametro.tipo == 2 or parametro.tipo == 5:
        return u'%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.data[parametro.nombre] if type(request.data[parametro.nombre]) is int else int(encrypt(request.data[parametro.nombre]))))
    else:
        return u'%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.data[parametro.nombre]))


def link_callback(uri, rel):
    from settings import MEDIA_ROOT, MEDIA_URL, STATIC_URL, BASE_DIR, SITE_STORAGE
    sUrl = STATIC_URL
    sRoot = os.path.join(BASE_DIR, 'static', 'pdf', 'tmp')
    mUrl = MEDIA_URL
    mRoot = os.path.join(SITE_STORAGE, 'media', 'pdf', 'tmp')
    if uri.startswith(mUrl):
        path = os.path.join(mRoot, uri.replace(mUrl, ""))
    elif uri.startswith(sUrl):
        path = os.path.join(sRoot, uri.replace(sUrl, ""))
    else:
        return uri
    # print(path)
    if not os.path.isfile(path):
        raise Exception('media URI must start with %s or %s' % (sUrl, mUrl))
    return path


def conviert_html_to_pdf_save_path(request, template_path, context_dict, output_folder, fileName, css=None):
    from settings import MEDIA_ROOT, MEDIA_URL, STATIC_URL, BASE_DIR, SITE_STORAGE
    from django.template.loader import get_template
    from xhtml2pdf import pisa
    template = get_template(template_path)
    html = template.render(context_dict, request).encode(encoding="UTF-8")
    result = StringIO.BytesIO()
    filepdf = open(output_folder + os.sep + fileName, "w+b")
    links = lambda uri, rel: os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ''))
    pdf1 = pisa.pisaDocument(StringIO.BytesIO(html), dest=filepdf, default_css=css, link_callback=link_callback)
    pisaStatus = pisa.CreatePDF(StringIO.BytesIO(html), result, link_callback=links if links else link_callback)
    if not pdf1.err:
        return {"isSuccess": True, "message": "",  "data": {"filepdf": filepdf, "result": result}}
    return {"isSuccess": False, "message": "Ocurrio un error al generar pdf", "data": {"pdf1": pdf1}}


def generate_acuerdo_terminos_examen_final(eMatriculaSedeExamen, isDemo=False):
    from settings import MEDIA_ROOT, MEDIA_URL, STATIC_URL, BASE_DIR, SITE_STORAGE, DEBUG
    from PyPDF2 import PdfFileMerger, PdfFileReader, PdfFileWriter
    try:
        ahora = datetime.now()
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'

        eInscripcion = eMatriculaSedeExamen.matricula.inscripcion
        ePersona = eInscripcion.persona
        eUser = ePersona.usuario
        username = eUser.username
        fileName = f'acuerdo_{ahora.strftime("%Y_%m_%d__%H_%M_%S")}'
        if isDemo:
            fileName = f'borrador_{ahora.strftime("%Y_%m_%d__%H_%M_%S")}'
        folder_comprobante = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), 'acuerdo', str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', ''))
        folder_qrcode = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), 'acuerdo', str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'qrcode', ''))
        ruta_img = folder_qrcode + fileName + '.png'
        ruta_pdf = folder_comprobante + fileName + '.pdf'
        # url_pdf = f'applicant/{ePerson.document}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
        url_pdf = f'{url_path}/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
        url_pdf_final = f'/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
        # url_png = f'applicant/{ePerson.document}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'
        url_png = f'{url_path}/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'
        url_png_final = f'/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'
        if os.path.isfile(ruta_pdf):
            os.remove(ruta_pdf)
        elif os.path.isfile(ruta_img):
            os.remove(ruta_img)
        os.makedirs(folder_comprobante, exist_ok=True)
        os.makedirs(folder_qrcode, exist_ok=True)
        num_comprobante = f"UNEMI-EXAMEN-{eMatriculaSedeExamen.id:08d}-{str(ahora.year)}"
        if isDemo:
            num_comprobante = f"UNEMI-BORRARDOR-{0000:08d}-{str(ahora.year)}"
        # firma = f'Comprobante Nro: {num_comprobante} \nInscripción: {eApplicant.inscription.person.__str__()}\n{ePerson.get_type_document_display()}: {ePerson.document}\nFecha inscripción: {eApplicantPhase.confirmation_date.strftime("%Y/%m/%d %H:%M:%S")}\nGenerado en: https://admisionpregrado.unemi.edu.ec\nDocumento: {url_pdf}'.encode('utf-8')
        firma = f'Comprobante Nro: {num_comprobante} \nGenerado en: https://sga.unemi.edu.ec \nDocumento: {url_pdf}'.encode('utf-8')
        if isDemo:
            firma = f'Comprobante NO VALIDO'.encode('utf-8')
        # url = pyqrcode.create(firma, version=19, encoding='iso-8859-1', mode='binary')
        url = pyqrcode.create(firma, encoding='iso-8859-1', mode='binary')
        imagen_qr = url.png(ruta_img, scale=16, module_color=[0, 0, 0, 128], background=[255, 248, 220])
        archivofoto = None
        if eMatriculaSedeExamen.archivofoto:
            rutas = (eMatriculaSedeExamen.archivofoto.url).split("media/")
            archivofoto = rutas[1]
        aData = {}
        aData['num_comprobante'] = num_comprobante
        aData['version'] = ahora.strftime('%Y%m%d_%H%M%S')
        aData['eMatriculaSedeExamen'] = eMatriculaSedeExamen
        aData['eInscripcion'] = eInscripcion
        aData['imagen_qr'] = f'{url_path}/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'
        aData['ruta_qr'] = f'sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/qrcode/{fileName}.png'
        aData['ahora'] = ahora
        aData['isDemo'] = isDemo
        aData['archivofoto'] = archivofoto
        aData['num_comprobante'] = num_comprobante
        aData['ePersona'] = ePersona
        aData['terminos_text'] = ''
        es_admision = eInscripcion.es_admision()
        es_pregrado = eInscripcion.es_pregrado()
        if es_admision or es_pregrado:
            if ePeriodoMatricula := eMatriculaSedeExamen.matricula.nivel.periodo.periodomatricula_set.filter(status=True, mostrar_terminos_examenes=True).first():
                 aData['terminos_text'] = ePeriodoMatricula.terminos_examenes if es_pregrado else ePeriodoMatricula.terminos_nivelacion
        result = conviert_html_to_pdf_save_path(request=None, template_path='pregrado/aulavirtual/examen/acuerdo_examen_final.html', context_dict={
            'pagesize': 'A4',
            'data': aData,
        }, output_folder=folder_comprobante, fileName=f"{fileName}.pdf", css=None)
        isSuccess = result.get('isSuccess', False)
        if not isSuccess:
            message = result.get('message', 'Error al generar borrador de acuerdo' if isDemo else 'Error al generar acuerdo')
            raise NameError(message)
        fileNameMerge = f'acuerdo_merge_{ahora.strftime("%Y_%m_%d__%H_%M_%S")}'
        if isDemo:
            fileNameMerge = f'borrador_merge_{ahora.strftime("%Y_%m_%d__%H_%M_%S")}'
        ruta_pdf_final = folder_comprobante + fileNameMerge + '.pdf'
        url_pdf_merge = f'/media/sede/examen/{ePersona.documento()}/acuerdo/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileNameMerge}.pdf'
        if os.path.isfile(ruta_pdf_final):
            os.remove(ruta_pdf_final)
        os.makedirs(folder_comprobante, exist_ok=True)

        # merger = PdfFileMerger()
        # merger.setPageMode('/FullScreen')
        # merger.append(PdfFileReader(open(ruta_pdf, "rb")))
        # if DEBUG:
        #     merger.append(eMatriculaSedeExamen.archivoidentidad)
        # else:
        #     # merger.append(SITE_STORAGE + eMatriculaSedeExamen.archivoidentidad.url)
        #     merger.append(PdfFileReader(open("".join([SITE_STORAGE, eMatriculaSedeExamen.archivoidentidad.url]).replace('//', '/'), "rb")))
        # with open(ruta_pdf_final, "wb") as new_file:
        #     merger.write(new_file)
        # merger.close()
        # pdfs = [
        #     PdfFileReader(open(ruta_pdf, "rb")),
        #     open("".join([SITE_STORAGE, eMatriculaSedeExamen.archivoidentidad.url]).replace('//', '/'), "rb") if not DEBUG else eMatriculaSedeExamen.archivoidentidad.file.name
        # ]
        # pdfWriter = PdfFileWriter()
        # pdfReader_comprobnte = PdfFileReader(ruta_pdf)
        # for pageNum in range(pdfReader_comprobnte.numPages):
        #     pageObj = pdfReader_comprobnte.getPage(pageNum)
        #     pdfWriter.addPage(pageObj)
        # pdfReader_identidad = PdfFileReader(SITE_STORAGE + eMatriculaSedeExamen.archivoidentidad.url)
        # for pageNum in range(pdfReader_identidad.numPages):
        #     pageObj = pdfReader_identidad.getPage(pageNum)
        #     pdfWriter.addPage(pageObj)
        # pdfWriter.write(open(ruta_pdf_final, "wb"))
        return {"isSuccess": True, "message": 'Se genero correctamenta borrador' if isDemo else 'Se genero correctamente acuerdo', "data": {"url_pdf": url_pdf_final, "url_png": url_png_final}}
    except Exception as ex:
        # print(sys.exc_info()[-1].tb_lineno)
        # print("COMPROBANTE")
        # print(ruta_pdf)
        # print("CEDULA")
        # print(SITE_STORAGE + eMatriculaSedeExamen.archivoidentidad.url)
        return {"isSuccess": False, "message": ex.__str__(), "data": {}}


def generate_qr_examen_final(eMateriaAsignadaPlanificacionSedeVirtualExamen, **kwargs):
    from hashlib import md5
    from settings import MEDIA_ROOT, MEDIA_URL, STATIC_URL, BASE_DIR, SITE_STORAGE, DEBUG, JR_JAVA_COMMAND, \
        JR_RUN, DATABASES, STATIC_ROOT, SITE_ROOT
    from sga.models import Reporte
    from django.core.exceptions import ObjectDoesNotExist
    from sga.reportes import transform_jasperstarter_kwargs
    from sga.templatetags.sga_extras import encrypt
    unicode = str
    try:
        ahora = datetime.now()
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'
        eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
        eInscripcion = eMateriaAsignada.matricula.inscripcion
        ePersona = eInscripcion.persona
        eUser = ePersona.usuario
        username = eUser.username

        output_folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf'))
        output_folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images'))
        try:
            shutil.rmtree(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            shutil.rmtree(output_folder_images)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_images)
        except Exception as ex:
            pass
        try:
            eReporte = Reporte.objects.get(pk=657)
        except ObjectDoesNotExist:
            raise NameError(u"Reporte no encontrado")
        pdfname = str(uuid.uuid4())
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', ''))
        qrname = str(uuid.uuid4())
        folder_qr = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images', ''))
        rutapdf = folder_pdf + pdfname + '.pdf'
        rutaqr = folder_qr + qrname + '.png'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        if os.path.isfile(rutaqr):
            os.remove(rutaqr)
        fecha_hora = ahora.year.__str__() + ahora.month.__str__() + ahora.day.__str__() + ahora.hour.__str__() + ahora.minute.__str__() + ahora.second.__str__()
        token = md5(str(encrypt(eMateriaAsignadaPlanificacionSedeVirtualExamen.id) + fecha_hora).encode("utf-8")).hexdigest()
        firma = f'{token}'.encode('utf-8')
        url = pyqrcode.create(firma, encoding='iso-8859-1', mode='binary')
        # imagen_qr = url.png(rutaqr, scale=16, module_color=[0, 0, 0, 128], background=[255, 248, 220])
        imagen_qr = url.png(rutaqr, 16, '#000000')
        url_pdf = "/".join(['sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', pdfname + ".pdf"])
        url_qr = "/".join(['sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images', pdfname + ".png"])
        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                        'pr', eReporte.archivo.file.name,
                        '--jdbc-dir', JR_RUN,
                        '-f', 'pdf',
                        '-t', 'postgres',
                        '-H', DATABASES['sga_select']['HOST'],
                        '-n', DATABASES['sga_select']['NAME'],
                        '-u', DATABASES['sga_select']['USER'],
                        '-p', '{}{}{}'.format('"', DATABASES['sga_select']['PASSWORD'], '"'),
                        '--db-port', DATABASES['sga_select']['PORT'],
                        '-o', output_folder_pdf + os.sep + pdfname]
        parametros = eReporte.parametros()
        if kwargs:
            paramlist = [transform_jasperstarter_kwargs(p, **kwargs) for p in parametros]

        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')
        # base_url = get_variable('SITE_URL_SGA')
        runjrcommand.append(u'MEDIA_DIR=' + str("/".join([MEDIA_ROOT, ''])))
        # static_dir = f"{url_path}/static/img/"
        static_dir = os.path.join(SITE_ROOT, 'static', 'img')
        runjrcommand.append(u'STATIC_DIR=' + str("/".join([static_dir, ''])))
        runjrcommand.append(u'QR_DIR=' + str(rutaqr))
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)
            # print('runjr:', runjr.returncode)
        else:
            runjr = subprocess.call(mens.encode("latin1"), shell=True)
        # print("url_pdf: ", url_pdf)

        return {"isSuccess": True, "message": 'Se genero correctamente código QR', "data": {"url_pdf": url_pdf, "codigo_qr": token}}
    except Exception as ex:
        # print(sys.exc_info()[-1].tb_lineno)
        # print(ex.__str__())
        return {"isSuccess": False, "message": "Error al generar código QR {}".format(ex), "data": {}}


def generate_qr_examen_final2(eMateriaAsignadaPlanificacionSedeVirtualExamen, **kwargs):
    from hashlib import md5
    from settings import MEDIA_ROOT, MEDIA_URL, STATIC_URL, BASE_DIR, SITE_STORAGE, DEBUG, JR_JAVA_COMMAND, \
        JR_RUN, DATABASES, STATIC_ROOT, SITE_ROOT
    from sga.models import Reporte
    from django.core.exceptions import ObjectDoesNotExist
    from sga.reportes import transform_jasperstarter_kwargs
    from sga.templatetags.sga_extras import encrypt
    unicode = str
    try:
        ahora = datetime.now()
        url_path = 'http://127.0.0.1:8000'
        if not DEBUG:
            url_path = 'https://sga.unemi.edu.ec'
        eMateriaAsignada = eMateriaAsignadaPlanificacionSedeVirtualExamen.materiaasignada
        eInscripcion = eMateriaAsignada.matricula.inscripcion
        ePersona = eInscripcion.persona
        eUser = ePersona.usuario
        username = eUser.username

        output_folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf'))
        output_folder_images = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images'))
        try:
            shutil.rmtree(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_pdf)
        except Exception as ex:
            pass
        try:
            shutil.rmtree(output_folder_images)
        except Exception as ex:
            pass
        try:
            os.makedirs(output_folder_images)
        except Exception as ex:
            pass
        try:
            eReporte = Reporte.objects.get(pk=657)
        except ObjectDoesNotExist:
            raise NameError(u"Reporte no encontrado")
        pdfname = str(uuid.uuid4())
        folder_pdf = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', ''))
        qrname = str(uuid.uuid4())
        folder_qr = os.path.join(os.path.join(SITE_STORAGE, 'media', 'sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images', ''))
        rutapdf = folder_pdf + pdfname + '.pdf'
        rutaqr = folder_qr + qrname + '.png'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)
        if os.path.isfile(rutaqr):
            os.remove(rutaqr)
        fecha_hora = ahora.year.__str__() + ahora.month.__str__() + ahora.day.__str__() + ahora.hour.__str__() + ahora.minute.__str__() + ahora.second.__str__()
        token = md5(str(encrypt(eMateriaAsignadaPlanificacionSedeVirtualExamen.id) + fecha_hora).encode("utf-8")).hexdigest()
        firma = f'{token}'.encode('utf-8')
        url = pyqrcode.create(firma, encoding='iso-8859-1', mode='binary')
        # imagen_qr = url.png(rutaqr, scale=16, module_color=[0, 0, 0, 128], background=[255, 248, 220])
        imagen_qr = url.png(rutaqr, 16, '#000000')
        url_pdf = "/".join(['sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', pdfname + ".pdf"])
        url_qr = "/".join(['sede', 'examen', ePersona.documento(), str(eMateriaAsignada.id), str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'images', qrname + ".png"])
        # runjrcommand = [JR_JAVA_COMMAND, '-jar',
        #                 os.path.join(JR_RUN, 'jasperstarter.jar'),
        #                 'pr', eReporte.archivo.file.name,
        #                 '--jdbc-dir', JR_RUN,
        #                 '-f', 'pdf',
        #                 '-t', 'postgres',
        #                 '-H', DATABASES['default']['HOST'],
        #                 '-n', DATABASES['default']['NAME'],
        #                 '-u', DATABASES['default']['USER'],
        #                 '-p', f"'{DATABASES['default']['PASSWORD']}'",
        #                 '--db-port', DATABASES['default']['PORT'],
        #                 '-o', output_folder_pdf + os.sep + pdfname]
        # parametros = eReporte.parametros()
        # if kwargs:
        #     paramlist = [transform_jasperstarter_kwargs(p, **kwargs) for p in parametros]
        #
        # if paramlist:
        #     runjrcommand.append('-P')
        #     for parm in paramlist:
        #         runjrcommand.append(parm)
        # else:
        #     runjrcommand.append('-P')
        # # base_url = get_variable('SITE_URL_SGA')
        # runjrcommand.append(u'MEDIA_DIR=' + str("/".join([MEDIA_ROOT, ''])))
        # # static_dir = f"{url_path}/static/img/"
        # static_dir = os.path.join(SITE_ROOT, 'static', 'img')
        # runjrcommand.append(u'STATIC_DIR=' + str("/".join([static_dir, ''])))
        # runjrcommand.append(u'QR_DIR=' + str(rutaqr))
        # mens = ''
        # mensaje = ''
        # for m in runjrcommand:
        #     mens += ' ' + m
        # if DEBUG:
        #     runjr = subprocess.run(mens, shell=True, check=True)
        #     # print('runjr:', runjr.returncode)
        # else:
        #     runjr = subprocess.call(mens.encode("latin1"), shell=True)
        # # print("url_pdf: ", url_pdf)

        return {"isSuccess": True, "message": 'Se genero correctamente código QR', "data": {"url_pdf": url_pdf, "pdfname": pdfname, "url_qr": url_qr, "codigo_qr": token}}
    except Exception as ex:
        # print(sys.exc_info()[-1].tb_lineno)
        # print(ex.__str__())
        return {"isSuccess": False, "message": "Error al generar código QR", "data": {}}

