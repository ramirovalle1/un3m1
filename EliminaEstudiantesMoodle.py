#!/usr/bin/env python

import os
import sys
import warnings
warnings.filterwarnings('ignore', message='Unverified HTTPS request')
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from sga.models import *
from moodle import moodle

periodo = Periodo.objects.get(pk=126)
excludemateria = Materia.objects.values_list('id', flat=True).filter(status=True, nivel__periodo=periodo, asignaturamalla__nivelmalla_id__in=[7, 8], asignaturamalla__malla__carrera__coordinacion__id__in=[1]).distinct()
cursos = Materia.objects.filter(status=True, nivel__periodo=periodo).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
cursos = cursos.exclude(id__in=excludemateria)
for materia in cursos:

    from django.db import connections
    if materia.idcursomoodle:
        cursoid = materia.idcursomoodle
        idestudiantes = ""
        asignados = materia.materiaasignada_set.select_related().filter(status=True, retiramateria=False)
        matricula_ids = asignados.values_list("matricula_id", flat=True).filter(matricula__estado_matricula__in=[1, 3])
        if matricula_ids:
            print(materia)
            for x in asignados.exclude(matricula_id__in=matricula_ids).values_list('matricula__inscripcion__persona__idusermoodle', flat=False):
                idestudiantes += "%s," % x[0]

            docentes = materia.mis_profesores()
            for curpro in docentes:
                profesor = curpro.profesor
                if profesor and profesor.persona.usuario and not 'POR DEFINIR' in profesor.persona.nombres:
                    idestudiantes += "%s," % profesor.persona.idusermoodle

            cursor = connections['moodle_db'].cursor()
            queryest = """
                            SELECT DISTINCT asi.userid, asi.roleid
                            FROM  mooc_role_assignments asi
                            INNER JOIN MOOC_CONTEXT CON ON asi.CONTEXTID=CON.ID AND ASI.ROLEID=%s AND CON.INSTANCEID=%s AND asi.userid not in(%s0)
                    """ % (materia.nivel.periodo.rolestudiante, cursoid, idestudiantes)
            cursor.execute(queryest)
            rowest = cursor.fetchall()
            if rowest:
                for deluserest in rowest:
                    unrolest = moodle.UnEnrolarCurso(materia.nivel.periodo, 1, deluserest[1], deluserest[0], cursoid)
                    print('************ Eliminar Estudiante: *** %s' % deluserest[0])
