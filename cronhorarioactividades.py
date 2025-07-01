import os
import random
import sys

from django.db.models import Count
import threading

import xlsxwriter
import xlwt
from django.http import HttpResponse
from django.template.loader import render_to_string
from xlwt import *

from settings import MEDIA_ROOT

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")


application = get_wsgi_application()
from django.db import transaction
from datetime import datetime, timedelta

from sagest.models import LogDia, MarcadaActividad, LogMarcada
from sga.models import Periodo, ClaseActividad, Profesor, Persona, ClaseActividadEstado, Clase, ProfesorDistributivoHoras, DetalleDistributivo
from inno.models import HorarioTutoriaAcademica, SolicitudTutoriaIndividual
from sga.funciones import log

periodo = Periodo.objects.get(id=126)
# docentes = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__periodo_id=126, fecha_creacion__gte='2022-05-30').values_list('detalledistributivo__distributivo__profesor_id', flat=True).distinct()
docentes = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=126).values_list('profesor_id', flat=True).distinct()
dias = [1, 2, 3, 4, 5, 6]



fechas = ['2022-05-16', '2022-05-17', '2022-05-18', '2022-05-19', '2022-05-20', '2022-05-24', '2022-05-25']

#
# def marcar(user, fecha, time, actividad):
#     try:
#         marcada = None
#         if Persona.objects.filter(usuario=user).exists():
#             persona = Persona.objects.filter(usuario=user)[0]
#             if persona.perfilusuario_set.filter(administrativo__isnull=False, status=True) or persona.perfilusuario_set.filter(profesor__isnull=False, status=True):
#                 # if persona.distributivopersona_set.filter(estadopuesto_id=1, status=True).exists():
#                 if persona.logdia_set.filter(fecha=fecha).exists():
#                     logdia = persona.logdia_set.filter(fecha=fecha)[0]
#                     logdia.cantidadmarcadas += 1
#                     logdia.procesado = False
#                 else:
#                     logdia = LogDia(persona=persona,
#                                     fecha=fecha,
#                                     cantidadmarcadas=1)
#                 logdia.save()
#                 if not logdia.logmarcada_set.filter(time=time).exists():
#                     registro = LogMarcada(logdia=logdia,
#                                           time=time,
#                                           secuencia=logdia.cantidadmarcadas,
#                                           tipomarcada=2)
#                     registro.save()
#                     marcada = registro
#                 nombres = persona.apellido1 + ' ' + persona.apellido2 + ' ' + persona.nombres
#                 print(nombres, marcada)
#                 if marcada is not None:
#                     actividad = ClaseActividad.objects.get(id=actividad)
#                     for act in ClaseActividad.objects.filter(dia=actividad.dia, detalledistributivo__distributivo__profesor=actividad.detalledistributivo.distributivo.profesor, detalledistributivo__distributivo__periodo=actividad.detalledistributivo.distributivo.periodo).order_by('turno__comienza'):
#                         if not MarcadaActividad.objects.filter(claseactividad=act, logmarcada__logdia__fecha=fecha) or act.marcada_doble(fecha):
#                             if act.id == actividad.id:
#                                 detalle = MarcadaActividad(logmarcada=marcada, claseactividad=act)
#                                 detalle.save()
#                                 print(detalle.pk)
#                             elif not act.modalidad == 1 and not act.ordenmarcada == 3 and not act.ordenmarcada == 1:
#                                 detalle = MarcadaActividad(logmarcada=marcada, claseactividad=act)
#                                 detalle.save()
#                                 print(detalle.pk)
#     except Exception as e:
#         print(e)

