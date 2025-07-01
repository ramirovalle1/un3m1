import io
import os
import time
import json
import threading
import shutil
import xlsxwriter
import xlwt
from django.template.loader import render_to_string
from xlwt import *
from webpush import send_user_notification
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.forms import model_to_dict
from django.http import HttpResponse
from django.shortcuts import redirect

from inno.models import MatriculaSedeExamen, AulaPlanificacionSedeVirtualExamen, \
    MateriaAsignadaPlanificacionSedeVirtualExamen
from sga.commonviews import traerNotificaciones
from sga.models import *
from settings import MEDIA_ROOT, MEDIA_URL, DEBUG
from wpush.models import SubscriptionInfomation
from webpush.utils import _send_notification


class ReportPlanificacionSedes(threading.Thread):

    def __init__(self, request, data, eNotificacion):
        self.request = request
        self.data = data
        self.eNotificacion = eNotificacion
        threading.Thread.__init__(self)

    def run(self):
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'sedes')
        request, data, eNotificacion = self.request, self.data, self.eNotificacion
        isFilter = True if 'isFilter' in data and data['isFilter'] else False
        try:
            shutil.rmtree(directory)
        except Exception as ex:
            pass
        try:
            os.makedirs(directory)
        except Exception as ex:
            pass

        # try:
        #     os.stat(directory)
        # except:
        #     os.mkdir(directory)

        nombre_archivo = "reporte_planificacion_sedes{}.xls".format(random.randint(1, 10000).__str__())
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'sedes', nombre_archivo)

        try:
            __author__ = 'Unemi'
            title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
            titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
            font_style = XFStyle()
            font_style.font.bold = True
            font_style2 = XFStyle()
            font_style2.font.bold = False
            wb = Workbook(encoding='utf-8')
            ws = wb.add_sheet('hoja1')
            ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
            ws.write_merge(1, 1, 0, 9, 'REPORTE DE PLANIFICACIÓN DE SEDES', titulo2)
            # response = HttpResponse(content_type="application/ms-excel")
            # response['Content-Disposition'] = 'attachment; filename=reporte_planificación_sedes' + random.randint(1, 10000).__str__() + '.xls'
            columns = [
                (u"#", 1000),
                (u"SEDE", 10000),
                (u"FECHA", 6000),
                (u"HORA INICIO", 6000),
                (u"HORA FIN", 6000),
                (u"SALA/LABORATORIO", 6000),
                (u"CAPACIDAD", 6000),
                (u"PLANIFICADOS", 6000),
                (u"SUPERVISOR", 6000),
                (u"APLICADOR", 6000),
            ]
            row_num = 3
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], font_style)
                ws.col(col_num).width = columns[col_num][1]
            ePeriodo = request.session['periodo']
            eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True).exclude(asignatura_id=4837)
            eNiveles = Nivel.objects.filter(status=True, periodo=ePeriodo, materia__isnull=False, id__in=eMaterias.values_list('nivel_id', flat=True)).distinct()
            eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(status=True, matricula__status=True, matricula__retiradomatricula=False, matricula__nivel__in=eNiveles)
            eSedes = SedeVirtual.objects.filter(pk__in=eMatriculaSedeExamenes.values_list('sede_id', flat=True))
            eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True, turnoplanificacion__fechaplanificacion__periodo=ePeriodo, turnoplanificacion__fechaplanificacion__sede__in=eSedes)
            usernotify = User.objects.get(pk=request.user.pk)
            ePersona = Persona.objects.get(usuario=usernotify)
            if isFilter:
                eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(Q(supervisor=ePersona) | Q(responsable=ePersona) | Q(turnoplanificacion__fechaplanificacion__supervisor=ePersona), status=True, turnoplanificacion__fechaplanificacion__periodo=ePeriodo)
            row_num = 4
            i = 0
            for eAulaPlanificacionSedeVirtualExamen in eAulaPlanificacionSedeVirtualExamenes:
                i += 1
                eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                if eAulaPlanificacionSedeVirtualExamen.supervisor:
                    eSupervisor = eAulaPlanificacionSedeVirtualExamen.supervisor
                elif eFechaPlanificacionSedeVirtualExamen.supervisor:
                    eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                else:
                    eSupervisor = None
                ws.write(row_num, 0, u"%s" % i, font_style2)
                ws.write(row_num, 1, u"%s" % eSedeVirtual.nombre, font_style2)
                ws.write(row_num, 2, u"%s" % eFechaPlanificacionSedeVirtualExamen.fecha.__str__(), font_style2)
                ws.write(row_num, 3, u"%s" % eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__(), font_style2)
                ws.write(row_num, 4, u"%s" % eTurnoPlanificacionSedeVirtualExamen.horafin.__str__(), font_style2)
                ws.write(row_num, 5, u"%s" % eLaboratorioVirtual.nombre, font_style2)
                ws.write(row_num, 6, u"%s" % eLaboratorioVirtual.capacidad, font_style2)
                ws.write(row_num, 7, u"%s" % eAulaPlanificacionSedeVirtualExamen.cantidadad_planificadas(), font_style2)
                ws.write(row_num, 8, u"%s" % eSupervisor.nombre_completo() if eSupervisor else '', font_style2)
                ws.write(row_num, 9, u"%s" % eAplicador.nombre_completo() if eAplicador else '', font_style2)
                row_num += 1
            wb.save(directory)

            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = 'Reporte Listo'
                eNotificacion.url = "{}reportes/horario/examenes/sedes/{}".format(MEDIA_URL, nombre_archivo)
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo='Reporte Listo',
                                             titulo=f'Excel Planificación de sedes {ePeriodo.get_clasificacion_display() if ePeriodo.clasificacion else ""}'.strip(),
                                             destinatario=ePersona,
                                             url="{}reportes/horario/examenes/sedes/{}".format(MEDIA_URL, nombre_archivo),
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)
            subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
            push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=1, status=True).select_related("subscription")
            for device in push_infos:
                try:
                    payload = {"head": "Reporte terminado",
                               "body": 'Planificación de horarios de exámenes en sedes',
                               "action": "notificacion",
                               "timestamp": time.mktime(datetime.now().timetuple()),
                               "url": eNotificacion.url,
                               "btn_notificaciones": traerNotificaciones(request, data, ePersona),
                               "mensaje": 'Su reporte ha sido generado con exito'}
                    _send_notification(device.subscription, json.dumps(payload), ttl=500)
                except Exception as exep:
                    print(f"Fallo de envio del push notification: {exep.__str__()}")
        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = textoerror
                eNotificacion.url = None
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo=textoerror,
                                             titulo=f'Excel Planificación de sedes {ePeriodo.get_clasificacion_display() if ePeriodo.clasificacion else ""}'.strip(),
                                             destinatario=ePersona,
                                             url=None,
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)


