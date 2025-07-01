import os
import sys

import openpyxl
# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
from django.db import transaction

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
# #
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=126)
#     for dis in distributivo:
#         profmateria = ProfesorMateria.objects.filter(profesor=dis.profesor_id, materia__nivel__periodo=126,
#                                        activo=True, tipoprofesor__id__in=[12, 11, 6, 7, 1, 2, 3, 14 ])
#         # cabhoras = profmateria.aggregate(valor=Sum('hora'))['valor']
#         # horasact = dis.horasdocencia
#         # if cabhoras != horasact and horasact != 0:
#         # print(dis.id)
#         dis.actualiza_hijos()
#         dis.resumen_evaluacion_acreditacion().actualizar_resumen()
#
# except Exception as ex:
#     print(ex)
#
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=126)
#     for dis in distributivo:
#         profmateria = ProfesorMateria.objects.filter(profesor=dis.profesor_id, materia__nivel__periodo=126, activo=True, tipoprofesor__id=11, materia__asignaturamalla__malla__carrera__modalidad=3)
#         for prof in profmateria:
#             print(prof.id)
#             # prof.tipoprofesor_id = 14
#             # prof.save()
#
# except Exception as ex:
#     print(ex)

#F
# try:
#     profmateria = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=126, activo=True, tipoprofesor__id=11, materia__asignaturamalla__malla__carrera__modalidad=3)
#     print("TOTAL: {}".format(len(profmateria)))
#     cont = 0
#     for prof in profmateria:
#         prof.tipoprofesor_id=14
#         prof.save()
#         cont += 1
#         print("{} - {}/{}".format(prof.__str__(), cont,len(profmateria)))
#
#
#
# except Exception as ex:
#     print(ex)


# try:
#     clase = Clase.objects.filter(status=True, materia__nivel__periodo=126, activo=True, tipoprofesor__id=11, materia__asignaturamalla__malla__carrera__modalidad=3)
#     print("TOTAL: {}".format(len(clase)))
#     cont = 0
#     for clas in clase:
#         clas.tipoprofesor_id=14
#         clas.save()
#         cont += 1
#         print("{} - {}/{}".format(clas.__str__(), cont,len(clase)))
#
#
#
# except Exception as ex:
#     print(ex)

##turnos salud
# try:
#     clase = Clase.objects.filter(status=True, materia__nivel__periodo=126, activo=True,
#                                  materia__asignaturamalla__malla__carrera__id__in=[1, 110, 111, 3, 112], turno__sesion__id__in=[1, 4])
#     # for clas in clase:
#     #     print(clas.id)
#     print("TOTAL: {}".format(len(clase)))
#     for clas in clase:
#         if clas.turno.sesion.id == 1:
#
#             if clas.turno_id == 1:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=108, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                 # if not clas.turno_id == 108:
#                     clas.turno_id = 108
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 2:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=109, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 109
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 3:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=110, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 110
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 4:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=111, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 111
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 232:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=111, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 111
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 5:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=112, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 112
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 233:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=112, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 112
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 6:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=113, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 113
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 55:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=114, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 114
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 373:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=114, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 114
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 56:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=115, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 115
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 291:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=115, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 115
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 301:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=116, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 116
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 302:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=117, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 117
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 102:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=118, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 118
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 374:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=118, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 118
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 103:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=118, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 118
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 303:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=118, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 118
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#
#         if clas.turno.sesion.id == 4:
#
#             if clas.turno_id == 67:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=132, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 132
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 59:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=133, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 133
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 60:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=134, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 134
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 61:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=135, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 135
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 249:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=135, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 135
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 62:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=136, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 136
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 250:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=136, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 136
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 63:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=137, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 137
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 34:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=120, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 120
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 359:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=120, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 120
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 35:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=121, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 121
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 292:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=121, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 121
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 362:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=122, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 122
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 363:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=123, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 123
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 38:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=124, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                     clas.turno_id = 124
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 364:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=124, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 124
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 39:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=124, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 124
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#             if clas.turno_id == 308:
#                 if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=124, dia=clas.dia,
#                                             profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#                     clas.turno_id = 124
#                     clas.save()
#                     print(u"%s," % (clas.id))
#
#
# except Exception as ex:
#     print(ex)

# #materia inicio fin
# try:
#     materias = Materia.objects.filter(status=True,nivel__periodo=126).exclude(asignaturamalla__malla__carrera__id__in = [1, 3, 110, 111], asignaturamalla__nivelmalla__id__in=[7, 8])
#     # pm = Materia.objects.filter(status=True,nivel__periodo=126,asignaturamalla__nivelmalla__id__in=[7, 8], asignaturamalla__malla__carrera__id__in = [1, 3, 110, 111])
#     for materia in materias:
#         materia.inicio = '2022-05-30'
#         materia.fin = '2022-09-30'
#         materia.fechafinasistencias = '2022-09-18'
#         materia.save()
#         print(u"%s," % (materia.id))
# except Exception as ex:
#     print(ex)
# print("fin")
#
#
# #profesormateria inicio fin
# try:
#     profesoresmat = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=126).exclude(materia__asignaturamalla__malla__carrera__id__in = [1, 3, 110, 111], materia__asignaturamalla__nivelmalla__id__in=[7, 8])
#     for prof in profesoresmat:
#         prof.desde = '2022-05-30'
#         prof.hasta = '2022-09-30'
#         prof.save()
#         print(u"%s," % (prof.id))
# except Exception as ex:
#     print(ex)
# print("fin")
#



#horario inicio fin
# try:
#     clases = Clase.objects.filter(status=True, materia__nivel__periodo=126).exclude(materia__asignaturamalla__malla__carrera__id__in = [1, 3, 110, 111], materia__asignaturamalla__nivelmalla__id__in=[7, 8])
#     for clase in clases:
#         clase.inicio = '2022-05-30'
#         clase.fin = '2022-09-18'
#         clase.save()
#         print(u"%s," % (clase.id))
# except Exception as ex:
#     print(ex)
# print("fin")




