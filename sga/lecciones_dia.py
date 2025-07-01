# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import MATRICULACION_LIBRE
from sga.commonviews import adduserdata
from sga.funciones import convertir_fecha, convertir_hora
from sga.models import Clase, Carrera


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    coordinaciones = persona.mis_coordinaciones()
    periodo = request.session['periodo']
    if request.method == 'POST':

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        adduserdata(request, data)
        data['title'] = u'Listado de cumplimiento de clases por docentes'
        inicio = datetime.now().date()
        fin = datetime.now().date()
        if coordinaciones:
            carreras = Carrera.objects.filter(activa=True, malla__asignaturamalla__materia__nivel__periodo=periodo, coordinacion__in=coordinaciones).distinct()
        else:
            carreras = Carrera.objects.filter(activa=True, malla__asignaturamalla__materia__nivel__periodo=periodo).distinct()
        estadoid = 0
        profesorid = 0
        if 'inicio' in request.GET:
            inicio = convertir_fecha(request.GET['inicio'])
            # if inicio > datetime.now().date():
            #     inicio = datetime.now().date()

        if 'fin' in request.GET:
            fin = convertir_fecha(request.GET['fin'])
            # if fin > datetime.now().date():
            #     fin = datetime.now().date()

        if 'horainicio' in request.GET:
            hora_aux = request.GET['horainicio'].split(':')
            horainicio = str(int(hora_aux[0])-1)+":00"
            horainicio = convertir_hora(horainicio)
        else:
            hora_aux = datetime.now().time().hour
            horainicio = convertir_hora(str(int(hora_aux) - 1) + ":00")
        if 'horafin' in request.GET:
            hora_aux = request.GET['horafin'].split(':')
            horafin = str(int(hora_aux[0]) + 1) + ":00"
            horafin = convertir_hora(horafin)
        else:
            hora_aux = str(datetime.now().time().hour)
            horafin = convertir_hora(str(int(hora_aux) + 1) + ":00")

        if 'profesorid' in request.GET:
            profesorid = int(request.GET['profesorid'])

        if 'estadoid' in request.GET:
            estadoid = int(request.GET['estadoid'])

        clases = []
        profesor_select = []


        claseshorario = Clase.objects.filter(
                                             Q(inicio__gte=inicio, inicio__lte=fin) |
                                             Q(fin__gte=inicio, fin__lte=fin) |
                                             Q(inicio__gte=inicio, fin__lte=fin) |
                                             Q(inicio__lte=inicio, fin__gte=fin),
                                             Q(turno__comienza__gte=horainicio,
                                               turno__termina__lte=horafin) ,
                                             materia__asignaturamalla__malla__carrera__coordinacion__in= coordinaciones,
                                             activo=True).distinct().order_by('materia__profesormateria__profesor', 'turno__comienza')

        if 'carreraid' in request.GET:
            if int(request.GET['carreraid']) > 0:
                carrera = Carrera.objects.get(pk=int(request.GET['carreraid']))
                if MATRICULACION_LIBRE:
                    claseshorario = claseshorario.filter(materia__asignaturamalla__malla__carrera=carrera)
                else:
                    claseshorario = claseshorario.filter(materia__nivel__carrera=carrera)
        else:
            carrera = carreras[0]
            if MATRICULACION_LIBRE:
                claseshorario = claseshorario.filter(materia__asignaturamalla__malla__carrera=carrera)
            else:
                claseshorario = claseshorario.filter(materia__nivel__carrera=carrera)

        fechas = []
        if inicio == fin:
            fechas.append(inicio)
            dia_semana = inicio.isoweekday()
            claseshorario = claseshorario.filter(dia=dia_semana)
        else:
            for dia in daterange(inicio, (fin + timedelta(days=1))):
                fechas.append(dia)

        for clase in claseshorario:
            pm = clase.materia.profesor_principal()
            if pm:
                profesor = pm.persona.nombre_completo_inverso()
            else:
                profesor = "SIN ASIGNAR"
            if profesor != "SIN ASIGNAR":
                if not (pm.id, profesor) in profesor_select:
                    profesor_select.append((pm.id, profesor))

        if profesorid > 0:
            claseshorario = claseshorario.filter(materia__profesormateria__profesor__id=profesorid)

        carreraid = []

        hora_actual = datetime.now().time()
        for fechalista in fechas:
            dia_semanalista = fechalista.isoweekday()
            clases_dia = claseshorario.filter(inicio__lte=fechalista, fin__gte=fechalista, dia=dia_semanalista)
            for clase in clases_dia:
                pm = clase.materia.profesor_principal()
                if pm:
                    profesor = pm.persona.nombre_completo_inverso()
                else:
                    profesor = "SIN ASIGNAR"
                leccion = clase.lecciongrupo_fecha(fechalista)
                if fin == datetime.now().date() and inicio == datetime.now().date():
                    if leccion:
                        if leccion.abierta:
                            estado = 1
                        else:
                            estado = 2
                    else:
                        if clase.turno.comienza > hora_actual:
                            estado = 4
                        else:
                            estado = 3
                else:
                    if leccion:
                        estado = 2
                    else:
                        estado = 3
                adicionar = False
                if estadoid == 0:
                    adicionar = True
                elif estadoid == 1 and estado == 1:
                    adicionar = True
                elif estadoid == 2 and estado == 2:
                    adicionar = True
                elif estadoid == 3 and estado == 3:
                    adicionar = True
                if adicionar:
                    clases.append((profesor, clase, estado, leccion, fechalista))

                if clase.materia.asignaturamalla.malla.carrera.id not in carreraid:
                    carreraid.append(clase.materia.asignaturamalla.malla.carrera.id)

        if 'excel' in request.GET:
            try:
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
                wb = xlwt.Workbook()
                ws = wb.add_sheet("Carrera")
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
                ws.col(10).width = 4000
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
                ws.write(4, 10, 'IDCLASE')
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'
                a = 4
                for cla in clases:
                    a += 1
                    ws.write(a, 0, a - 4)
                    ws.write(a, 1, cla[1].materia.asignaturamalla.malla.carrera.__str__())
                    ws.write(a, 2, cla[0])
                    ws.write(a, 3, cla[1].materia.nombre_completo())
                    ws.write(a, 4, cla[4], date_format)
                    ws.write(a, 5, cla[1].turno.nombre_horario())
                    h = ''
                    if cla[3]:
                        for l in cla[3].mis_leciones():
                            h = l.horaentrada.strftime("%H:%M")
                    ws.write(a, 6, h)
                    ws.write(a, 7, cla[1].aula.nombre)
                    asis = ''
                    if cla[2] == 1 or cla[2] == 2:
                        asis = u"%s/%s (%s%s)" % (round(cla[3].asistencia_real(), 2), round(cla[3].asistencia_plan(), 2), round(cla[3].porciento_asistencia(), 2), "%")
                    ws.write(a, 8, asis)
                    esta = ''
                    if cla[2] == 1:
                        esta = 'ABIERTA'
                    elif cla[2] == 2:
                        esta = 'REGISTRADA'
                    elif cla[2] == 3:
                        esta = 'NO REGISTRADAS'
                    elif cla[2] == 4:
                        esta = u"PRÓXIMA CLASE"
                    ws.write(a, 9, esta)
                    ws.write(a, 10, cla[1].id)
                wb.save(response)
                return response
            except Exception as ex:
                pass

        data['carreraid'] = int(request.GET['carreraid']) if 'carreraid' in request.GET else carreras[0].id
        data['carreras'] = carreras
        data['inicio'] = inicio
        data['fin'] = fin

        data['horainicio'] = str(horainicio)[0:5]
        data['horafin'] = str(horafin)[0:5]

        data['profesorid'] = profesorid
        data['estadoid'] = estadoid
        data['clases'] = clases
        data['profesor_select'] = profesor_select
        data['hoy'] = datetime.now().date() == inicio and datetime.now().date() == fin

        horas = ['07:00','08:00','09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00','19:00','20:00','21:00','22:00']
        data['horas'] = horas
        return render(request, "lecciones_dia/view.html", data)