class ReportHorariosExamenesSedes(threading.Thread):

    def __init__(self, request, data, eNotificacion):
        self.request = request
        self.data = data
        self.eNotificacion = eNotificacion
        threading.Thread.__init__(self)

    def run(self):

        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'alumnos')
        request, data, eNotificacion = self.request, self.data, self.eNotificacion
        isFilter = True if 'isFilter' in data and data['isFilter'] else False
        try:
            shutil.rmtree(directory)
        except Exception as ex:
            pass
        try:
            os.makedirs(directory)
        except Exception as ex:
            pass

        # try:
        #     os.stat(directory)
        # except:
        #     os.mkdir(directory)

        nombre_archivo = "reporte_horarios_examenes_sedes{}.xlsx".format(random.randint(1, 10000).__str__())
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'alumnos', nombre_archivo)
        usernotify = User.objects.get(pk=request.user.pk)
        ePersona = Persona.objects.get(usuario=usernotify)
        try:
            __author__ = 'Unemi'
            workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
            ws = workbook.add_worksheet('planificación')
            title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
            titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
            font_style = XFStyle()
            font_style.font.bold = True
            font_style2 = XFStyle()
            font_style2.font.bold = False
            fuentecabecera = workbook.add_format({
                'align': 'center',
                'bg_color': 'silver',
                'border': 1,
                'bold': 1
            })

            formatoceldacenter = workbook.add_format({
                'border': 1,
                'valign': 'vcenter',
                'align': 'center'})
            # wb = Workbook(encoding='utf-8')
            # ws = wb.add_sheet('hoja1')
            # ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
            # ws.write_merge(1, 1, 0, 15, 'REPORTE DE HORARIOS DE EXAMENES DE ALUMNOS EN SEDES', titulo2)
            # response = HttpResponse(content_type="application/ms-excel")
            # response['Content-Disposition'] = 'attachment; filename=reporte_horarios_examenes_sedes' + random.randint(1, 10000).__str__() + '.xls'
            columns = [
                (u"#", 1000),
                (u"TIPO DOCUMENTO", 10000),
                (u"DOCUMENTO", 10000),
                (u"ALUMNO", 10000),
                (u"FACULTAD", 10000),
                (u"CARRERA", 10000),
                (u"MODALIDAD", 10000),
                (u"NIVEL", 10000),
                (u"ASIGNATURA", 10000),
                (u"PARALELO", 10000),
                (u"PROFESOR", 10000),
                (u"SEDE", 10000),
                (u"FECHA", 6000),
                (u"HORA INICIO", 6000),
                (u"HORA FIN", 6000),
                (u"SALA/LABORATORIO", 6000),
                (u"SUPERVISOR", 6000),
                (u"APLICADOR", 6000),
                (u"NUM. PLANIFICACIÓN", 6000),
            ]
            row_num = 3
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                ws.set_column(row_num, col_num, columns[col_num][1])
            ePeriodo = request.session['periodo']
            eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
            eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True, asignaturamalla__malla__modalidad_id__lte=3).exclude(Q(asignatura_id=4837) | Q(materiaasignada__materia__asignaturamalla__malla_id__in=eMallasIngles.values_list('id', flat=True)))
            eMateriaAsignadas = MateriaAsignada.objects.filter(materia__in=eMaterias, matricula__status=True, matricula__bloqueomatricula=False, retiramateria=False, status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres').distinct()
            if isFilter:
                eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True, turnoplanificacion__fechaplanificacion__periodo=ePeriodo)
                eAulaPlanificacionSedeVirtualExamenes = eAulaPlanificacionSedeVirtualExamenes.filter(Q(supervisor=ePersona) | Q(responsable=ePersona) | Q(turnoplanificacion__fechaplanificacion__supervisor=ePersona))
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion__in=eAulaPlanificacionSedeVirtualExamenes)
                eMateriaAsignadas = eMateriaAsignadas.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list('materiaasignada__id', flat=True))
            if 'validaFiltro' in request.GET and request.GET['validaFiltro']:
                if not 'inputSede' in request.GET:
                    raise NameError(u'Parametro de sede no encontrado')
                if not 'inputFechaInicio' in request.GET:
                    raise NameError(u'Parametro de fecha inicio no encontrado')
                if not 'inputFechaFin' in request.GET:
                    raise NameError(u'Parametro de fecha fin no encontrado')
                fechainicio = convertir_fecha_invertida(request.GET['inputFechaInicio'])
                fechafin = convertir_fecha_invertida(request.GET['inputFechaFin'])
                if fechainicio > fechafin:
                    raise NameError("Fecha de inicio no puede ser mayor a la fecha fin")
                eAulaPlanificacionSedeVirtualExamenes = AulaPlanificacionSedeVirtualExamen.objects.filter(status=True, turnoplanificacion__fechaplanificacion__periodo=ePeriodo, turnoplanificacion__fechaplanificacion__sede_id=request.GET['inputSede'])
                eAulaPlanificacionSedeVirtualExamenes = eAulaPlanificacionSedeVirtualExamenes.filter(turnoplanificacion__fechaplanificacion__fecha__range=[fechainicio, fechafin])
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(aulaplanificacion__in=eAulaPlanificacionSedeVirtualExamenes)
                eMateriaAsignadas = eMateriaAsignadas.filter(pk__in=eMateriaAsignadaPlanificacionSedeVirtualExamenes.values_list('materiaasignada__id', flat=True))

            # if DEBUG:
            #     eMateriaAsignadas = eMateriaAsignadas[0:10]
            row_num = 4
            i = 0
            for eMateriaAsignada in eMateriaAsignadas:
                i += 1
                eMateriaAsignadaPlanificacionSedeVirtualExamenes = MateriaAsignadaPlanificacionSedeVirtualExamen.objects.filter(materiaasignada=eMateriaAsignada)
                eMateria = eMateriaAsignada.materia
                eParalelo = eMateria.paralelomateria
                eProfesor = eMateria.profesor_principal_virtual()
                eAsignaturaMalla = eMateria.asignaturamalla
                eNivelMalla = eAsignaturaMalla.nivelmalla
                eAsignatura = eAsignaturaMalla.asignatura
                eMatricula = eMateriaAsignada.matricula
                eInscripcion = eMatricula.inscripcion
                eModalidad = eInscripcion.modalidad
                eFacultad = eInscripcion.coordinacion
                eCarrera = eInscripcion.carrera
                ePersona = eInscripcion.persona
                eLaboratorioVirtual = None
                eAplicador = None
                eSupervisor = None
                eTurnoPlanificacionSedeVirtualExamen = None
                eFechaPlanificacionSedeVirtualExamen = None
                eSedeVirtual = None
                if eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id").exists():
                    eMateriaAsignadaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamenes.first()
                    eAulaPlanificacionSedeVirtualExamen = eMateriaAsignadaPlanificacionSedeVirtualExamen.aulaplanificacion
                    eLaboratorioVirtual = eAulaPlanificacionSedeVirtualExamen.aula
                    eAplicador = eAulaPlanificacionSedeVirtualExamen.responsable
                    eTurnoPlanificacionSedeVirtualExamen = eAulaPlanificacionSedeVirtualExamen.turnoplanificacion
                    eFechaPlanificacionSedeVirtualExamen = eTurnoPlanificacionSedeVirtualExamen.fechaplanificacion
                    eSedeVirtual = eFechaPlanificacionSedeVirtualExamen.sede
                    if eAulaPlanificacionSedeVirtualExamen.supervisor:
                        eSupervisor = eAulaPlanificacionSedeVirtualExamen.supervisor
                    elif eFechaPlanificacionSedeVirtualExamen.supervisor:
                        eSupervisor = eFechaPlanificacionSedeVirtualExamen.supervisor
                    else:
                        eSupervisor = None
                if not eSedeVirtual:
                    eMatriculaSedeExamenes = MatriculaSedeExamen.objects.filter(matricula=eMateriaAsignada.matricula, status=True)
                    if eMatriculaSedeExamenes.values("id").exists():
                        eMatriculaSedeExamen = eMatriculaSedeExamenes.first()
                        eSedeVirtual = eMatriculaSedeExamen.sede
                ws.write(row_num, 0, u"%s" % i, formatoceldacenter)
                ws.set_column(row_num, 0, 40)

                ws.write(row_num, 1, u"%s" % ePersona.tipo_documento(), formatoceldacenter)
                ws.set_column(row_num, 1, 40)

                ws.write(row_num, 2, u"%s" % ePersona.documento(), formatoceldacenter)
                ws.set_column(row_num, 2, 40)

                ws.write(row_num, 3, u"%s" % ePersona.nombre_completo(), formatoceldacenter)
                ws.set_column(row_num, 3, 40)

                ws.write(row_num, 4, u"%s" % eFacultad.nombre if eFacultad else '', formatoceldacenter)
                ws.set_column(row_num, 4, 40)

                ws.write(row_num, 5, u"%s" % eCarrera.nombrevisualizar if eCarrera.nombrevisualizar else eCarrera.nombre, formatoceldacenter)
                ws.set_column(row_num, 5, 40)

                ws.write(row_num, 6, u"%s" % eModalidad.nombre if eModalidad else '', formatoceldacenter)
                ws.set_column(row_num, 6, 40)

                ws.write(row_num, 7, u"%s" % eNivelMalla.nombre, formatoceldacenter)
                ws.set_column(row_num, 7, 40)

                ws.write(row_num, 8, u"%s" % eAsignatura.nombre, formatoceldacenter)
                ws.set_column(row_num, 8, 40)

                ws.write(row_num, 9, u"%s" % eParalelo.nombre if eParalelo else '', formatoceldacenter)
                ws.set_column(row_num, 9, 40)

                ws.write(row_num, 10, u"%s" % eProfesor.persona.nombre_completo() if eProfesor else '', formatoceldacenter)
                ws.set_column(row_num, 10, 40)

                ws.write(row_num, 11, u"%s" % eSedeVirtual.nombre if eSedeVirtual else '', formatoceldacenter)
                ws.set_column(row_num, 11, 40)

                ws.write(row_num, 12, u"%s" % eFechaPlanificacionSedeVirtualExamen.fecha.__str__() if eFechaPlanificacionSedeVirtualExamen else '', formatoceldacenter)
                ws.set_column(row_num, 12, 40)

                ws.write(row_num, 13, u"%s" % eTurnoPlanificacionSedeVirtualExamen.horainicio.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', formatoceldacenter)
                ws.set_column(row_num, 13, 40)

                ws.write(row_num, 14, u"%s" % eTurnoPlanificacionSedeVirtualExamen.horafin.__str__() if eTurnoPlanificacionSedeVirtualExamen else '', formatoceldacenter)
                ws.set_column(row_num, 14, 40)

                ws.write(row_num, 15, u"%s" % eLaboratorioVirtual.nombre if eLaboratorioVirtual else '', formatoceldacenter)
                ws.set_column(row_num, 15, 40)

                ws.write(row_num, 16, u"%s" % eSupervisor.nombre_completo() if eSupervisor else '', formatoceldacenter)
                ws.set_column(row_num, 16, 40)

                ws.write(row_num, 17, u"%s" % eAplicador.nombre_completo() if eAplicador else '', formatoceldacenter)
                ws.set_column(row_num, 17, 40)

                ws.write(row_num, 18, u"%s" % len(eMateriaAsignadaPlanificacionSedeVirtualExamenes.values("id")), formatoceldacenter)
                ws.set_column(row_num, 18, 40)
                row_num += 1
            # workbook.save(directory)
            workbook.close()

            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = 'Reporte Listo'
                eNotificacion.url = "{}reportes/horario/examenes/alumnos/{}".format(MEDIA_URL, nombre_archivo)
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo='Reporte Listo',
                                             titulo=f'Excel Horario de examenes en sedes {ePeriodo.get_clasificacion_display() if ePeriodo.clasificacion else ""}'.strip(),
                                             destinatario=ePersona,
                                             url="{}reportes/horario/examenes/alumnos/{}".format(MEDIA_URL, nombre_archivo),
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)
            subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
            push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=1, status=True).select_related("subscription")
            for device in push_infos:
                try:
                    payload = {"head": "Reporte terminado",
                               "body": 'Planificación de horarios de exámenes en sedes',
                               "action": "notificacion",
                               "timestamp": time.mktime(datetime.now().timetuple()),
                               "url": eNotificacion.url,
                               "btn_notificaciones": traerNotificaciones(request, data, ePersona),
                               "mensaje": 'Su reporte ha sido generado con exito'}
                    _send_notification(device.subscription, json.dumps(payload), ttl=500)
                except Exception as exep:
                    print(f"Fallo de envio del push notification: {exep.__str__()}")
        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = textoerror
                eNotificacion.url = None
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo=textoerror,
                                             titulo=f'Excel Horario de examenes en sedes {ePeriodo.get_clasificacion_display() if ePeriodo.clasificacion else ""}'.strip(),
                                             destinatario=ePersona,
                                             url=None,
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)


