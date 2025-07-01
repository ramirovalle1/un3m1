# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
import xlwt
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import convertir_fecha, convertir_hora, puede_realizar_accion_afirmativo
from sga.models import Profesor, Carrera, ProfesorMateria, ESTADO_TIPO_CLASE, Turno, ProfesorDistributivoHoras


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    if request.method == 'POST':
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Asistencias Docentes en el Periodo'
        profesorid = 0
        periodo = request.session['periodo']
        persona = request.session['persona']
        if puede_realizar_accion_afirmativo(request, 'sga.puede_ver_todo_asistencia_docente'):
            carreras = Carrera.objects.filter(activa=True, malla__asignaturamalla__materia__nivel__periodo=periodo).distinct()
        else:
            carreras = Carrera.objects.filter(activa=True, malla__asignaturamalla__materia__nivel__periodo=periodo, coordinacion__in=persona.mis_coordinaciones()).distinct()
        estadotipoclase = int(request.GET['ide']) if 'ide' in request.GET else 0
        fechainicio = None
        fechafin = None
        horainicio = None
        horafin = None
        if 'hi' in request.GET and 'hf' in request.GET:
            horainicio = convertir_hora(request.GET['hi'])
            horafin = convertir_hora(request.GET['hf'])
            if horainicio > horafin:
                return HttpResponseRedirect("/asistencias_periodo?info=No puede ser mayor la hora de inicio que la hora fin.")
        if 'fi' in request.GET and 'ff' in request.GET:
            inicio = fechainicio = convertir_fecha(request.GET['fi'])
            fin = fechafin = convertir_fecha(request.GET['ff'])
            if inicio > fin:
                return HttpResponseRedirect("/asistencias_periodo?info=No puede ser mayor la fecha de inicio que la fecha fin.")
        else:
            inicio = periodo.inicio
            fin = periodo.fin
            if periodo.fin > datetime.now().date():
                fin = datetime.now().date()
        asistencias_registradas = 0
        asistencias_no_registradas = 0
        asistencias_dias_feriados = 0
        asistencias_dias_examen = 0
        asistencias_dias_tutoria = 0
        asistencias_dias_suspension = 0
        origen_solicitado = 0
        origen_movil = 0
        origen_coordinador = 0
        origen_profesor = 0
        resultado = []
        clases = []
        id_carrera = 0
        if 'idc' in request.GET:
            id_carrera = int(request.GET['idc'])
        if 'idp' in request.GET:
            profesorid = int(request.GET['idp'])
            if profesorid>0:
                profesor = Profesor.objects.get(pk=int(request.GET['idp']))
                profesorescarrera = ProfesorDistributivoHoras.objects.filter(profesor = profesor, periodo=periodo)
            else:
                if id_carrera > 0:
                    profesorescarrera = ProfesorDistributivoHoras.objects.filter(carrera__id=id_carrera, periodo=periodo).distinct()
                else:
                    profesorescarrera = ProfesorDistributivoHoras.objects.filter(carrera__in=carreras, periodo=periodo).distinct()
            for distributivoprofesor in profesorescarrera:
                profesormaterias = ProfesorMateria.objects.filter(profesor=distributivoprofesor.profesor, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6, 7], activo=True).distinct().order_by('desde','materia__asignatura__nombre')
                for profesormateria in profesormaterias:
                    data_asistencia = profesormateria.asistencia_docente(fechainicio=inicio, fechafin=fin, periodo=periodo, estadotipoclase=estadotipoclase, turnocomienza=horainicio, turnotermina=horafin)
                    asistencias_registradas += data_asistencia['total_asistencias_registradas']
                    asistencias_no_registradas += data_asistencia['total_asistencias_no_registradas']
                    asistencias_dias_feriados += data_asistencia['total_asistencias_dias_feriados']
                    asistencias_dias_examen += data_asistencia['total_asistencias_dias_examen']
                    asistencias_dias_tutoria += data_asistencia['total_asistencias_dias_tutoria']
                    asistencias_dias_suspension += data_asistencia['total_asistencias_dias_suspension']
                    origen_solicitado += data_asistencia['origen_solicitado']
                    origen_movil += data_asistencia['origen_movil']
                    origen_coordinador += data_asistencia['origen_coordinador']
                    origen_profesor += data_asistencia['origen_profesor']
                    clases.extend(data_asistencia['clases'])
                clases.sort(key=lambda clasesimp: (clasesimp[4], clasesimp[10]), reverse=True)
        porcentaje = 0
        if (asistencias_registradas+asistencias_no_registradas) > 0:
            porcentaje = Decimal((((asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension) * 100) / (asistencias_registradas + asistencias_no_registradas + asistencias_dias_feriados + asistencias_dias_suspension))).quantize(Decimal('.01'))
        origen_profesor = origen_coordinador + origen_profesor
        total_asistencia_registradas = asistencias_registradas + asistencias_dias_feriados + asistencias_dias_suspension
        resultado.append((asistencias_registradas, asistencias_no_registradas, origen_solicitado, origen_movil, origen_coordinador, origen_profesor, asistencias_dias_feriados + asistencias_dias_suspension, porcentaje, asistencias_dias_examen, total_asistencia_registradas))
        #     porcentaje = Decimal(((asistencias_registradas * 100) / (asistencias_registradas+asistencias_no_registradas))).quantize(Decimal('.01'))
        # resultado.append((asistencias_registradas, asistencias_no_registradas, origen_solicitado, origen_movil, origen_coordinador, origen_profesor, asistencias_dias_feriados,porcentaje,asistencias_dias_examen))

        if 'excel' in request.GET:
            try:
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado.xls'
                wb = xlwt.Workbook()
                ws = wb.add_sheet('Sheetname')
                estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                ws.col(0).width = 1000
                ws.col(1).width = 11000
                ws.col(2).width = 11000
                ws.col(3).width = 27000
                ws.col(4).width = 3000
                ws.col(5).width = 5000
                ws.col(6).width = 3000
                ws.col(7).width = 2000
                ws.col(8).width = 3000
                ws.col(9).width = 4000
                ws.write(4, 0, 'N.')
                ws.write(4, 1, 'CARRERA')
                ws.write(4, 2, 'PROFESOR')
                ws.write(4, 3, 'CLASE')
                ws.write(4, 4, 'FECHA')
                ws.write(4, 5, 'TURNO')
                ws.write(4, 6, 'APERTURA')
                ws.write(4, 7, 'AULA')
                ws.write(4, 8, 'ASISTENCIA')
                ws.write(4, 9, 'ESTADO')
                ws.write(4, 10, 'ORIGEN')
                a = 4
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                for cla in clases:
                    a += 1
                    ws.write(a, 0, a - 4)
                    ws.write(a, 1, cla[1].materia.asignaturamalla.malla.carrera.__str__())
                    ws.write(a, 2, cla[0].__str__())
                    ws.write(a, 3, cla[1].materia.nombre_completo())
                    ws.write(a, 4, cla[4], date_format)
                    ws.write(a, 5, cla[1].turno.nombre_horario())
                    h = ''
                    if cla[3]:
                        h = cla[3].horaentrada.strftime("%H:%M")
                    ws.write(a, 6, h)
                    ws.write(a, 7, cla[1].aula.nombre)
                    asis = ''
                    if cla[2] == 1 or cla[2] == 2:
                        if cla[6] == 1:
                            asis = u"%s/%s (%s%s)" % (round(cla[3].asistencia_real(), 2), round(cla[3].asistencia_plan(), 2), round(cla[3].porciento_asistencia(), 2), "%")
                        else:
                            asis = u"%s/%s (%s%s)" % (round(cla[7].registrados_asistieron(), 2), round(cla[7].registrados(), 2),round(cla[7].porciento_asistencia(), 2), "%")
                    ws.write(a, 8, asis)
                    ws.write(a, 9, cla[11])
                    ws.write(a, 10, cla[5])

                wb.save(response)
                return response
            except Exception as ex:
                pass

        if 'exceltodo' in request.GET:
            try:
                carreras = Carrera.objects.filter(malla__asignaturamalla__materia__nivel__periodo=periodo, status=True, activa=True).order_by('-id').distinct()
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=archivo.xls'
                wb = xlwt.Workbook()
                for carrera in carreras:
                    clases = []
                    nombrearchivo = carrera.alias
                    ws = wb.add_sheet(nombrearchivo)
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 1000
                    ws.col(1).width = 11000
                    ws.col(2).width = 11000
                    ws.col(3).width = 27000
                    ws.col(4).width = 3000
                    ws.col(5).width = 5000
                    ws.col(6).width = 3000
                    ws.col(7).width = 2000
                    ws.col(8).width = 3000
                    ws.col(9).width = 4000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'CARRERA')
                    ws.write(4, 2, 'PROFESOR')
                    ws.write(4, 3, 'CLASE')
                    ws.write(4, 4, 'FECHA')
                    ws.write(4, 5, 'TURNO')
                    ws.write(4, 6, 'APERTURA')
                    ws.write(4, 7, 'AULA')
                    ws.write(4, 8, 'ASISTENCIA')
                    ws.write(4, 9, 'ESTADO')
                    ws.write(4, 10, 'ORIGEN')
                    ws.write(4, 11, 'HORAS PROGRAMADAS')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    profesormaterias = ProfesorMateria.objects.filter(materia__asignaturamalla__malla__carrera=carrera, materia__nivel__periodo=periodo, tipoprofesor_id__in=[1, 2, 5, 6, 7], status=True).distinct().order_by('profesor__persona__apellido1', 'profesor__persona__apellido2', 'profesor__persona__nombres','desde','materia__asignatura__nombre')
                    for profesormateria in profesormaterias:
                        data_asistencia = profesormateria.asistencia_docente(inicio, fin, periodo)
                        clases.extend(data_asistencia['clases'])
                    # fin
                    for cla in clases:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, cla[1].materia.asignaturamalla.malla.carrera.__str__())
                        ws.write(a, 2, cla[0].__str__())
                        ws.write(a, 3, cla[1].materia.nombre_completo())
                        ws.write(a, 4, cla[4], date_format)
                        ws.write(a, 5, cla[1].turno.nombre_horario())
                        h = ''
                        if cla[3]:
                            h = cla[3].horaentrada.strftime("%H:%M")
                        ws.write(a, 6, h)
                        ws.write(a, 7, cla[1].aula.nombre)
                        asis = ''
                        if cla[2] == 1 or cla[2] == 2:
                            if cla[6] == 1:
                                asis = u"%s/%s (%s%s)" % (round(cla[3].asistencia_real(), 2), round(cla[3].asistencia_plan(), 2), round(cla[3].porciento_asistencia(), 2), "%")
                            else:
                                asis = u"%s/%s (%s%s)" % (round(cla[7].registrados_asistieron(), 2), round(cla[7].registrados(), 2),round(cla[7].porciento_asistencia(), 2), "%")
                        ws.write(a, 8, asis)
                        ws.write(a, 9, cla[11])
                        ws.write(a, 10, cla[5])
                        ws.write(a, 11, cla[1].materia.horas)
                wb.save(response)
                return response
            except Exception as ex:
                pass

        if not request.session['periodo'].visible:
            return HttpResponseRedirect("/?info=Periodo Inactivo.")
        profesores = Profesor.objects.filter(profesormateria__activo=True, profesormateria__principal=True, profesormateria__materia__nivel__periodo=periodo, profesormateria__materia__asignaturamalla__malla__carrera__in=carreras, status=True).distinct()
        if id_carrera > 0:
            profesores = profesores.filter(profesormateria__materia__asignaturamalla__malla__carrera__id=id_carrera).distinct()
        profesores = profesores.values_list('id','persona__apellido1','persona__apellido2','persona__nombres').distinct()
        data['profesor_select'] = profesores
        data['profesorid'] = profesorid
        data['clases'] = clases
        data['resultado'] = resultado
        data['hoy'] = datetime.now().date() == inicio and datetime.now().date() == fin
        data['carreraid'] = id_carrera
        data['carreras'] = carreras
        data['estado_tipo_clases'] = ESTADO_TIPO_CLASE
        data['estadoid'] = estadotipoclase
        data['inicio'] = fechainicio
        data['fin'] = fechafin
        data['horainicioselect'] = horainicio
        data['horafinselect'] = horafin
        turnos = Turno.objects.filter(status=True, mostrar=True)
        data['horasinicio'] = turnos.values_list('comienza', flat=True).distinct('comienza').order_by('comienza')
        data['horasfin'] = turnos.values_list('termina', flat=True).distinct('termina').order_by('termina')
        return render(request, "asistencias_periodo/view.html", data)
