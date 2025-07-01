import concurrent.futures
import os
import sys

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

def importar_calificaciones_derecho():
    print("funcion 1")
    periodo = Periodo.objects.get(id=224)
    carrera_id=126
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3, asignaturamalla__malla__carrera_id=carrera_id ).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)


def importar_calificaciones_economia():
    print("funcion 2")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 128
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)


def importar_calificaciones_turismo():
    print("funcion 3")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 134
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)


def importar_calificaciones_comunicacion():
    print("funcion 4")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 131
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: ' + msg)


def importar_calificaciones_psicologia():
    print("funcion 5")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 132
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)


def importar_calificaciones_trabajosocial():
    print("funcion 6")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 130
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)



def importar_calificaciones_tics():
    print("funcion 7")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 133
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)

def importar_calificaciones_eduinicial():
    print("funcion 8")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 127
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)

def importar_calificaciones_edubasica():
    print("funcion 9")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 135
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)

def importar_calificaciones_pedagogia():
    print("funcion 10")
    periodo = Periodo.objects.get(id=224)
    carrera_id = 129
    materias = Materia.objects.filter(status=True, nivel__periodo=periodo, cerrado=False,
                                      asignaturamalla__malla__modalidad_id=3,
                                      asignaturamalla__malla__carrera_id=carrera_id).exclude(nivel__id__in=[1516, 1517])

    for materia in materias:
        with transaction.atomic():
            try:
                materiasasignadas = MateriaAsignada.objects.filter(status=True, materia=materia,
                                                                   matricula__bloqueomatricula=False,
                                                                   matricula__retiradomatricula=False,
                                                                   matricula__status=True, retiramateria=False)

                for materiaasignada in materiasasignadas:
                    # guardo_nota = False
                    notas_de_moodle = materiaasignada.materia.notas_de_moodle(
                        materiaasignada.matricula.inscripcion.persona)
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


            except Exception as ex:
                transaction.set_rollback(True)
                msg = ex.__str__()
                print('ERROR: '+msg)





if __name__ == "__main__":
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # Submit de cada función al ThreadPoolExecutor
        future_1 = executor.submit(importar_calificaciones_derecho)
        future_2 = executor.submit(importar_calificaciones_economia)
        future_3 = executor.submit(importar_calificaciones_turismo)
        future_4 = executor.submit(importar_calificaciones_comunicacion)
        future_5 = executor.submit(importar_calificaciones_psicologia)
        future_6 = executor.submit(importar_calificaciones_trabajosocial)
        future_7 = executor.submit(importar_calificaciones_tics)
        future_8 = executor.submit(importar_calificaciones_eduinicial)
        future_9 = executor.submit(importar_calificaciones_edubasica)
        future_10 = executor.submit(importar_calificaciones_pedagogia)