class ReportCalifcacionPeriodo(threading.Thread):

    def __init__(self, request, data, eNotificacion):
        self.request = request
        self.data = data
        self.eNotificacion = eNotificacion
        threading.Thread.__init__(self)

    def run(self):
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'calificaciones', 'periodos', 'alumnos')
        request, data, eNotificacion = self.request, self.data, self.eNotificacion
        try:
            shutil.rmtree(directory)
        except Exception as ex:
            pass
        try:
            os.makedirs(directory)
        except Exception as ex:
            pass
        idp = request.GET['idp']
        idm = request.GET['idm']
        ePeriodo = Periodo.objects.get(pk=idp)
        eModalidad_aux = Modalidad.objects.get(pk=idm)
        nombre_archivo = "rpt_calificaciones_idp_{}_{}.xlsx".format(ePeriodo.pk, random.randint(1, 10000).__str__())
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'calificaciones', 'periodos', 'alumnos', nombre_archivo)
        usernotify = User.objects.get(pk=request.user.pk)
        ePersona = Persona.objects.get(usuario=usernotify)
        try:
            eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
            eMaterias = Materia.objects.filter(nivel__periodo=ePeriodo, status=True, asignaturamalla__malla__modalidad=eModalidad_aux).exclude(Q(asignatura_id=4837) | Q(materiaasignada__materia__asignaturamalla__malla_id__in=eMallasIngles.values_list('id', flat=True)))
            eMateriaAsignadas = MateriaAsignada.objects.filter(materia__in=eMaterias, matricula__status=True, matricula__bloqueomatricula=False, retiramateria=False, status=True)
            eMateriaAsignadas = eMateriaAsignadas.order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres').distinct()
            if DEBUG:
                eMateriaAsignadas = eMateriaAsignadas[0:10]
            eModeloEvaluativos = ModeloEvaluativo.objects.filter(pk__in=eMaterias.values_list("modeloevaluativo__id", flat=True))
            if not eModeloEvaluativos.values("id").exists():
                raise NameError(u"No exise materias configuradas con modelos evaluativos")
            if len(eModeloEvaluativos.values("id")) > 1:
                raise NameError(u"Exise materias configuradas con más de un modelo evaluativo")
            eModeloEvaluativo = eModeloEvaluativos.first()
            eDetalleModeloEvaluativos = eModeloEvaluativo.campos()
            __author__ = 'Unemi'
            workbook = xlsxwriter.Workbook(directory, {'constant_memory': True})
            ws = workbook.add_worksheet('calificaciones')
            title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
            titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
            font_style = XFStyle()
            font_style.font.bold = True
            font_style2 = XFStyle()
            font_style2.font.bold = False
            fuentetitulo = workbook.add_format({'align': 'center',
                                                'valign': 'vcenter',
                                                'bold': 1,
                                                'text_wrap': True,
                                                'font_size': 16})
            fuentesubtitulo = workbook.add_format({'align': 'center',
                                                   'valign': 'vcenter',
                                                   'bold': 1,
                                                   'text_wrap': True,
                                                   'font_size': 14})
            fuentecabecera = workbook.add_format({'align': 'center',
                                                  'valign': 'vcenter',
                                                  'bold': 1,
                                                  'border': 1,
                                                  'text_wrap': True,
                                                  'fg_color': '#1C3247',
                                                  'font_color': 'white'})
            formatoceldacenter = workbook.add_format({'border': 1,
                                                      'valign': 'vcenter',
                                                      'align': 'center',
                                                      'text_wrap': True
                                                      })
            formatoceldaleft = workbook.add_format({'border': 1,
                                                    'valign': 'vcenter',
                                                    'align': 'left',
                                                    'text_wrap': True
                                                    })
            formatoceldadecimal = workbook.add_format({'num_format': '$ #,##0,00',
                                                       'text_wrap': True,
                                                       'align': 'center',
                                                       'valign': 'vcenter',
                                                       'border': 1})


            columns = [
                (u"#", 10),
                (u"TIPO DOCUMENTO", 20),
                (u"DOCUMENTO", 20),
                (u"ALUMNO", 50),
                (u"FACULTAD", 80),
                (u"CARRERA", 80),
                (u"MODALIDAD", 20),
                (u"NIVEL", 20),
                (u"ASIGNATURA", 150),
                (u"PARALELO", 20),
                (u"PROFESOR", 50),
            ]
            row_num = 3
            for col_num in range(len(columns)):
                ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                ws.set_column(row_num, col_num, columns[col_num][1])
            row_num = 3
            col_num = len(columns)
            if eDetalleModeloEvaluativos.values("id").filter(status=True).exists():
                for eDetalleModeloEvaluativo in eDetalleModeloEvaluativos:
                    ws.write(row_num, col_num, eDetalleModeloEvaluativo.nombre, fuentecabecera)
                    ws.set_column(row_num, col_num, 10)
                    col_num = col_num + 1
            col_num = len(columns) + len(eDetalleModeloEvaluativos.values("id").filter(status=True))
            ws.write(row_num, col_num, "NOTA FINAL", fuentecabecera)
            ws.set_column(row_num, col_num, 10)
            ws.merge_range(1, 1, 1, col_num + 1, "UNIVERSIDAD ESTATAL DE MILAGRO", fuentetitulo)
            ws.merge_range(2, 1, 2, col_num + 1, f'Calificaciones del período académico {ePeriodo.nombre} de carreras en modalidad {eModalidad_aux.nombre}', fuentesubtitulo)
            row_num = 4
            i = 0
            for eMateriaAsignada in eMateriaAsignadas:
                i += 1
                eMateria = eMateriaAsignada.materia
                eModeloEvaluativo = eMateria.modeloevaluativo
                eDetalleModeloEvaluativos = eModeloEvaluativo.campos()
                eModeloEvaluativo.campos()
                eParalelo = eMateria.paralelomateria
                eProfesor = None
                if eMateria.asignaturamalla.malla.modalidad.es_enlinea():
                    eProfesor = eMateria.profesor_principal_virtual()
                elif eMateria.asignaturamalla.malla.modalidad.es_presencial() or eMateria.asignaturamalla.malla.modalidad.es_semipresencial():
                    eProfesor = eMateria.profesor_principal()
                eAsignaturaMalla = eMateria.asignaturamalla
                eMalla = eAsignaturaMalla.malla
                eNivelMalla = eAsignaturaMalla.nivelmalla
                eAsignatura = eAsignaturaMalla.asignatura
                eMatricula = eMateriaAsignada.matricula
                eInscripcion = eMatricula.inscripcion
                eModalidad = eMalla.modalidad
                eFacultad = eInscripcion.coordinacion
                eCarrera = eInscripcion.carrera
                ePersona = eInscripcion.persona
                eEvaluacionGenericas = eMateriaAsignada.evaluacion_generica()

                ws.write(row_num, 0, u"%s" % i, formatoceldacenter)
                ws.set_column(row_num, 0, 10)

                ws.write(row_num, 1, u"%s" % ePersona.tipo_documento(), formatoceldacenter)
                ws.set_column(row_num, 1, 20)

                ws.write(row_num, 2, u"%s" % ePersona.documento(), formatoceldacenter)
                ws.set_column(row_num, 2, 20)

                ws.write(row_num, 3, u"%s" % ePersona.nombre_completo(), formatoceldaleft)
                ws.set_column(row_num, 3, 50)

                ws.write(row_num, 4, u"%s" % eFacultad.nombre if eFacultad else '', formatoceldaleft)
                ws.set_column(row_num, 4, 80)

                ws.write(row_num, 5, u"%s" % eCarrera.nombrevisualizar if eCarrera.nombrevisualizar else eCarrera.nombre, formatoceldaleft)
                ws.set_column(row_num, 5, 80)

                ws.write(row_num, 6, u"%s" % eModalidad.nombre if eModalidad else '', formatoceldacenter)
                ws.set_column(row_num, 6, 20)

                ws.write(row_num, 7, u"%s" % eNivelMalla.nombre, formatoceldacenter)
                ws.set_column(row_num, 7, 20)

                ws.write(row_num, 8, u"%s" % eAsignatura.nombre, formatoceldaleft)
                ws.set_column(row_num, 8, 150)

                ws.write(row_num, 9, u"%s" % eParalelo.nombre if eParalelo else '', formatoceldacenter)
                ws.set_column(row_num, 9, 20)

                ws.write(row_num, 10, u"%s" % eProfesor.persona.nombre_completo() if eProfesor else '', formatoceldaleft)
                ws.set_column(row_num, 10, 50)

                col_num = 10
                if eDetalleModeloEvaluativos.values("id").filter(status=True).exists():
                    for eDetalleModeloEvaluativo in eDetalleModeloEvaluativos:
                        col_num += 1
                        eEvaluacionGenericas_aux = eEvaluacionGenericas.filter(detallemodeloevaluativo=eDetalleModeloEvaluativo)
                        if eEvaluacionGenericas_aux.values("id").exists():
                            eCalificacion = eEvaluacionGenericas_aux.first()
                            ws.write(row_num, col_num, u"%s" % null_to_decimal(eCalificacion.valor, eCalificacion.detallemodeloevaluativo.decimales), formatoceldadecimal)
                            ws.set_column(row_num, col_num, 10)
                        else:
                            ws.write(row_num, col_num, "0.0", formatoceldadecimal)
                            ws.set_column(row_num, col_num, 10)
                    col_num += 1
                    ws.write(row_num, col_num, u"%s" % null_to_decimal(eMateriaAsignada.notafinal, 2), formatoceldadecimal)
                    ws.set_column(row_num, col_num, 10)
                row_num += 1
            workbook.close()

            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = f'Reporte listo del período académico {ePeriodo.nombre} de carreras en modalidad {eModalidad_aux.nombre}'
                eNotificacion.url = "{}reportes/calificaciones/periodos/alumnos/{}".format(MEDIA_URL, nombre_archivo)
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo=f'Reporte listo del período académico {ePeriodo.nombre} de carreras en modalidad {eModalidad_aux.nombre}',
                                             titulo=f'Calificaciones de {ePeriodo.nombre}',
                                             destinatario=ePersona,
                                             url="{}reportes/calificaciones/periodos/alumnos/{}".format(MEDIA_URL, nombre_archivo),
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)
            subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
            push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=1, status=True).select_related("subscription")
            for device in push_infos:
                try:
                    payload = {"head": "Reporte terminado",
                               "body": f'Calificaciones de {ePeriodo.nombre}',
                               "action": "notificacion",
                               "timestamp": time.mktime(datetime.now().timetuple()),
                               "url": eNotificacion.url,
                               "btn_notificaciones": traerNotificaciones(request, data, ePersona),
                               "mensaje": 'Su reporte ha sido generado con exito'}
                    _send_notification(device.subscription, json.dumps(payload), ttl=500)
                except Exception as exep:
                    print(f"Fallo de envio del push notification: {exep.__str__()}")
        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = textoerror
                eNotificacion.url = None
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo=textoerror,
                                             titulo=f'Calificaciones de {ePeriodo.nombre}',
                                             destinatario=ePersona,
                                             url=None,
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)