#
# ##turnos semipresenciales
# try:
#     clase = Clase.objects.filter(status=True, materia__nivel__periodo=126, activo=True,
#                                  materia__asignaturamalla__malla__carrera__id__in=[160,149,187], turno__sesion__id=7)
#     # for clas in clase:
#     #     print(clas.id)
#     print("TOTAL: {}".format(len(clase)))
#     for clas in clase:
#
#         if clas.turno_id == 331:
#             if not Clase.objects.filter(status=True, materia=clas.materia, turno_id=445, dia=clas.dia,
#                                  profesor=clas.profesor, tipoprofesor=clas.tipoprofesor, inicio=clas.inicio, fin=clas.fin, aula=clas.aula).exists():
#
#                 clas.turno_id = 445
#                 clas.save()
#                 print(u"%s,"%(clas.id))
#
# except Exception as ex:
#     print(ex)
#



  # print(dis.horasdocencia)
#         # if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=118, distributivo = dis).exists():
#         #     distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=118,
#         #                                               criteriodocenciaperiodo__periodo=119,
#         #                                               distributivo= dis)
#         #     # print(u"(%s) doc %s - %s - %s - %s"%(dis.id,distant,distant.criteriodocenciaperiodo.criterio, distant.fecha_creacion,distant.usuario_creacion))
#         #     print(u"%s,"%(dis.id))
#             # distant.delete()


#criterio2
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status = True, periodo_id=126, profesor_id=205)
#     for dis in distributivo:
#         if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=126, distributivo = dis).exists():
#             distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=126, distributivo= dis)
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=126, distributivo_id=dis).exists():
#                 horas = distant.horas
#                 porcprincipal = null_to_decimal(horas * 60 / 100, 0)
#                 porcrit1= null_to_decimal(porcprincipal * 60 / 100, 0)
#                 detdistri = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=681,
#                     horas=porcrit1
#                 )
#                 detdistri.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=126, distributivo_id=dis).exists():
#                 horas = distant.horas
#                 porcprincipal = null_to_decimal(horas * 60 / 100, 0)
#                 porcrit2= null_to_decimal(porcprincipal * 25 / 100, 0)
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=680,
#                     horas=porcrit2
#                 )
#                 detdistri2.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=126, distributivo_id=dis).exists():
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=678,
#                     horas=1
#                 )
#                 detdistri2.save()
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=126, distributivo_id=dis).exists():
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=distant.distributivo_id,
#                     criteriodocenciaperiodo_id=674,
#                     horas=1
#                 )
#                 detdistri2.save()
#
#         for detalledistributivo in DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__periodo=126, distributivo=dis).order_by('-criteriodocenciaperiodo__criterio_id'):
#             actividad1 = None
#             actividad2 = None
#             actividad3 = None
#             actividad4 = None
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 122:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=122).exists():
#                             actividad1 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PLANIFICAR Y ACTUALIZAR CONTENIDOS DE CLASES, SEMINARIOS, TALLERES, ENTRE OTROS.",
#                                                                       desde=convertir_fecha('31-05-2022'),
#                                                                       hasta=convertir_fecha('30-09-2022'),
#                                                                       horas=distant.horas,
#                                                                       vigente=True)
#                             actividad1.save()
#                             print(u"Inserta atividad 1 %s" % actividad1)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 121:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=121).exists():
#                             actividad2 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PREPARAR, ELABORAR, APLICAR Y CALIFICAR EXÁMENES, TRABAJOS Y PRÁCTICAS",
#                                                                       desde=convertir_fecha('31-05-2022'),
#                                                                       hasta=convertir_fecha('30-09-2022'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad2.save()
#                             print(u"Inserta atividad 2 %s" % actividad2)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 124:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=124).exists():
#                             actividad3 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"ORIENTAR Y ACOMPAÑAR A ESTUDIANTES A TRAVÉS DE TUTORÍAS ACADÉMICAS DE FORMA PRESENCIAL Y/O EN LÍNEA.",
#                                                                       desde=convertir_fecha('31-05-2022'),
#                                                                       hasta=convertir_fecha('30-09-2022'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad3.save()
#                             print(u"Inserta atividad 3 %s" % actividad3)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 123:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=123).exists():
#                             actividad4 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"DISEÑAR Y ELABORAR MATERIAL DIDÁCTICO, GUÍAS DOCENTES O SYLLABUS",
#                                                                       desde=convertir_fecha('31-05-2022'),
#                                                                       hasta=convertir_fecha('30-09-2022'),
#                                                                       horas=1,
#                                                                       vigente=True)
#                             actividad4.save()
#                             print(u"Inserta atividad 4 %s" % actividad4)
# #
# #
# #
# #
# #
# #
# except Exception as ex:
#     print(ex)


