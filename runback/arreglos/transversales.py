import os
import sys
import io
import xlsxwriter
import xlwt
import openpyxl
import xlwt
from xlwt import *
from django.http import HttpResponse
from xlwt import *

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()

from django.http import HttpResponse
from settings import MEDIA_ROOT, BASE_DIR
from xlwt import easyxf, XFStyle
from sga.adm_criteriosactividadesdocente import asistencia_tutoria
from inno.models import *
from sga.models import *
from sagest.models import *
from balcon.models import *



def calificacion_transversales_en_linea():
    try:
        periodo = Periodo.objects.get(id=177)
        asignaturas = DetalleGrupoAsignatura.objects.values_list('asignatura_id', flat=True).filter(status=True,
                                                                                                    grupo_id__in=[1, 2,
                                                                                                                  3])

        abrirm = Materia.objects.filter(status=True, nivel__periodo_id=177, cerrado=True,
                                        asignaturamalla__asignatura_id__in=asignaturas, modeloevaluativo_id=27,
                                        asignaturamalla__malla__carrera__coordinacion__in=[4])

        # for mat in abrirm:
        #   mat.cerrado = False
        #  mat.save()
        abrirm.update(cerrado=False)

        materias = Materia.objects.filter(status=True, nivel__periodo_id=177, cerrado=False,
                                          asignaturamalla__asignatura_id__in=asignaturas, modeloevaluativo_id=27,
                                          asignaturamalla__malla__carrera__coordinacion__in=[4])

        for materia in materias:
            idcursomoodle = materia.idcursomoodle
            materiasasignadas = MateriaAsignada.objects.filter(status=True,
                                                               matricula__nivel__periodo=periodo,
                                                               materia=materia,
                                                               matricula__bloqueomatricula=False,
                                                               matricula__retiradomatricula=False, materia__status=True,
                                                               matricula__status=True,
                                                               matricula__inscripcion__carrera__modalidad__in=[3])

            cursor = connections['moodle_db'].cursor()
            for materiaasignada in materiasasignadas:
                # guardo_nota = False
                usuario = materiaasignada.matricula.inscripcion.persona.usuario.username
                # SE NECESITA EL ID DE CURSO MOODLE
                sql = """
                                                    SELECT ROUND(nota.finalgrade,2), UPPER(gc.fullname)
                                                            FROM mooc_grade_grades nota
                                                    INNER JOIN mooc_grade_items it ON nota.itemid=it.id AND courseid=%s AND itemtype='category'
                                                    INNER JOIN mooc_grade_categories gc ON gc.courseid=it.courseid AND gc.id=it.iteminstance AND gc.depth=2
                                                    INNER JOIN mooc_user us ON nota.userid=us.id
                                                    WHERE us.username = '%s' and UPPER(gc.fullname)='RE'
                                                    ORDER BY it.sortorder
                                                """ % (str(idcursomoodle), usuario)

                cursor.execute(sql)
                results = cursor.fetchall()
                if results:
                    for notasmooc in results:
                        campo = materiaasignada.campo(notasmooc[1].upper())
                        if not campo:
                            print('revisar curso moodle - ', materiaasignada.materia.id, 'idcursomoodle -',
                                  materiaasignada.materia.idcursomoodle)
                            continue
                        if type(notasmooc[0]) is Decimal:
                            if null_to_decimal(campo.valor) != float(notasmooc[0]):
                                actualizar_nota_planificacion(materiaasignada.id, notasmooc[1].upper(), notasmooc[0])
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                calificacion=notasmooc[0])
                                auditorianotas.save()
                                print('importacion exitosa - ', materiaasignada)

                        else:
                            if null_to_decimal(campo.valor) != float(0):
                                actualizar_nota_planificacion(materiaasignada.id, notasmooc[1].upper(), notasmooc[0])
                                auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                                auditorianotas.save()
                                print('importacion exitosa - ', materiaasignada)

                else:
                    detallemodelo = DetalleModeloEvaluativo.objects.get(pk=125)
                    campo = materiaasignada.campo(detallemodelo.nombre)
                    actualizar_nota_planificacion(materiaasignada.id, detallemodelo.nombre, 0)
                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                    auditorianotas.save()

            for asig in materia.asignados_a_esta_materia():
                asig.cerrado = True
                asig.save(actualiza=False)
                asig.actualiza_estado()
                asig.cierre_materia_asignada()
            # for asig in materia.asignados_a_esta_materia():
            #     asig.cierre_materia_asignada()

            materia.cerrado = True
            materia.fechacierre = datetime.now().date()
            materia.save()
            print('PROCESO FINALIZADO')






    except Exception as ex:
        msg = ex.__str__()

        textoerror = '{} Linea:{}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
        print(textoerror)
        print(msg)


calificacion_transversales_en_linea()


