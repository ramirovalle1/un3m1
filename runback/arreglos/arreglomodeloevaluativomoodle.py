import os
import sys
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
from sga.models import *
from sagest.models import *

try:
    materiaget = Materia.objects.filter(cerrado=False, nivel__periodo__tipo__in=[3,4], nivel__modalidad__id=3).exclude(pk__in=[44465, 44467, 44467, 44467, 44471, 44471, 44471, 44470, 44470, 44470, 44473, 44473, 44473, 44480, 44483, 44483, 44483, 44491, 44491, 44491])

    for mat in materiaget:
        print("{} ({})".format(mat, mat.pk))
        evaluaciones = EvaluacionGenerica.objects.filter(materiaasignada__materia=mat)
        evaluaciones.delete()
        for maa in mat.asignados_a_esta_materia():
            maa.evaluacion()
            maa.notafinal = 0
            maa.save(actualiza=False)
        if mat.cronogramaevaluacionmodelo_set.exists():
            cronograma = mat.cronogramaevaluacionmodelo_set.all()[0]
            cronograma.materias.remove(mat)

    for mat in materiaget:
        for alumno in mat.asignados_a_esta_materia_moodle().filter(retiramateria=False):
            # Si alumno no tiene matricula bloqueada
            if alumno.matricula.bloqueomatricula is False:
                # Extraer datos de moodle
                if mat.notas_de_moodle(alumno.matricula.inscripcion.persona):
                    print(mat.notas_de_moodle(alumno.matricula.inscripcion.persona))
                for notasmooc in mat.notas_de_moodle(alumno.matricula.inscripcion.persona):
                    campo = alumno.campo(notasmooc[1].upper())
                    # if not alumno.matricula.bloqueomatricula:
                    if type(notasmooc[0]) is Decimal:
                        if null_to_decimal(campo.valor) != float(notasmooc[0]) or (
                                alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
                                                            calificacion=notasmooc[0])
                            auditorianotas.save()
                    else:
                        if null_to_decimal(campo.valor) != float(0) or (
                                alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
                            actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
                            auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
                            auditorianotas.save()

    # idsmaterias = []
    # for mat in materiaget:
    #     estudiantes = mat.asignados_a_esta_materia_moodle().filter(retiramateria=False)
    #     primerestudiante = estudiantes.filter(matricula__bloqueomatricula=False).first()
    #     bandera = True
    #     modelo_mood = ''
    #     modelo_sga = ''
    #     if primerestudiante:
    #         for notasmooc in mat.notas_de_moodle(primerestudiante.matricula.inscripcion.persona):
    #             bandera = primerestudiante.evaluacion_generica().filter(
    #                 detallemodeloevaluativo__nombre=notasmooc[1].upper()).exists()
    #             if not bandera:
    #                 for notasmoocstr in mat.notas_de_moodle(primerestudiante.matricula.inscripcion.persona):
    #                     modelo_mood += "{}, ".format(notasmoocstr[1])
    #                 for notassga in primerestudiante.evaluacion_generica():
    #                     modelo_sga += "{}, ".format(notassga.detallemodeloevaluativo.nombre)
    #                 print(u"Modelo Evaluativo extraido es diferente al modelo existente\nMoodle:\n{}\nSGA:\n{}".format(
    #                     modelo_mood, modelo_sga))
    #                 idsmaterias.append(mat.id)
    # print(idsmaterias)
    # print(len(idsmaterias))

    # materiaasignada = MateriaAsignada.objects.filter(status=True, retiramateria=False, materia__in=materiaget.values_list('id', flat=True))
    # modelogen = EvaluacionGenerica.objects.filter(materiaasignada__in=materiaasignada.values_list('id',flat=True)).values('detallemodeloevaluativo__nombre', 'detallemodeloevaluativo__modelo__id', 'detallemodeloevaluativo__modelo__nombre', 'materiaasignada__materia__modeloevaluativo__id', 'materiaasignada__materia__modeloevaluativo__nombre', 'id')
    # print(materiaget.count())
    # print(materiaasignada.count())
    # print(modelogen.count())
    # print(modelogen.query)
    # print('----------------------')
    # print(modelogen.filter(valor=0).count())
except Exception as ex:
    print(ex)
    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))