#PROFESORES
# try:
#     profesor = Profesor.objects.filter(status=True,id__in=[1148,
# 156,
# 602,
# 912,
# 591,
# 1060,
# 37,
# 258,
# 21,
# 338,
# 594,
# 193,
# 234,
# 622,
# 655,
# 160,
# 585,
# 2078,
# 155,
# 53,
# 263,
# 82,
# 225,
# 368,
# 131,
# 226,
# 213,
# 93,
# 1787,
# 921,
# 966,
# 120,
# 31,
# 195,
# 15,
# 619,
# 81,
# 44,
# 250,
# 5,
# 642,
# 67,
# 941,
# 11,
# 118,
# 74,
# 200,
# 245,
# 915,
# 129,
# 80,
# 868,
# 592,
# 268,
# 628,
# 260,
# 310,
# 205,
# 23,
# 621,
# 371,
# 251,
# 84,
# 577,
# 38,
# 907,
# 909,
# 2046,
# 56,
# 1122,
# 306,
# 183,
# 136,
# 147,
# 624,
# 123,
# 325,
# 117,
# 202,
# 73,
# 336,
# 157,
# 608,
# 361,
# 32,
# 1790,
# 171,
# 1459,
# 26,
# 221,
# 1494,
# 138,
# 627,
# 584,
# 278,
# 231,
# 358,
# 327,
# 946,
# 83,
# 89,
# 208,
# 52,
# 256,
# 119,
# 1450,
# 345,
# 232,
# 581,
# 43,
# 339,
# 145,
# 126,
# 113,
# 273,
# 880,
# 215,
# 197,
# 90,
# 14,
# 1127,
# 176,
# 218,
# 671,
# 1058,
# 2076,
# 906,
# 604,
# 189,
# 965,
# 220,
# 253,
# 765,
# 184,
# 164,
# 194,
# 62,
# 178,
# 242,
# 905,
# 45,
# 1639,
# 216,
# 947,
# 620,
# 143,
# 40,
# 939,
# 229,
# 170,
# 1637,
# 142,
# 16,
# 22,
# 243,
# 366,
# 352,
# 149,
# 582,
# 4,
# 810,
# 2077,
# 1759,
# 108,
# 2075,
# 214,
# 1704,
# 370,
# 235,
# 198,
# 224,
# 614,
# 20,
# 233,
# 173,
# 1149,
# 241,
# 1834,
# 903,
# 644,
# 219,
# 1174,
# 580,
# 9,
# 942,
# 19,
# 174,
# 167,
# 340,
# 159,
# 938,
# 888,
# 49,
# 911,
# 182,
# 191,
# 51,
# 954,
# 814,
# 222,
# 230,
# 625,
# 1622,
# 626,
# 154,
# 1142,
# 667,
# 640,
# 1140,
# 172,
# 139,
# 2004,
# 1137,
# 13,
# 1717,
# 103,
# 858,
# 244,
# 590,
# 1451,
# 78,
# 196,
# 578,
# 1133,
# 187,
# 593,
# 259,
# 606])
#     for pro in profesor:
#         distributivo = ProfesorDistributivoHoras(profesor_id=pro.id,
#                                                  periodo_id=156,
#                                                  dedicacion=pro.dedicacion,
#                                                  horasdocencia=0,
#                                                  horasinvestigacion=0,
#                                                  horasgestion=0,
#                                                  horasvinculacion=0,
#                                                  coordinacion=pro.coordinacion,
#                                                  categoria=pro.categoria,
#                                                  nivelcategoria=pro.nivelcategoria,
#                                                  cargo=pro.cargo,
#                                                  nivelescalafon=pro.nivelescalafon)
#         distributivo.save()
# except Exception as ex:
#     print(ex)