# def horarios_marcar():
#     try:
#         for p in docentes:
#             prof = Profesor.objects.get(id=p)
#
#             claseactividadestado = ClaseActividadEstado.objects.filter(profesor=prof, periodo=periodo, status=True).order_by('-id')
#             if claseactividadestado:
#                 for actividad in ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo_id=156).order_by('turno__comienza'):
#                     if str(claseactividadestado.first().fecha_creacion.date()) in fechas:
#                         for fecha in fechas:
#                             f = datetime.strptime(fecha, '%Y-%m-%d').date()
#                             if f >= claseactividadestado.first().fecha_creacion.date() and actividad.dia == f.weekday() + 1:
#                                 if actividad.marcada_doble(f) or (actividad.modalidad == 2 and (actividad.ordenmarcada == 1 or actividad.ordenmarcada == 3) and not actividad.actividad_marcada(f)) and not actividad.ordenmarcada == 2:
#                                     if actividad.marcada_doble(f):
#                                         if len(actividad.marcadaactividad_set.filter(status=True, logmarcada__logdia__fecha=f)) == 0:
#                                             hora = datetime.strptime((str(f) + ' ' + str(actividad.turno.comienza)), '%Y-%m-%d %H:%M:%S')
#                                             if not LogMarcada.objects.filter(logdia__fecha=f, tipomarcada=2, time__range=(hora - timedelta(minutes=10), hora + timedelta(hours=1)), logdia__persona=prof.persona):
#                                                 marcar(prof.persona.usuario, f, hora, actividad.id)
#                                             hora = datetime.strptime((str(f) + ' ' + str(actividad.turno.termina)), '%Y-%m-%d %H:%M:%S')
#                                             if not LogMarcada.objects.filter(logdia__fecha=f, tipomarcada=2, time__range=(hora - timedelta(minutes=10), hora + timedelta(hours=1)), logdia__persona=prof.persona):
#                                                 marcar(prof.persona.usuario, f, hora + timedelta(minutes=1), actividad.id)
#                                         else:
#                                             hora = datetime.strptime((str(f) + ' ' + str(actividad.turno.termina)), '%Y-%m-%d %H:%M:%S')
#                                             if not LogMarcada.objects.filter(logdia__fecha=f, tipomarcada=2, time__range=(hora - timedelta(minutes=10), hora + timedelta(hours=1)), logdia__persona=prof.persona):
#                                                 marcar(prof.persona.usuario, f, hora + timedelta(minutes=1), actividad.id)
#                                     elif not actividad.marcada_doble(f) and not actividad.ordenmarcada == 3:
#                                         hora = datetime.strptime((str(f) + ' ' + str(actividad.turno.comienza)), '%Y-%m-%d %H:%M:%S')
#                                         if not LogMarcada.objects.filter(logdia__fecha=f, tipomarcada=2, time__range=(hora - timedelta(minutes=10), hora + timedelta(hours=1)), logdia__persona=prof.persona):
#                                             marcar(prof.persona.usuario, f, hora, actividad.id)
#                                     else:
#                                         hora = datetime.strptime((str(f) + ' ' + str(actividad.turno.termina)), '%Y-%m-%d %H:%M:%S')
#                                         if not LogMarcada.objects.filter(logdia__fecha=f, tipomarcada=2, time__range=(hora - timedelta(minutes=10), hora + timedelta(hours=1)), logdia__persona=prof.persona):
#                                             marcar(prof.persona.usuario, f, hora + timedelta(minutes=1), actividad.id)
#
#
#         print('Masivo de marcadas finalizado.............')
#     except Exception as e:
#         print(e)


# def horarios():
#     for p in docentes:
#         for iddia in dias:
#             pk = None
#             actividadesdia = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo=periodo,
#                                                            dia=iddia).values('id', 'modalidad', 'turno__comienza')
#             clasesdia = Clase.objects.filter(materia__nivel__periodo__visible=True, materia__nivel__periodo=periodo, materia__nivel__periodo__visiblehorario=True, activo=True, dia=iddia, materia__profesormateria__profesor_id=p, materia__profesormateria__principal=True, materia__profesormateria__activo=True, materia__profesormateria__status=True).order_by('inicio')
#             for actividadt in ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo_id=126, dia=iddia).order_by('turno__comienza'):
#                 changeorden = 2
#                 antecesor = ClaseActividad.objects.get(id=pk) if pk else None
#                 actividadvirtualdespues = actividadesdia.filter(tipodistributivo=3, turno__comienza__gt=actividadt.turno.termina).exists()
#                 actividadotrasdespues = actividadesdia.filter(tipodistributivo__lt=3, turno__comienza__gt=actividadt.turno.termina).exclude(id=actividadt.pk).exists()
#                 esgestion = True if actividadt.tipodistributivo == 3 else False
#                 actividadt.ordenmarcada = 2
#                 if not actividadt.ordenmarcada == 1:
#                     if not esgestion:
#                         changeorden = None
#                     if antecesor:
#                         clasesintermedias = clasesdia.filter(turno__comienza__gte=antecesor.turno.termina, turno__termina__lte=actividadt.turno.comienza)
#                         if antecesor.tipodistributivo == 3 and not esgestion and not antecesor.ordenmarcada == 1 and not actividadvirtualdespues or (clasesintermedias and antecesor.tipodistributivo == 3):
#                             antecesor.ordenmarcada = 3 if not antecesor.ordenmarcada == 1 else 1
#                             if esgestion:
#                                 changeorden = 1
#                         elif esgestion and not antecesor.tipodistributivo == 3 or clasesintermedias:
#                             changeorden = 1
#                         elif esgestion and antecesor.tipodistributivo == 3 and not actividadvirtualdespues:
#                             changeorden = 3
#                         elif antecesor.tipodistributivo == 3 and not esgestion and not antecesor.ordenmarcada == 1:
#                             antecesor.ordenmarcada = 3
#                         antecesor.save()
#                     elif esgestion:
#                         changeorden = 1
#                     actividadt.ordenmarcada = changeorden
#                     actividadt.save()
#                 pk = actividadt.pk
#     print('Proceso de orden de marcadas finalizado.............')
#     # horarios_marcar()
#     # print('iniciando masivo de marcadas.............')