class ReportPlanificacionExamenes(threading.Thread):

    def __init__(self, request, data, eNotificacion):
        self.request = request
        self.data = data
        self.eNotificacion = eNotificacion
        threading.Thread.__init__(self)

    def run(self):

        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'planificacion')
        request, data, eNotificacion = self.request, self.data, self.eNotificacion
        isFilter = True if 'isFilter' in data and data['isFilter'] else False
        try:
            shutil.rmtree(directory)
        except Exception as ex:
            pass
        try:
            os.makedirs(directory)
        except Exception as ex:
            pass

        # try:
        #     os.stat(directory)
        # except:
        #     os.mkdir(directory)

        nombre_archivo = "reporte_planificacion_examenes_sedes{}.xlsx".format(random.randint(1, 10000).__str__())
        directory = os.path.join(MEDIA_ROOT, 'reportes', 'horario', 'examenes', 'planificacion', nombre_archivo)
        usernotify = User.objects.get(pk=request.user.pk)
        ePersona = Persona.objects.get(usuario=usernotify)
        ePeriodo = request.session['periodo']
        try:
            libre_origen = nombre_archivo
            fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
            fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
            output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
            libdestino = xlwt.Workbook()
            hojadestino = libdestino.add_sheet('HOJA1')
            fil = 0
            columnas = [
                (u"facultad", 7000, 1),
                (u"carrera", 7000, 1),
                (u"nivel", 7000, 0),
                (u"paralelo", 7000, 0),
                (u"asignatura", 7000, 0),
                (u"docente", 7000, 0),
                (u"idmateria", 7000, 0),
                (u"idcursomoodle", 7000, 0),
                (u"examen_creado_sga", 7000, 0),
                (u"modelo_evaluativo_sga", 7000, 0),
                (u"migrado_moodle", 7000, 0),
                (u"nombre_examen_moodle", 7000, 0),
                (u"desde_examen_moodle", 7000, 0),
                (u"hasta_examen_moodle", 7000, 0),
                (u"tiempo_examen_moodle", 7000, 0),
                (u"metodo_navegacion_examen_moodle", 7000, 0),
                (u"total_examen_moodle", 7000, 0),
                (u"valor_examen_moodle", 7000, 0),
                (u"tiene_clave_examen_moodle", 7000, 0),
                (u"categoria_calificacion_examen_moodle", 7000, 0),
                (u"item_calificacion_examen_moodle", 7000, 0),
                (u"seccion_examen_moodle", 7000, 0),
                (u"tiene_preguntas", 7000, 0)
            ]
            for col_num in range(len(columnas)):
                hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
                hojadestino.col(col_num).width = columnas[col_num][1]
            asignaturas_id = DetalleGrupoAsignatura.objects.filter(status=True, grupo_id=2).values('asignatura_id')
            eMaterias = Materia.objects.filter(Q(asignaturamalla__malla__carrera__modalidad=3) | Q(asignaturamalla__asignatura__id__in=asignaturas_id), status=True, nivel__periodo=ePeriodo).exclude(nivel__id__in=[1481, 1482, 1501, 1508])
            totalmaterias = eMaterias.count()
            cont = 1
            fila = 1
            for eMateria in eMaterias:
                facultad = eMateria.coordinacion()
                carrera = eMateria.asignaturamalla.malla.carrera
                nivel = eMateria.asignaturamalla.nivelmalla
                paralelo = eMateria.paralelo
                asignatura = eMateria.asignaturamalla.asignatura.nombre
                profesor = 'sin profesor'
                pm = eMateria.profesormateria_set.filter(status=True, tipoprofesor_id=14).last()
                if pm:
                    profesor = pm.profesor.persona.nombre_completo_inverso()
                idmateria = eMateria.id
                idcurso = eMateria.idcursomoodle
                tiene_examen_sga = 'NO'
                migrado_moodle = 'NO'
                num_preguntas = 0
                modeloevaluativo = 'SIN MODELO'
                if eMateria.modeloevaluativo:
                    modeloevaluativo = eMateria.modeloevaluativo.nombre
                eTestSilaboSemanal = TestSilaboSemanal.objects.filter(status=True,
                                                                      silabosemanal__silabo__materia_id=idmateria,
                                                                      silabosemanal__examen=True,
                                                                      detallemodelo__alternativa_id=20).last()
                if facultad.id == 9:
                    cursor_verbose = 'db_moodle_virtual'
                else:
                    cursor_verbose = 'moodle_db'
                conexion = connections[cursor_verbose]
                cursor = conexion.cursor()
                name = ''
                timeopen = ''
                timeclose = ''
                timelimit = ''
                navmethod = ''
                sumgrades = ''
                grade = ''
                password = None
                categoria = eTestSilaboSemanal.detallemodelo.nombre if eTestSilaboSemanal else ''
                categoryid = 0
                categoria_moodle = ''
                itemid = 0
                item_moodle = ''
                seccion = ''
                instance = None
                if eTestSilaboSemanal:
                    tiene_examen_sga = 'SI'
                    if eTestSilaboSemanal.estado_id == 4:
                        migrado_moodle = 'SI'
                        instance = eTestSilaboSemanal.idtestmoodle
                    if instance:
                        sql = f"""SELECT name, timeopen, timeclose, timelimit, navmethod, sumgrades, grade, password  FROM mooc_quiz WHERE id={instance} AND course={eMateria.idcursomoodle}"""
                        cursor.execute(sql)
                        quiz = cursor.fetchone()
                        if quiz:
                            name = quiz[0]
                            timeopen = quiz[1]
                            timeopen = str(datetime.fromtimestamp(timeopen))
                            timeclose = quiz[2]
                            timeclose = str(datetime.fromtimestamp(timeclose))
                            timelimit = quiz[3]
                            timelimit = str((timelimit / 60) if timelimit else 0)
                            navmethod = quiz[4]
                            sumgrades = str(quiz[5])
                            grade = str(quiz[6])
                            password = str(quiz[7])
                            sql = """SELECT id, fullname FROM mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (
                            eMateria.idcursomoodle, categoria)
                            cursor.execute(sql)
                            category = cursor.fetchone()
                            if category:
                                categoryid = category[0]
                                categoria_moodle = category[1]
                                sql = """select id, itemname from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (
                                eMateria.idcursomoodle, categoryid, name, instance)
                                cursor.execute(sql)
                                item = cursor.fetchone()
                                if item:
                                    itemid = item[0]
                                    item_moodle = item[1]
                            sql = """SELECT section FROM mooc_course_modules WHERE course=%s AND instance=%s """ % (
                            eMateria.idcursomoodle, instance)
                            cursor.execute(sql)
                            course_module = cursor.fetchone()
                            if course_module:
                                sectionid = course_module[0]
                                sql = """SELECT name FROM mooc_course_sections WHERE course=%s AND id=%s """ % (
                                eMateria.idcursomoodle, sectionid)
                                cursor.execute(sql)
                                section = cursor.fetchone()
                                if section:
                                    seccion = section[0]
                            sql = """SELECT DISTINCT  qet.name, qet.questiontext, re.answer, re.answerformat FROM 
                            mooc_quiz q INNER JOIN mooc_quiz_slots qe ON q.id=qe.quizid INNER JOIN mooc_question qet ON 
                            qet.category=qe.questioncategoryid INNER JOIN mooc_question_answers re ON re.question=qet.id 
                            WHERE re.fraction>0 AND q.id=%s  """ % (instance)
                            cursor.execute(sql)
                            preguntas = cursor.fetchall()
                            num_preguntas = len(preguntas)

                print('curso actualizado', cont, 'de', totalmaterias)
                cont += 1

                hojadestino.write(fila, 0, "%s" % facultad, fuentenormal)
                hojadestino.write(fila, 1, "%s" % carrera, fuentenormal)
                hojadestino.write(fila, 2, "%s" % nivel, fuentenormal)
                hojadestino.write(fila, 3, "%s" % paralelo, fuentenormal)
                hojadestino.write(fila, 4, "%s" % asignatura, fuentenormal)
                hojadestino.write(fila, 5, "%s" % profesor, fuentenormal)
                hojadestino.write(fila, 6, idmateria, fuentenormal)
                hojadestino.write(fila, 7, idcurso, fuentenormal)
                hojadestino.write(fila, 8, tiene_examen_sga, fuentenormal)
                hojadestino.write(fila, 9, modeloevaluativo, fuentenormal)
                hojadestino.write(fila, 10, migrado_moodle, fuentenormal)
                hojadestino.write(fila, 11, name, fuentenormal)
                hojadestino.write(fila, 12, timeopen, fuentenormal)
                hojadestino.write(fila, 13, timeclose, fuentenormal)
                hojadestino.write(fila, 14, timelimit, fuentenormal)
                hojadestino.write(fila, 15, navmethod, fuentenormal)
                hojadestino.write(fila, 16, sumgrades, fuentenormal)
                hojadestino.write(fila, 17, grade, fuentenormal)
                hojadestino.write(fila, 18, 'SI' if password else 'NO', fuentenormal)
                hojadestino.write(fila, 19, categoria_moodle, fuentenormal)
                hojadestino.write(fila, 20, item_moodle, fuentenormal)
                hojadestino.write(fila, 21, seccion, fuentenormal)
                hojadestino.write(fila, 22, 'SI' if num_preguntas > 0 else 'NO', fuentenormal)

                fila += 1

            libdestino.save(directory)

            print(directory)
            print("Proceso finalizado. . .")
            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = 'Reporte Listo'
                eNotificacion.url = "{}reportes/horario/examenes/planificacion/{}".format(MEDIA_URL, nombre_archivo)
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo='Reporte Listo',
                                             titulo=f'Planificación de examenes',
                                             destinatario=ePersona,
                                             url="{}reportes/horario/examenes/planificacion/{}".format(MEDIA_URL, nombre_archivo),
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)
            subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
            push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=1, status=True).select_related("subscription")
            for device in push_infos:
                try:
                    payload = {"head": "Reporte terminado",
                               "body": 'Planificación de examenes',
                               "action": "notificacion",
                               "timestamp": time.mktime(datetime.now().timetuple()),
                               "url": eNotificacion.url,
                               "btn_notificaciones": traerNotificaciones(request, data, ePersona),
                               "mensaje": 'Su reporte ha sido generado con exito'}
                    _send_notification(device.subscription, json.dumps(payload), ttl=500)
                except Exception as exep:
                    print(f"Fallo de envio del push notification: {exep.__str__()}")
        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
            if eNotificacion:
                eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
                eNotificacion.en_proceso = False
                eNotificacion.cuerpo = textoerror
                eNotificacion.url = None
                eNotificacion.save(request)
            else:
                eNotificacion = Notificacion(cuerpo=textoerror,
                                             titulo=f'Planificación de examenes',
                                             destinatario=ePersona,
                                             url=None,
                                             prioridad=1,
                                             app_label='SGA',
                                             fecha_hora_visible=datetime.now() + timedelta(days=1),
                                             tipo=2,
                                             en_proceso=False)
                eNotificacion.save(request)