#PROCESO COPIAR DISTRIBUTIVO
#
with transaction.atomic():
    try:

        distributivoant = ProfesorDistributivoHoras.objects.filter(status = True, periodo_id=156)

        for disant in distributivoant:
            distributivo = ProfesorDistributivoHoras(profesor_id=disant.profesor_id,
                                                             periodo_id=191, #191
                                                             dedicacion=disant.dedicacion,
                                                             horasdocencia=disant.horasdocencia,
                                                             horasinvestigacion=disant.horasinvestigacion,
                                                             horasgestion=disant.horasgestion,
                                                             horasvinculacion=disant.horasvinculacion,
                                                             coordinacion=disant.coordinacion,
                                                             categoria=disant.categoria,
                                                             nivelcategoria=disant.nivelcategoria,
                                                             cargo=disant.cargo,
                                                             nivelescalafon=disant.nivelescalafon)
            distributivo.save()
        # #
        #
        criteriosantdoc = CriterioDocenciaPeriodo.objects.filter(status=True, periodo_id=156)

        for crit in criteriosantdoc:
            if not CriterioDocenciaPeriodo.objects.filter(status=True, criterio_id=crit.criterio_id, periodo_id=191).exists():
                ncriterio= CriterioDocenciaPeriodo(
                    criterio_id=crit.criterio_id,
                    periodo_id = 191, #191
                    minimo = crit.minimo,
                    maximo = crit.maximo,
                    actividad_id = crit.actividad_id)
                ncriterio.save()
        #
        #
        criteriosantinv = CriterioInvestigacionPeriodo.objects.filter(status=True, periodo_id=156)

        for crit in criteriosantinv:
            if not CriterioInvestigacionPeriodo.objects.filter(status=True, criterio_id=crit.criterio_id, periodo_id=191).exists():
                ncriterio= CriterioInvestigacionPeriodo(
                    criterio_id=crit.criterio_id,
                    periodo_id = 191, #191
                    minimo = crit.minimo,
                    maximo = crit.maximo,
                    actividad_id = crit.actividad_id)
                ncriterio.save()
        #
        criteriosantgest = CriterioGestionPeriodo.objects.filter(status=True, periodo_id=156)

        for crit in criteriosantgest:
            if not CriterioGestionPeriodo.objects.filter(status=True, criterio_id=crit.criterio_id, periodo_id=191).exists():
                ncriterio= CriterioGestionPeriodo(
                    criterio_id=crit.criterio_id,
                    periodo_id = 191, #191
                    minimo = crit.minimo,
                    maximo = crit.maximo,
                    actividad_id = crit.actividad_id)
                ncriterio.save()


        #

        detalleante = DetalleDistributivo.objects.filter(status=True, distributivo__periodo=156)
        for detalle in detalleante:
            if  ProfesorDistributivoHoras.objects.filter(status=True, profesor_id= detalle.distributivo.profesor_id, periodo_id=191).exists():
                distriact = ProfesorDistributivoHoras.objects.get(status=True, profesor_id= detalle.distributivo.profesor_id, periodo_id=191)

                if detalle.criteriodocenciaperiodo:
                    if CriterioDocenciaPeriodo.objects.filter(status=True, periodo_id=191, criterio=detalle.criteriodocenciaperiodo.criterio).exists():
                        criteriodocencia = CriterioDocenciaPeriodo.objects.get(status=True, periodo_id=191, criterio=detalle.criteriodocenciaperiodo.criterio)

                        if criteriodocencia.criterio.id == 118:
                            if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio=detalle.criteriodocenciaperiodo.criterio, distributivo__profesor_id=detalle.distributivo.profesor_id, distributivo__periodo_id=191).exists():
                                detalledis = DetalleDistributivo(distributivo_id=distriact.id,
                                                                 criteriodocenciaperiodo=criteriodocencia,
                                                                 horas=0)
                                detalledis.save()

                                for act in ActividadDetalleDistributivo.objects.filter(criterio=detalle):
                                    if not ActividadDetalleDistributivo.objects.filter(criterio=detalledis).exists():
                                        actividad1 = ActividadDetalleDistributivo(criterio=detalledis,
                                                                                  nombre=criteriodocencia.criterio.nombre,
                                                                                  desde=convertir_fecha('01-10-2022'),
                                                                                  hasta=convertir_fecha('24-11-2022'),
                                                                                  horas=0,
                                                                                  vigente=True)
                                        actividad1.save()

                        else:
                            if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio=detalle.criteriodocenciaperiodo.criterio, distributivo__profesor_id= detalle.distributivo.profesor_id, distributivo__periodo_id=191).exists():
                                detalledis = DetalleDistributivo(distributivo_id=distriact.id,
                                                                         criteriodocenciaperiodo=criteriodocencia,
                                                                         horas=detalle.horas)
                                detalledis.save()

                                for act in ActividadDetalleDistributivo.objects.filter(criterio=detalle):
                                    if not ActividadDetalleDistributivo.objects.filter(criterio=detalledis).exists():
                                        actividad1 = ActividadDetalleDistributivo(criterio=detalledis,
                                                                                            nombre=criteriodocencia.criterio.nombre,
                                                                                            desde=convertir_fecha('01-10-2022'),
                                                                                            hasta=convertir_fecha('24-11-2022'),
                                                                                            horas=detalle.horas,
                                                                                            vigente=True)
                                        actividad1.save()



                if detalle.criterioinvestigacionperiodo:
                    if CriterioInvestigacionPeriodo.objects.filter(status=True, periodo_id=191, criterio=detalle.criterioinvestigacionperiodo.criterio).exists():
                        criterioinvestigacion = CriterioInvestigacionPeriodo.objects.get(status=True, periodo_id=191, criterio=detalle.criterioinvestigacionperiodo.criterio)
                        if not DetalleDistributivo.objects.filter(status=True, criterioinvestigacionperiodo__criterio=detalle.criterioinvestigacionperiodo.criterio, distributivo__profesor_id=detalle.distributivo.profesor_id, distributivo__periodo_id=191).exists():
                            detalledis = DetalleDistributivo(distributivo_id=distriact.id,
                                                             criterioinvestigacionperiodo=criterioinvestigacion,
                                                             horas=detalle.horas)
                            detalledis.save()

                            for act in ActividadDetalleDistributivo.objects.filter(criterio=detalle):
                                if not ActividadDetalleDistributivo.objects.filter(criterio=detalledis).exists():
                                    actividad1 = ActividadDetalleDistributivo(criterio=detalledis,
                                                                              nombre=criterioinvestigacion.criterio.nombre,
                                                                              desde=convertir_fecha('01-10-2022'),
                                                                              hasta=convertir_fecha('24-11-2022'),
                                                                              horas=detalle.horas,
                                                                              vigente=True)
                                    actividad1.save()
                #
                if detalle.criteriogestionperiodo:
                    if CriterioGestionPeriodo.objects.filter(status=True, periodo_id=191, criterio=detalle.criteriogestionperiodo.criterio).exists():
                        criteriogestion = CriterioGestionPeriodo.objects.get(status=True, periodo_id=191, criterio=detalle.criteriogestionperiodo.criterio)

                        if not DetalleDistributivo.objects.filter(status=True, criteriogestionperiodo__criterio=detalle.criteriogestionperiodo.criterio, distributivo__profesor_id=detalle.distributivo.profesor_id, distributivo__periodo_id=191).exists():
                            detalledis = DetalleDistributivo(distributivo_id=distriact.id,
                                                             criteriogestionperiodo=criteriogestion,
                                                             horas=detalle.horas)
                            detalledis.save()


                            for act in ActividadDetalleDistributivo.objects.filter(criterio=detalle):
                                if not ActividadDetalleDistributivo.objects.filter(criterio=detalledis).exists():
                                    actividad1 = ActividadDetalleDistributivo(criterio=detalledis,
                                                                      nombre=criteriogestion.criterio.nombre,
                                                                      desde=convertir_fecha('01-10-2022'),
                                                                      hasta=convertir_fecha('24-11-2022'),
                                                                      horas=detalle.horas,
                                                                      vigente=True)
                                    actividad1.save()

    except Exception as ex:
        transaction.set_rollback(True)

#FIN











