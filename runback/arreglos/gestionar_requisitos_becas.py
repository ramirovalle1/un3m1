#!/usr/bin/env python
import os
import sys

csv_filepathname3 = "problemas2021_corregido_g6.csv"
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
import sys
from datetime import datetime

from django.db import transaction

from sga.funciones import lista_mejores_promedio_beca_v3, asignar_orden_portipo_beca, listado_incripciones_reconocimiento_academico, lista_discapacitado_beca, lista_deportista_beca, lista_migrante_exterior_beca, lista_etnia_beca, lista_gruposocioeconomico_beca
from sga.models import BecaTipo, Inscripcion, PreInscripcionBeca, Periodo, Matricula
import warnings
from settings import SITE_STORAGE, DEBUG
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
from PyPDF2 import PdfFileReader


def get_files(path):
    """ Generator que retorna lista de archivos.

    @param path: Path al directorio a examinar.
    @yield Un nombre de archivo con path completo.
    """
    for archivo in os.listdir(path):
        path_completo = os.path.join(path, archivo)
        if os.path.isdir(path_completo):
            for f in get_files(path_completo):
                yield f
        elif os.path.isfile(path_completo):
            yield path_completo


data_requisitos = {
    7: 'No ser contratista incumplido o adjudicatario fallido con el Estado'
}

def get_d(path_folder):
    for file in get_files(path_folder):
        temp = open(file, 'rb')
        PDF_read = PdfFileReader(temp, strict=False)
        first_page = PDF_read.getPage(0)
        texto = first_page.extractText()
        listado_palabras = texto.split('\n')
        listado_palabras2 = texto.replace('\n', '').replace(',', '').replace('.', '').split(' ')
        #Requisito de No ser contratista incumplido o adjudicatario fallido con el Estado

        if len(listado_palabras) > 2:
            if data_requisitos[7] == listado_palabras[2]:
                print([palabra for palabra in listado_palabras if palabra.isdigit()])

        if len(listado_palabras2) > 2:
            print(file)
            print(listado_palabras2)
            print([palabra.replace(',', '') for palabra in listado_palabras2 if (palabra.isdigit() or palabra.replace(',', '').isdigit()) and len(palabra.replace(',', '')) > 9])
if DEBUG:
    path_folder = f"{SITE_ROOT}/media/archivo_beca_requisito/"
else:
    path_folder = f"{SITE_STORAGE}/media/archivo_beca_requisito/"


def migrar_ruta_requisitos_preinscripcion(path_folder):
    folders =[ruta for ruta in get_files(path_folder)]
    preinscripciones = PreInscripcionBeca.objects.filter(periodo_id=119)
    for preinscripcion in preinscripciones:
        username = preinscripcion.inscripcion.persona.usuario.username
        listado_busqueda = [s for s in folders if s.__contains__(username)]
        for file in listado_busqueda:
            temp = open(file, 'rb')
            PDF_read = PdfFileReader(temp, strict=False)
            first_page = PDF_read.getPage(0)
            texto = first_page.extractText()
            if texto.find('CERTIFICADO DE SER BECARIO') != -1:
                requisito = preinscripcion.preinscripcionbecarequisito_set.filter(detallerequisitobeca__requisitobeca_id=5).first()
                if requisito is not None:
                    requisito.archivo = file.split('/media/')[1]
                    requisito.save()
                    print('Archivo es de Becados externo', file)
            elif texto.find('REGISTRO DE NO TENER IMPEDIMENTO LEGAL') != -1:
                requisito = preinscripcion.preinscripcionbecarequisito_set.filter(detallerequisitobeca__requisitobeca_id=6).first()
                if requisito is not None:
                    requisito.archivo = file.split('/media/')[1]
                    requisito.save()
                    print('Archivo es de impedimento legal', file)
            elif texto.find('Sistema Oficial de Contratación Pública') != -1:
                requisito = preinscripcion.preinscripcionbecarequisito_set.filter(detallerequisitobeca__requisitobeca_id=7).first()
                if requisito is not None:
                    requisito.archivo = file.split('/media/')[1]
                    requisito.save()
                    print('Archivo es de Pagos a porveedores incumplimiento', file)
#get_d(path_folder)
migrar_ruta_requisitos_preinscripcion(path_folder)