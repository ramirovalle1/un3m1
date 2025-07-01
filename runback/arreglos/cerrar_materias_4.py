import io
import os
import sys
import xlsxwriter
import xlwt
import openpyxl
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

from inno.models import *
from sga.models import *
from sagest.models import *

def importar_cerrar_materias(carrera):
    with transaction.atomic():
        try:
            periodo = Periodo.objects.get(id=177)
            materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                              asignaturamalla__malla__carrera_id=carrera,
                                              fin__lte=datetime.now().date()).exclude(modeloevaluativo_id=27)
            for materia in materias:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia, matricula__bloqueomatricula=False,
                                                              matricula__retiradomatricula=False, matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(materiaasignada.matricula.inscripcion.persona)
                    if notas_de_moodle:
                        for notasmooc in notas_de_moodle:
                            campo = materiaasignada.campo(notasmooc[1].upper())
                            if not campo:
                                print('revisar curso moodle - ', materiaasignada.materia.id, 'idcursomoodle -',
                                      materiaasignada.materia.idcursomoodle)
                                continue
                            if type(notasmooc[0]) is Decimal:
                                if null_to_decimal(campo.valor) != float(notasmooc[0]):
                                    actualizar_nota_planificacion(materiaasignada.id, notasmooc[1].upper(),
                                                                  notasmooc[0])
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=notasmooc[0])
                                    auditorianotas.save()
                                    print('importacion exitosa - ', materiaasignada)

                            else:
                                if null_to_decimal(campo.valor) != float(0):
                                    actualizar_nota_planificacion(materiaasignada.id, notasmooc[1].upper(),
                                                                  notasmooc[0])
                                    auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                                    calificacion=0)
                                    auditorianotas.save()
                                    print('importacion exitosa - ', materiaasignada)

                    else:
                        for detallemodelo in materiaasignada.materia.modeloevaluativo.detallemodeloevaluativo_set.filter(
                                migrarmoodle=True):
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

def coordinacion4():
    for carrera in Materia.objects.filter(status=True, nivel__periodo_id=177, cerrado=False,
                                          asignaturamalla__malla__carrera__coordinacion=4).exclude(
        modeloevaluativo_id=27).values_list('asignaturamalla__malla__carrera_id', flat=True).distinct():
        importar_cerrar_materias(carrera)

#coordinacion4()
def actualizar_nivel_inscripcion_malla6():
    matriculas = Matricula.objects.filter(status=True, nivel__periodo_id=177, inscripcion__carrera_id__in=[160,132,140] )
    for matricula in matriculas:
        inscripcion = matricula.inscripcion
        print('ACTUALIZANDO- ', inscripcion.persona.cedula)
        inscripcion.actualizar_nivel()
        print('ACTUALIZADO')
    print('FIN')

actualizar_nivel_inscripcion_malla6()