#CRITERIOS Y ACTIVIDADES
#
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status = True, periodo_id=156)
#     for dis in distributivo:
#
#         if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=156, distributivo_id=dis.id).exists():
#             if dis.profesor.dedicacion_id == 1:
#                 detdistri2 = DetalleDistributivo(
#                         distributivo_id=dis.id,
#                         criteriodocenciaperiodo_id=715,
#                         horas=20
#                     )
#                 detdistri2.save()
#
#             if dis.profesor.dedicacion_id == 2:
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=dis.id,
#                     criteriodocenciaperiodo_id=715,
#                     horas=5
#                 )
#                 detdistri2.save()
#
#
#         if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=156, distributivo_id=dis).exists():
#             if dis.profesor.dedicacion_id == 1:
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=dis.id,
#                     criteriodocenciaperiodo_id=714,
#                     horas=10
#                 )
#                 detdistri2.save()
#
#             if dis.profesor.dedicacion_id == 2:
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=dis.id,
#                     criteriodocenciaperiodo_id=714,
#                     horas=5
#                 )
#                 detdistri2.save()
#
#         if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=147, criteriodocenciaperiodo__periodo=156, distributivo_id=dis).exists():
#             if dis.profesor.dedicacion_id == 1:
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=dis.id,
#                     criteriodocenciaperiodo_id=716,
#                     horas=10
#                 )
#                 detdistri2.save()
#
#             if dis.profesor.dedicacion_id == 2:
#                 detdistri2 = DetalleDistributivo(
#                     distributivo_id=dis.id,
#                     criteriodocenciaperiodo_id=716,
#                     horas=10
#                 )
#                 detdistri2.save()
#
#
#
#
#         for detalledistributivo in DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__periodo=156, distributivo=dis).order_by('-criteriodocenciaperiodo__criterio_id'):
#             actividad1 = None
#             actividad2 = None
#             actividad3 = None
#             # actividad4 = None
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 122:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=156, distributivo=dis).exists():
#                     distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=156, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=122).exists():
#                             actividad1 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PLANIFICAR Y ACTUALIZAR CONTENIDOS DE CLASES, SEMINARIOS, TALLERES, ENTRE OTROS.",
#                                                                       desde=convertir_fecha('03-05-2022'),
#                                                                       hasta=convertir_fecha('27-05-2022'),
#                                                                       horas=distant.horas,
#                                                                       vigente=True)
#                             actividad1.save()
#                             print(u"Inserta atividad 1 %s" % actividad1)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 123:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=156, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=156, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=123).exists():
#                             actividad2 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"DISEÑAR Y ELABORAR MATERIAL DIDÁCTICO, GUÍAS DOCENTES O SYLLABUS",
#                                                                       desde=convertir_fecha('03-05-2022'),
#                                                                       hasta=convertir_fecha('27-05-2022'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad2.save()
#                             print(u"Inserta atividad 2 %s" % actividad2)
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 147:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=147, criteriodocenciaperiodo__periodo=156, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=147, criteriodocenciaperiodo__periodo=156, distributivo=dis)
#
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=147).exists():
#                             actividad3 = ActividadDetalleDistributivo(criterio=detalledistributivo,
#                                                                       nombre=u"PARTICIPAR Y ORGANIZAR COLECTIVOS ACADÉMICOS DE DEBATE, CAPACITACIÓN O INTERCAMBIO DE METODOLOGÍAS Y EXPERIENCIAS DE ENSEÑANZA",
#                                                                       desde=convertir_fecha('03-05-2022'),
#                                                                       hasta=convertir_fecha('27-05-2022'),
#                                                                       horas=distant2.horas,
#                                                                       vigente=True)
#                             actividad3.save()
#                             print(u"Inserta atividad 3 %s" % actividad3)
#
#
#
# #
# #
# #
# except Exception as ex:
#     print(ex)

# #tipo profesor horario
# try:
#     clases = Clase.objects.filter(status=True, materia__nivel__periodo=126, tipoprofesor_id=13)
#     for clase in clases:
#         clase.tipoprofesor_id = 2
#         clase.save()
#         print(u"%s," % (clase.id))
# except Exception as ex:
#     print(ex)
#
# print("fin")

#tipo profesor - profesor materia
# try:
#     pmat = ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=126, tipoprofesor_id=13)
#     for pm in pmat:
#         if not ProfesorMateria.objects.filter(status=True, materia__nivel__periodo=126, tipoprofesor_id=2, materia_id=pm.materia, profesor_id=pm.profesor).exists():
#             pm.tipoprofesor_id = 2
#             pm.save()
#             print(u"%s," % (pm.id))
# except Exception as ex:
#     print(ex)
#
#
#
# print("fin")