def horario_tutoria():
    print(len(docentes))
    directory = os.path.join(MEDIA_ROOT, 'reportes', 'horarioactividades')
    try:
        try:
            os.stat(directory)
        except:
            os.mkdir(directory)

        nombre_archivo = "reporte_horas_planificadas.xls".format(random.randint(1, 10000).__str__())
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horarioactividades', nombre_archivo)
        # print(len(docentes))
        borders = Borders()
        borders.left = 1
        borders.right = 1
        borders.top = 1
        borders.bottom = 1
        __author__ = 'Unemi'
        title = easyxf('font: name Arial, bold on , height 240; alignment: horiz centre')
        normal = easyxf('font: name Arial , height 150; alignment: horiz left')
        encabesado_tabla = easyxf('font: name Arial , bold on , height 150; alignment: horiz left')
        normalc = easyxf('font: name Arial , height 150; alignment: horiz center')
        subtema = easyxf('font: name Arial, bold on , height 180; alignment: horiz left')
        normalsub = easyxf('font: name Arial , height 180; alignment: horiz left')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        normal.borders = borders
        normalc.borders = borders
        normalsub.borders = borders
        subtema.borders = borders
        encabesado_tabla.borders = borders
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('exp_xls_post_part')

        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename=horarioactividades.xls'
        ws.col(0).width = 1000
        ws.col(1).width = 3500
        ws.col(2).width = 3500
        ws.col(3).width = 1000
        ws.col(4).width = 1000


        row_num = 0
        ws.write(row_num, 0, "Nº", encabesado_tabla)
        ws.write(row_num, 1, "DOCENTE", encabesado_tabla)
        ws.write(row_num, 2, "CRITERIO", encabesado_tabla)
        ws.write(row_num, 3, u"HORAS ASIGNADAS", encabesado_tabla)
        ws.write(row_num, 4, u"HORAS PLANIFICADAS", encabesado_tabla)

        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        data = {}
        c= 1
        row_num = 1
        i = 0
        for p in docentes:
            print(c)
            campo0 = c
            campo2 = ' '
            for actividad in DetalleDistributivo.objects.filter(status=True, distributivo__profesor_id=p, distributivo__periodo=periodo).distinct():
                campo1 = actividad.distributivo.profesor.persona.nombre_completo()
                if actividad.criteriodocenciaperiodo:
                    campo2 = actividad.criteriodocenciaperiodo.criterio.nombre
                if actividad.criterioinvestigacionperiodo:
                    campo2 = actividad.criterioinvestigacionperiodo.criterio.nombre
                if actividad.criteriogestionperiodo:
                    campo2 = actividad.criteriogestionperiodo.criterio.nombre

                campo3 = str(int(actividad.horas))
                horasact = (ClaseActividad.objects.values("id").filter(detalledistributivo=actividad).count())
                if actividad.criteriodocenciaperiodo and actividad.criteriodocenciaperiodo.criterio_id == 118:
                    clase = Clase.objects.filter(status=True, activo=True, profesor=actividad.distributivo.profesor, materia__nivel__periodo=actividad.distributivo.periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True).values('id').distinct().order_by('inicio')
                    if clase.exists():
                        horasact += int(len(clase.values('dia', 'turno')))
                if actividad.criteriodocenciaperiodo and actividad.criteriodocenciaperiodo.criterio_id == 159:
                    clase = Clase.objects.filter(status=True, activo=True, profesor=actividad.distributivo.profesor, materia__nivel__periodo=actividad.distributivo.periodo, materia__nivel__periodo__visible=True, materia__nivel__periodo__visiblehorario=True, tipoprofesor_id=13).values('id').distinct().order_by('inicio')
                    if clase.exists():
                        horasact += int(len(clase))
                campo4=str(int(horasact))
                ws.write(row_num, 0, campo0, normal)
                ws.write(row_num, 1, campo1, normal)
                ws.write(row_num, 2, campo2, normal)
                ws.write(row_num, 3, campo3, normal)
                ws.write(row_num, 4, campo4, normal)
                wb.save(directory)
                row_num += 1
            c+=1

    except Exception as e:
        print(e)
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))

    print('media/reportes/horarioactividades/reporte_horas_planificadas.xls')
    print('Proceso de horario de tutorias finalizado.............')

