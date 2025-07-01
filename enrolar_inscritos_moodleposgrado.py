#!/usr/bin/env python
import os
import sys
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sagest.models import *
from moodle import moodle
from django.db import connections
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

try:
    cursor = connections['moodle_pos'].cursor()
    cursos = [227, 223]
    for idcurso in cursos:
        curso = CapEventoPeriodoIpec.objects.get(pk=idcurso)
        instructores = curso.capinstructoripec_set.filter(status=True)
        inscritos = CapInscritoIpec.objects.filter(status=True, capeventoperiodo_id=curso.id)
        for inscrito in inscritos:
            if inscrito.cancelo_rubro():
                for inst in instructores:
                    queryest = """
                            SELECT DISTINCT asi.userid, asi.roleid
                            FROM  mooc_role_assignments asi
                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID AND ASI.ROLEID=%s 
                            AND CON.INSTANCEID=%s AND asi.userid =%s
                                """ % (10, inst.idcursomoodle, inscrito.participante.idusermoodleposgrado)
                    cursor.execute(queryest)
                    rowest = cursor.fetchall()
                    if not rowest:
                        inst.crear_actualizar_estudiantes_curso(moodle, 1, inscrito.id)
                        print("%s Enrolado: %s - (%s)" % (curso,inscrito, inst))
except Exception as ex:
    print('error: %s' % ex)