#idmatricula 387202
#egresado 423487 genera rubro
#395900, 393226
#393226
#
# PROCESO DE MATRICULA INGLÉS ESTUDIANTE
#
# import xlwt
# from xlwt import *
# from django.http import HttpResponse
#
# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=reporte_moulos_ingles.xls'
# style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
# style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
# style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
# title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
# style1 = easyxf(num_format_str='D-MMM-YY')
# font_style = XFStyle()
# font_style.font.bold = True
# font_style2 = XFStyle()
# font_style2.font.bold = False
# wb = xlwt.Workbook()
# ws = wb.add_sheet('Sheetname')
# estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
# ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
# nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
# filename = os.path.join(output_folder, nombre)
# columns = [(u"Id", 6000),
#            (u"carrera", 6000),
#            (u"cedula", 6000),
#            (u"alumno", 6000),
#            (u"modulo", 6000),
#            (u"cant matricula", 6000),
#            (u"materia asignada", 6000),
#            (u"perdida de gratuidad", 6000),
#            ]
# row_num = 3
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# row_num = 4
#
# contador=1
# persona_responsable=Persona.objects.get(id=29898)
# for matricula in Matricula.objects.filter(status=True, nivel__periodo_id=119,retiradomatricula=False, id__in=[510133] ).exclude(inscripcion__carrera__id__in=[7,138,134,129,90,157]):
#     try:
#         bandera=0
#         modulomalla=None
#         ws.write(row_num, 0, u'%s' % matricula.id, font_style2)
#         ws.write(row_num, 1, u'%s' % matricula.inscripcion.carrera, font_style2)
#         ws.write(row_num, 2, u'%s' % matricula.inscripcion.persona.identificacion(), font_style2)
#         ws.write(row_num, 3, u'%s' % matricula.inscripcion.persona, font_style2)
#         id_modulos_ingles_todos=None
#         if matricula.inscripcion.modulos_ingles_mi_malla():
#             id_modulos_ingles_todos=matricula.inscripcion.modulos_ingles_mi_malla().values_list('asignatura_id',flat=True).distinct()
#         if id_modulos_ingles_todos:
#             if matricula.inscripcion.ultimo_modulo_ingles_pendiente():
#                 modulomalla=matricula.inscripcion.ultimo_modulo_ingles_pendiente()
#                 materias=Materia.objects.filter(status=True, nivel_id=658, asignatura=modulomalla.asignatura,inglesepunemi=True )
#                 for materia in materias:
#                     if materia.tiene_capacidad():
#                         matriculas=1
#                         materiaasignada=None
#                         matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura).count() + 1
#                         if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia, materia__asignatura=modulomalla.asignatura).exists():
#                             materiaasignada = MateriaAsignada(matricula=matricula,
#                                                               materia=materia,
#                                                               notafinal=0,
#                                                               asistenciafinal=0,
#                                                               cerrado=False,
#                                                               matriculas=matriculas,
#                                                               observaciones='',
#                                                               estado_id=NOTA_ESTADO_EN_CURSO,
#                                                               automatricula=False,
#                                                               importa_nota=False)
#                             materiaasignada.save()
#                             materiaasignada.evaluacion()
#                             creditos = materiaasignada.materia.creditos
#                             if materiaasignada.existe_modulo_en_malla():
#                                 creditos = materiaasignada.materia_modulo_malla().creditos
#                             registro = AgregacionEliminacionMaterias(matricula=matricula,
#                                                                      agregacion=True,
#                                                                      asignatura=materiaasignada.materia.asignatura,
#                                                                      responsable=persona_responsable,
#                                                                      fecha=datetime.now().date(),
#                                                                      creditos=creditos,
#                                                                      nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
#                                                                      matriculas=materiaasignada.matriculas)
#                             registro.save()
#                             if materiaasignada.matriculas>1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
#                                 matricula.calculo_matricula_ingles(materiaasignada)
#                             ws.write(row_num, 4, u'%s' % modulomalla, font_style2)
#                             ws.write(row_num, 5, u'%s' % matriculas, font_style2)
#                             ws.write(row_num, 6, u'%s' % materiaasignada, font_style2)
#                             ws.write(row_num, 7, u'%s' % "SI" if matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion) else "NO", font_style2)
#                             row_num += 1
#                             print(u"(%s) -- %s [%s]" % (contador, materiaasignada, materiaasignada.matricula_id))
#                             contador += 1
#                             bandera=1
#                             break
#                         else:
#                             ws.write(row_num, 4, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             ws.write(row_num, 5, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             ws.write(row_num, 6, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             ws.write(row_num, 7, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             row_num += 1
#                             print(u"(%s) -- YA TIENE MATRICULA EN EL MODULO %s" % (contador,materia))
#                             contador += 1
#                             bandera = 1
#             else:
#                 ws.write(row_num, 4, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 ws.write(row_num, 5, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 ws.write(row_num, 6, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 ws.write(row_num, 7, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 row_num += 1
#                 print(u"(%s) -- NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE %s" % (contador,matricula))
#                 contador += 1
#                 bandera = 1
#             # else:
#             #     ws.write(row_num, 4, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 5, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 6, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 7, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     row_num += 1
#             #     print(u"(%s) -- YA TIENE MATRICULA EN AL MENOS UN MODULO %s" %(matricula, contador))
#             #     contador += 1
#             #     bandera = 1
#         else:
#             ws.write(row_num, 4, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             ws.write(row_num, 5, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             ws.write(row_num, 6, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             ws.write(row_num, 7, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             row_num += 1
#             print(u"(%s) -- NO HAY MODULOS DE INGLES EN LA MALLA" % contador)
#             contador += 1
#             bandera = 1
#         if bandera == 0:
#             ws.write(row_num, 4, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             ws.write(row_num, 5, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             ws.write(row_num, 6, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             ws.write(row_num, 7, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             row_num += 1
#             print(u"NO SE MATRICULA - NO HAY CUPO %s -- %s" % (modulomalla,matricula))
#             contador += 1
#     except Exception as ex:
#         ws.write(row_num, 4, u'SALE ERROR %s' % ( matricula), font_style2)
#         ws.write(row_num, 5, u'SALE ERROR %s' % ( matricula), font_style2)
#         ws.write(row_num, 6, u'SALE ERROR %s' % ( matricula), font_style2)
#         ws.write(row_num, 7, u'SALE ERROR %s' % ( matricula), font_style2)
#         row_num += 1
#         contador += 1
#         print('error: %s %s' % (ex,matricula))
#         pass
# wb.save(filename)
# print("FIN: ", filename)
#

#DISTRIBUTIVO
# try:
#     profdistriactual = ProfesorDistributivoHoras.objects.filter(status=True, periodo=126)
#     for pda in profdistriactual:
#         if ProfesorDistributivoHoras.objects.filter(status=True, periodo=156, profesor=pda.profesor).exists():
#             profdistriplan = ProfesorDistributivoHoras.objects.get(status=True, periodo=156, profesor=pda.profesor)
#             profdistriplan.coordinacion = pda.coordinacion
#             profdistriplan.carrera = pda.carrera
#             profdistriplan.save()
#             print(u"%s," % (profdistriplan.id))
# except Exception as ex:
#     print(ex)

