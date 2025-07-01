#!/usr/bin/env python
import os
import io as StringIO
import sys
import pyqrcode


csv_filepathname3 = "problemas2021_corregido_g6.csv"
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from xhtml2pdf import pisa
from xhtml2pdf.default import DEFAULT_FONT
from settings import SITE_STORAGE, DEBUG, MEDIA_ROOT, MEDIA_URL
from django.db import transaction
#from settings import SITE_STORAGE, DEBUG
from sga.funciones import lista_mejores_promedio_beca_v3, asignar_orden_portipo_beca, listado_incripciones_reconocimiento_academico, lista_discapacitado_beca, lista_deportista_beca, lista_migrante_exterior_beca, lista_etnia_beca, lista_gruposocioeconomico_beca, elimina_tildes
from sga.models import BecaTipo, Inscripcion, PreInscripcionBeca, Periodo, Matricula, Administrativo
from feria.models import CronogramaFeria, ParticipanteFeria
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificadoferiaparticipacion
import warnings
from django.template.loader import get_template

warnings.filterwarnings('ignore', message='Unverified HTTPS request')
from PyPDF2 import PdfFileReader


def conviert_html_to_pdfsaveqrcertificadoferiaparticipacion2(request, template_src, context_dict, output_folder, filename):
    template = get_template(template_src)
    html = template.render(context_dict).encode(encoding="UTF-8")
    result = StringIO.BytesIO()
    filepdf = open(output_folder + os.sep + filename, "w+b")
    links = lambda uri, rel: os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ''))
    #pdfmetrics.registerFont(TTFont('zhfont', os.path.join(SITE_ROOT, 'static/fonts/Poppins/Poppins-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('zhfont', os.path.join(SITE_ROOT, 'static/fonts/Poppins/Poppins-Regular.ttf')))
    pdfmetrics.registerFont(TTFont('zhfont_bold', os.path.join(SITE_ROOT, 'static/fonts/Poppins/Poppins-Bold.ttf')))
    DEFAULT_FONT["helvetica"] = "zhfont"
    DEFAULT_FONT["helvetica-bold"] = "zhfont_bold"
    pdf1 = pisa.pisaDocument(StringIO.BytesIO(html), dest=filepdf, link_callback=links)
    pisaStatus = pisa.CreatePDF(StringIO.BytesIO(html), result, link_callback=links)
    if not pdf1.err:
        # return HttpResponse(result.getvalue(), content_type='application/pdf')
        return True, filepdf.name, result
    return False, pdf1, None

def generateCertificatesParticipants(request={}):
    eCronograma = CronogramaFeria.objects.get(pk=1)
    eParticipantes = ParticipanteFeria.objects.filter(solicitud__cronograma=eCronograma,
                                                      #solicitud_id=88,
                                                      solicitud__estado=2,
                                                      solicitud__status=True,
                                                      status=True)
    errores = []
    for index, eParticipante in enumerate(eParticipantes):
        eInscripcion = eParticipante.inscripcion
        eUsuario = eInscripcion.persona.usuario
        with transaction.atomic(using='default'):
            try:
                aData = {}
                url_path = 'http://127.0.0.1:8000'
                path_folder = SITE_ROOT
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                    path_folder = SITE_STORAGE



                aData['rector'] = rector = Administrativo.objects.get(pk=225)
                aData['rectorfirma'] = rectorfirma = rector.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['decano'] = decano = Administrativo.objects.get(pk=1458)
                aData['decanofirma'] = decanofirma = decano.persona.firmapersona_set.filter(status=True).order_by('-tipofirma').first()
                aData['url_path'] = url_path
                aData['eParticipante'] = eParticipante
                username = elimina_tildes(eUsuario.username)
                qrname = f'feria_qr_certificadoparticipacion_{eInscripcion.id}{eParticipante.solicitud.id}{eParticipante.id}'
                folder = os.path.join(os.path.join(path_folder, 'media', 'feria', 'certificados', 'participantes', username, 'participacion', ''))
                folder2 = os.path.join(os.path.join(path_folder, 'media', 'feria', 'certificados', 'participantes', username, 'qrcode', ''))
                os.makedirs(folder, exist_ok=True)
                os.makedirs(folder2, exist_ok=True)
                foldersave = f'feria/certificados/participantes/{username}/participacion/{qrname}.pdf'

                rutapdf = folder + qrname + '.pdf'
                aData['url_qr'] = rutaimg = folder2 + qrname + '.png'
                aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                if os.path.isfile(rutapdf):
                    os.remove(rutapdf)
                elif os.path.isfile(rutaimg):
                    os.remove(rutaimg)
                url = pyqrcode.create(f'{url_path}/media/feria/certificados/participantes/{username}/participacion/{qrname}.pdf')
                imageqr = url.png(rutaimg, 16, '#000000')
                aData['image_qrcode'] = f'{url_path}/media/feria/certificados/participantes/{username}/qrcode/{qrname}.png'
                valida, pdf, result = conviert_html_to_pdfsaveqrcertificadoferiaparticipacion2(
                    request,
                    'adm_feria/utileria/certificado.html',
                    {'pagesize': 'A4', 'data': aData}, folder, qrname + '.pdf'
                )
                if valida:
                    eParticipante.certificado = foldersave
                    eParticipante.save()
                    print(f'{index + 1}.- {eParticipante.inscripcion} ----> {eParticipante.certificado}')
            except Exception as ex:
                transaction.set_rollback(True, using='default')
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_error = f'({eInscripcion}   ocurrio el siguiente error {str(ex)} {err}'
                errores.append(msg_error)
    return errores

print("""
        ************************************************************************************************
        *                                                                                              *
        *                                   GENERACIÓN DE CERTIFICADOS                                 *
        *                                                                                              *
        ************************************************************************************************
        """)
errores  = generateCertificatesParticipants()
if len(errores) > 0:
    print('Ocurrieron errores al generar certificados:\n')
    for error in errores:
        print(error)
else:
    print('Se ejecutaron con exito la generación de certificados:')