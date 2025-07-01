import sys
import os


SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.funciones import variable_valor
CALCULAR_ASISTENCIA_PERIODO_ID = variable_valor('CALCULAR_ASISTENCIA_PERIODO_ID')
if CALCULAR_ASISTENCIA_PERIODO_ID > 0:
    from sga.models import Matricula, MateriaAsignada
    matr_pre = Matricula.objects.filter(status=True, nivel__periodo_id=CALCULAR_ASISTENCIA_PERIODO_ID,
                                    inscripcion__carrera__coordinacion__lte=5,
                                    inscripcion__carrera__modalidad__in=[1, 2]).values_list('id', flat=True).distinct()

    matr_niv = Matricula.objects.filter(status=True, nivel__periodo_id=CALCULAR_ASISTENCIA_PERIODO_ID, inscripcion__carrera_id=223,
                                    inscripcion__carrera__coordinacion=9).values_list('id', flat=True).distinct()
    matr = matr_pre | matr_niv
    for matricula in matr:
        for materiaasignada in MateriaAsignada.objects.filter(status=True, matricula_id=matricula):
            materiaasignada.save(actualiza=True)