import xlwt
from xlwt import *
from django.http import HttpResponse
#
# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=reporte_moulos_ingles.xls'
# style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
# style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
# style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
# title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
# style1 = easyxf(num_format_str='D-MMM-YY')
# font_style = XFStyle()
# font_style.font.bold = True
# font_style2 = XFStyle()
# font_style2.font.bold = False
# wb = xlwt.Workbook()
# ws = wb.add_sheet('Sheetname')
# estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
# ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
# nombre = "Lista" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
# filename = os.path.join(output_folder, nombre)
# columns = [(u"Id", 6000),
#            (u"carrera", 6000),
#            (u"cedula", 6000),
#            (u"alumno", 6000),
#            (u"modulo", 6000),
#            (u"cant matricula", 6000),
#            (u"materia asignada", 6000),
#            (u"perdida de gratuidad", 6000),
#            ]
# row_num = 3
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# row_num = 4
#
#ingles matricula
# contador=1
# persona_responsable=Persona.objects.get(id=29898)
# for matricula in Matricula.objects.filter(status=True, nivel__periodo_id=119,retiradomatricula=False, id__in=[379565] ).exclude(inscripcion__carrera__id__in=[7,138,134,129,90,157]):
#     try:
#         bandera=0
#         modulomalla=None
#         # ws.write(row_num, 0, u'%s' % matricula.id, font_style2)
#         # ws.write(row_num, 1, u'%s' % matricula.inscripcion.carrera, font_style2)
#         # ws.write(row_num, 2, u'%s' % matricula.inscripcion.persona.identificacion(), font_style2)
#         # ws.write(row_num, 3, u'%s' % matricula.inscripcion.persona, font_style2)
#         id_modulos_ingles_todos=None
#         if matricula.inscripcion.modulos_ingles_mi_malla():
#             id_modulos_ingles_todos=matricula.inscripcion.modulos_ingles_mi_malla().values_list('asignatura_id',flat=True).distinct()
#         if id_modulos_ingles_todos:
#             if matricula.inscripcion.ultimo_modulo_ingles_pendiente():
#                 modulomalla=matricula.inscripcion.ultimo_modulo_ingles_pendiente()
#                 materias=Materia.objects.filter(status=True, nivel_id=658, asignatura=modulomalla.asignatura,inglesepunemi=True )
#                 for materia in materias:
#                     if materia.tiene_capacidad():
#                         matriculas=1
#                         materiaasignada=None
#                         matriculas = matricula.inscripcion.historicorecordacademico_set.filter(asignatura=materia.asignatura).count() + 1
#                         if not MateriaAsignada.objects.filter(matricula=matricula, materia=materia, materia__asignatura=modulomalla.asignatura).exists():
#                             materiaasignada = MateriaAsignada(matricula=matricula,
#                                                               materia=materia,
#                                                               notafinal=0,
#                                                               asistenciafinal=0,
#                                                               cerrado=False,
#                                                               matriculas=matriculas,
#                                                               observaciones='',
#                                                               estado_id=NOTA_ESTADO_EN_CURSO,
#                                                               automatricula=False,
#                                                               importa_nota=False)
#                             materiaasignada.save()
#                             materiaasignada.evaluacion()
#                             creditos = materiaasignada.materia.creditos
#                             if materiaasignada.existe_modulo_en_malla():
#                                 creditos = materiaasignada.materia_modulo_malla().creditos
#                             registro = AgregacionEliminacionMaterias(matricula=matricula,
#                                                                      agregacion=True,
#                                                                      asignatura=materiaasignada.materia.asignatura,
#                                                                      responsable=persona_responsable,
#                                                                      fecha=datetime.now().date(),
#                                                                      creditos=creditos,
#                                                                      nivelmalla=materiaasignada.materia.nivel.nivelmalla if materiaasignada.materia.nivel.nivelmalla else None,
#                                                                      matriculas=materiaasignada.matriculas)
#                             registro.save()
#                             if materiaasignada.matriculas>1 or matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion):
#                                 matricula.calculo_matricula_ingles(materiaasignada)
#                             # ws.write(row_num, 4, u'%s' % modulomalla, font_style2)
#                             # ws.write(row_num, 5, u'%s' % matriculas, font_style2)
#                             # ws.write(row_num, 6, u'%s' % materiaasignada, font_style2)
#                             # ws.write(row_num, 7, u'%s' % "SI" if matricula.inscripcion.persona.tiene_otro_titulo(matricula.inscripcion) else "NO", font_style2)
#                             # row_num += 1
#                             print(u"(%s) -- %s [%s]" % (contador, materiaasignada, materiaasignada.matricula_id))
#                             contador += 1
#                             bandera=1
#                             break
#                         else:
#                             # ws.write(row_num, 4, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             # ws.write(row_num, 5, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             # ws.write(row_num, 6, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             # ws.write(row_num, 7, u'YA TIENE MATRICULA EN EL MODULO' %materia, font_style2)
#                             # row_num += 1
#                             print(u"(%s) -- YA TIENE MATRICULA EN EL MODULO %s" % (contador,materia))
#                             contador += 1
#                             bandera = 1
#             else:
#                 # ws.write(row_num, 4, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 # ws.write(row_num, 5, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 # ws.write(row_num, 6, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 # ws.write(row_num, 7, u'NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE', font_style2)
#                 # row_num += 1
#                 print(u"(%s) -- NO AY ULTIMO MÓDULO DE INGLÉS PENDIENTE %s" % (contador,matricula))
#                 contador += 1
#                 bandera = 1
#             # else:
#             #     ws.write(row_num, 4, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 5, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 6, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     ws.write(row_num, 7, u'YA TIENE MATRICULA EN AL MENOS UN MODULO %s' %matricula, font_style2)
#             #     row_num += 1
#             #     print(u"(%s) -- YA TIENE MATRICULA EN AL MENOS UN MODULO %s" %(matricula, contador))
#             #     contador += 1
#             #     bandera = 1
#         else:
#             # ws.write(row_num, 4, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             # ws.write(row_num, 5, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             # ws.write(row_num, 6, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             # ws.write(row_num, 7, u'NO HAY MODULOS DE INGLES EN LA MALLA', font_style2)
#             # row_num += 1
#             print(u"(%s) -- NO HAY MODULOS DE INGLES EN LA MALLA" % contador)
#             contador += 1
#             bandera = 1
#         if bandera == 0:
#             # ws.write(row_num, 4, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             # ws.write(row_num, 5, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             # ws.write(row_num, 6, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             # ws.write(row_num, 7, u'NO SE MATRICULA - NO HAY CUPO %s -- %s '%(modulomalla,matricula), font_style2)
#             # row_num += 1
#             print(u"NO SE MATRICULA - NO HAY CUPO %s -- %s" % (modulomalla,matricula))
#             contador += 1
#     except Exception as ex:
#         # ws.write(row_num, 4, u'SALE ERROR %s' % ( matricula), font_style2)
#         # ws.write(row_num, 5, u'SALE ERROR %s' % ( matricula), font_style2)
#         # ws.write(row_num, 6, u'SALE ERROR %s' % ( matricula), font_style2)
#         # ws.write(row_num, 7, u'SALE ERROR %s' % ( matricula), font_style2)
#         # row_num += 1
#         contador += 1
#         print('error: %s %s' % (ex,matricula))
#         pass
# # wb.save(filename)
# print("FIN: ")




















