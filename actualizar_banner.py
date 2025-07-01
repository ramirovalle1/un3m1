
import base64
import os
import sys
from moodle.moodle import ActualizarBannerCurso
from settings import SITE_STORAGE
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import  Materia, Carrera, Periodo, AsignaturaMalla

from django.db import transaction

def migrar_banner_carrera(id_periodo, id_carrera,banner_image_path,image_filename):
    try:
        eCarrera = Carrera.objects.get(pk=id_carrera)
        ePeriodo = Periodo.objects.get(pk=id_periodo)
        eAsignaturaMalla= AsignaturaMalla.objects.values_list('id',flat=True).filter(status=True,malla__carrera=eCarrera, vigente=True)
        materias = Materia.objects.filter(status=True, asignaturamalla__in = eAsignaturaMalla,nivel__periodo=ePeriodo)
        count=0
        for materia in materias:
            count+=1
            print(f"[{count}]/[{materias.count()}] ")
            if materia.coordinacion().id == 9:
                tipourl = 2
            else:
                tipourl = 1

            with open(banner_image_path, 'rb') as imagen_archivo:
                # Convertir la imagen en una cadena de base64
                ActualizarBannerCurso(materia.idcursomoodle, ePeriodo, tipourl, imagen_archivo, image_filename)
            print(f"banner actualizado: {materia}")
            print(f"id curso moodle: {materia.idcursomoodle}")
    except Exception as ex:
        transaction.set_rollback(True)

carrera = 143
periodo = 177 #PERIODO ACTUAL
output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', ''))#verificar que alli esta la imagen
banner_image_path = f"{output_folder}01.jpg"  # Reemplaza con la ruta al archivo de imagen
image_filename = "01.jpg"  # Reemplaza con el nombre del archivo de imagen
migrar_banner_carrera(periodo,carrera,banner_image_path,image_filename)