print('iniciando horario de tutorias.............')
# horarios()
horario_tutoria()

# print(c)
# estado = ClaseActividadEstado.objects.filter(status=True, periodo=periodo, profesor_id=p, estadosolicitud=2).exists()
# actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor_id=p, distributivo__periodo=periodo, criteriodocenciaperiodo_id__isnull=False).values_list('id', flat=True).distinct()
# for iddia in dias:
#     actividadesdia = ClaseActividad.objects.filter(status=True, detalledistributivo__distributivo__profesor_id=p, detalledistributivo__distributivo__periodo=periodo, dia=iddia, detalledistributivo__criteriodocenciaperiodo__isnull=False)
# #     criteriosdel = actividadesdia.exclude(detalledistributivo_id__in=actidocencia).values_list('detalledistributivo__criteriodocenciaperiodo__criterio_id', flat=True)
# #     for actividad in actividadesdia:
# #         if estado:
# #             if actividad.estadosolicitud == 1:
# #                 actividad.estadosolicitud = 2
# # #                 actividad.save()
# #         tutoold = HorarioTutoriaAcademica.objects.filter(profesor_id=p, periodo=periodo, dia=actividad.dia, turno=actividad.turno)
# #         if actividad.detalledistributivo.criteriodocenciaperiodo.criterio.procesotutoriaacademica:
# #             if not tutoold.exists():
# #                   tuto = HorarioTutoriaAcademica(profesor_id=p, periodo=periodo, dia=actividad.dia, turno=actividad.turno)
# #         # #         tuto.save()
# #         if actividad.detalledistributivo.criteriodocenciaperiodo.criterio_id == 136 or actividad.detalledistributivo.criteriodocenciaperiodo.criterio_id in criteriosdel:  # id de criterio de tutoria en plataforma
# #              print( '')
#              # if tutoold.exists():
#         #         tutoold.delete()
#     # for tu in HorarioTutoriaAcademica.objects.filter(profesor_id=p, periodo=periodo, dia=iddia).exclude(turno_id__in=actividadesdia.filter(detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).values_list('turno_id', flat=True)):
#     #     tu.delete()
#     for tut in  HorarioTutoriaAcademica.objects.filter(profesor_id=p, periodo=periodo, dia=iddia, turno_id__in=actividadesdia.filter(detalledistributivo__criteriodocenciaperiodo__criterio__procesotutoriaacademica=True).values_list('turno_id', flat=True)):
#         if HorarioTutoriaAcademica.objects.filter(profesor_id=p, periodo=periodo, dia=iddia, turno=tut.turno).count() > 1:
#             if tut.en_uso():
#                 duplicados = HorarioTutoriaAcademica.objects.filter(profesor_id=p, periodo=periodo, dia=iddia, turno=tut.turno).values_list('id', flat=True)
#                 solicitudes = SolicitudTutoriaIndividual.objects.filter(status=True, horario_id__in=duplicados)
#                 if solicitudes:
#                     mayor = solicitudes.values('horario_id').annotate(cant=Count('id')).values_list('cant', 'horario_id').order_by('-cant')[0][1]
#                     for s in solicitudes:
#                         s.horario_id = mayor
#                         s.save()
#             else:
#                 tut.delete()