#criterio2
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status = True, periodo_id=126, profesor_id=244)
#     for dis in distributivo:
#
#         for detalledistributivo in DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__periodo=126, distributivo=dis).order_by('-criteriodocenciaperiodo__criterio_id'):
#
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 122:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=122, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=122).exists():
#                         actdetalle = ActividadDetalleDistributivo.objects.get(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=122)
#                         if distant.horas != actdetalle.horas:
#                             actdetalle.horas = distant.horas
#                             actdetalle.save()
#                             print("Actualización horas actividades profesor %s    +++++  " % (str(distant2.distributivo.profesor)))
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 121:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=121, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=121).exists():
#                         actdetalle2 = ActividadDetalleDistributivo.objects.get(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=121)
#                         if distant2.horas != actdetalle2.horas:
#                             actdetalle2.horas = distant2.horas
#                             actdetalle2.save()
#                             print("Actualización horas actividades profesor %s    +++++  " % (str(distant2.distributivo.profesor)))
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 124:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=124, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=124).exists():
#                         actividad3 = ActividadDetalleDistributivo.objects.get(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=124)
#                         if distant2.horas != actividad3.horas:
#                             actividad3.horas = distant2.horas
#                             actividad3.save()
#                             print("Actualización horas actividades profesor %s    +++++  " % (str(distant2.distributivo.profesor)))
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 123:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=123, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=123).exists():
#                         actividad4 = ActividadDetalleDistributivo.objects.get(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=123)
#                         if distant2.horas != actividad4.horas:
#                             actividad4.horas = distant2.horas
#                             actividad4.save()
#                             print("Actualización horas actividades profesor %s    +++++  " % (str(distant2.distributivo.profesor)))
#
#             if detalledistributivo.criteriodocenciaperiodo.criterio_id == 118:
#                 if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=126, distributivo=dis).exists():
#                     distant2 = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#
#                     if ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=118).exists():
#                         actividad5 = ActividadDetalleDistributivo.objects.get(status=True, criterio=detalledistributivo, criterio__criteriodocenciaperiodo__criterio__id=118)
#                         if distant2.horas != actividad5.horas:
#                             actividad5.horas = distant2.horas
#                             actividad5.save()
#                             print("Actualización horas actividades profesor %s    +++++  " % (str(distant2.distributivo.profesor)))
#
# #
# #
# #
# #
# #
# #
# except Exception as ex:
#     print(ex)
#
# print("fin")


#criterios prácticas salud
# try:
#     distributivo = ProfesorDistributivoHoras.objects.filter(status = True, periodo=126, profesor__profesormateria__tipoprofesor__id=13).distinct()
#     for dis in distributivo:
#
#         if DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo__periodo=126, distributivo=dis, criteriodocenciaperiodo__criterio_id=118):
#             distant = DetalleDistributivo.objects.get(status=True, criteriodocenciaperiodo__criterio_id=118, criteriodocenciaperiodo__periodo=126, distributivo=dis)
#             distant.criteriodocenciaperiodo_id = 752
#             distant.save()
#
#             if ActividadDetalleDistributivo.objects.filter(status=True, criterio=distant, criterio__criteriodocenciaperiodo_id=752).exists():
#                 actividad = ActividadDetalleDistributivo.objects.get(status=True, criterio=distant, criterio__criteriodocenciaperiodo_id=752)
#                 actividad.nombre = u" DIRECCIÓN DE LOS APRENDIZAJES PRÁCTICOS Y DE LABORATORIO, BAJO LA COORDINACIÓN DE UN PROFESOR."
#                 actividad.save()
#                 print("Actualización actividades profesor %s    +++++  " % (str(distant.distributivo.profesor)))
#
#
#         else :
#             if not DetalleDistributivo.objects.filter(status=True, criteriodocenciaperiodo_id=752, criteriodocenciaperiodo__periodo=126, distributivo_id=dis).exists():
#                 horas = ProfesorMateria.objects.filter(profesor=dis.profesor, materia__nivel__periodo=126, activo=True, principal=True, status=True).aggregate(horas=Sum('hora')).get('horas')
#                 if horas:
#                     detdistri = DetalleDistributivo(
#                                     distributivo_id=dis.id,
#                                     criteriodocenciaperiodo_id=752,
#                                     horas=horas
#                                     )
#                     detdistri.save()
#                     dis.actualiza_hijos()
#                     dis.resumen_evaluacion_acreditacion().actualizar_resumen()
#
#                     detalledis = DetalleDistributivo.objects.get(distributivo_id=dis, status=True, criteriodocenciaperiodo_id=752, criteriodocenciaperiodo__periodo=126)
#                     if not ActividadDetalleDistributivo.objects.filter(status=True, criterio=detalledis, criterio__criteriodocenciaperiodo__criterio__id=752).exists():
#
#                         horas = ProfesorMateria.objects.filter(profesor=dis.profesor, materia__nivel__periodo=126, activo=True, principal=True, status=True).aggregate(horas=Sum('hora')).get('horas')
#
#                         actividad = ActividadDetalleDistributivo(criterio=detalledis,
#                                                                     nombre=u"DIRECCIÓN DE LOS APRENDIZAJES PRÁCTICOS Y DE LABORATORIO, BAJO LA COORDINACIÓN DE UN PROFESOR.",
#                                                                     desde=convertir_fecha('31-05-2022'),
#                                                                     hasta=convertir_fecha('30-09-2022'),
#                                                                     horas=horas,
#                                                                     vigente=True)
#                         actividad.save()
#                         print("Actualización actividades profesor %s    +++++  " % (str(detalledis.distributivo.profesor)))
#
#
#
#
#
#
#
#
#
#
#
# except Exception as ex:
#     print(ex)

#print("fin")


def cerrar_materias_transversales_2():
    materias = Materia.objects.filter(status=True, nivel__periodo_id=177, cerrado=False,
                                      asignaturamalla__malla__carrera__coordinacion__in=[2], modeloevaluativo_id=27)
    for materia in materias:
        print(materia)
        for asig in materia.asignados_a_esta_materia():
            asig.cerrado = True
            asig.save(actualiza=False)
            asig.actualiza_estado()
        for asig in materia.asignados_a_esta_materia():
            asig.cierre_materia_asignada()

        materia.cerrado = True
        materia.fechacierre = datetime.now().date()
        materia.save()

#cerrar_materias_transversales_2()

def actualizar_nivel_inscripcion_malla4():
    matriculas = Matricula.objects.filter(status=True, nivel__periodo_id=177, inscripcion__carrera_id__in=[110,149,137,139,187,224] )
    for matricula in matriculas:
        inscripcion = matricula.inscripcion
        print('ACTUALIZANDO- ', inscripcion.persona.cedula)
        inscripcion.actualizar_nivel()
        print('ACTUALIZADO')
    print('FIN')

actualizar_nivel_inscripcion_malla4()