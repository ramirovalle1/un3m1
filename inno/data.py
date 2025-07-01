# -*- coding: UTF-8 -*-
import calendar
from datetime import datetime, timedelta
from django.contrib import messages
from django.contrib.admin.utils import unquote
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User, Group
from django.db import transaction, router
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.utils.encoding import force_str

from bd.models import LogQuery, get_deleted_objects, TemplateBaseSetting
from decorators import secure_module
from bd.forms import *
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
import sys
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, convertir_fecha
from sga.models import *
from sagest.models import *
from matricula.models import *
from soap.models import *
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    ePeriodoAcademia = periodo.get_periodoacademia()
    hoy = datetime.now().date()

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'loadTeacherClassCalendar':
            try:
                if not 'idp' in request.POST:
                   raise NameError(u"Parametro de profesor no encontrado")
                if not 'ver' in request.POST:
                    raise NameError(u"Parametro de vista no encontrado")
                if not 'modal' in request.POST:
                    raise NameError(u"Parametro de modal no encontrado")
                ver = request.POST['ver']
                profesor = Profesor.objects.get(pk=int(request.POST['idp']))
                pmes = hoy.month
                panio = hoy.year
                pdia = 1
                dwnm = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                dwn = [1, 2, 3, 4, 5, 6, 7]
                semana = []
                dias_semana = DIAS_CHOICES
                dia_verbose = None
                mes_verbose = None
                semana_verbose = None
                fecha_dia = None
                numerosemana = 0
                calenadrio_mes = []
                sesiones = None
                clases = None
                clasecomplexivo = None
                dia_isoweekday = None

                if ver == 'M':
                    if 'mover' in request.POST:
                        mover = request.POST['mover']
                        if mover == 'before':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'after':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio

                        else:
                            pmes = hoy.month
                            panio = hoy.year
                    calendario = calendar.Calendar()
                    calenadrio_mes = calendario.monthdatescalendar(panio, pmes)
                    mes_verbose = MESES_CHOICES[pmes - 1][1]

                if ver == 'D':
                    fecha = hoy
                    pdia = fecha.day
                    if 'mover' in request.POST:
                        mover = request.POST['mover']
                        if mover == 'day':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            dia = int(request.POST['dia'])
                            fecha = date(anio, mes, dia)
                            pdia = fecha.day
                            pmes = fecha.month
                            panio = fecha.year

                        if mover == 'before':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            dia = int(request.POST['dia'])
                            fecha = date(anio, mes, dia)
                            fecha = fecha - timedelta(days=1)
                            pdia = fecha.day
                            pmes = fecha.month
                            panio = fecha.year

                        elif mover == 'after':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            dia = int(request.POST['dia'])
                            fecha = date(anio, mes, dia)
                            fecha = fecha + timedelta(days=1)
                            pdia = fecha.day
                            pmes = fecha.month
                            panio = fecha.year
                    fecha_dia = fecha
                    dia_verbose = dias_semana[fecha.isoweekday() - 1][1]
                    dia_isoweekday = fecha.isoweekday()
                    mes_verbose = (MESES_CHOICES[fecha.month - 1][1]).upper()

                if ver == 'W':
                    fecha = hoy
                    pdia = fecha.day
                    pmes = fecha.month
                    panio = fecha.year
                    calendario = calendar.Calendar()
                    numerosemana = fecha.isocalendar()[1]
                    semana_inicial = 1
                    semana_final = date(fecha.year, 12, 31).isocalendar()[1]
                    if 'mover' in request.POST:
                        mover = request.POST['mover']
                        if mover == 'before':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            numerosemana = int(request.POST['numsemana'])
                            numerosemana -= 1
                            if numerosemana < semana_inicial:
                                mes -= 1
                                if mes == 0:
                                    mes = 12
                                    anio -= 1
                                numerosemana = date(anio, mes, 31).isocalendar()[1]
                            is_valid = False
                            for s in calendario.monthdatescalendar(anio, mes):
                                for f in s:
                                    if f.isocalendar()[1] == numerosemana:
                                        is_valid = True
                            if not is_valid:
                                mes -= 1
                            pdia = 0
                            pmes = mes
                            panio = anio

                        elif mover == 'after':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            numerosemana = int(request.POST['numsemana'])
                            numerosemana += 1
                            if numerosemana > semana_final:
                                numerosemana = 1
                                mes += 1
                                if mes == 13:
                                    mes = 1
                                    anio += 1
                            is_valid = False
                            for s in calendario.monthdatescalendar(anio, mes):
                                for f in s:
                                    if f.isocalendar()[1] == numerosemana:
                                        is_valid = True
                            if not is_valid:
                                mes += 1
                            pdia = 0
                            pmes = mes
                            panio = anio

                    for s in calendario.monthdatescalendar(panio, pmes):
                        for f in s:
                            if f.isocalendar()[1] == numerosemana:
                                semana.append(f)
                    f_init = semana[0]
                    f_finish = semana[6]
                    if f_init.year == f_finish.year:
                        if f_init.month == f_finish.month:
                            semana_verbose = f"{(MESES_CHOICES[f_init.month - 1][1]).upper()} de {f_finish.year}"
                        else:
                            semana_verbose = f"{(MESES_CHOICES[f_init.month - 1][1]).upper()} - {(MESES_CHOICES[f_finish.month - 1][1]).upper()} de {f_finish.year}"
                    else:
                        semana_verbose = f"{(MESES_CHOICES[f_init.month - 1][1]).upper()} de {f_init.year} - {(MESES_CHOICES[f_finish.month - 1][1]).upper()} de {f_finish.year}"

                if 'hoy' in request.POST:
                    if int(request.POST['hoy']) == 1:
                        pmes = hoy.month
                        panio = hoy.year
                        if ver == 'D':
                            pdia = hoy.day
                            dia_verbose = dias_semana[hoy.isoweekday() - 1][1]
                            fecha = hoy
                            dia_isoweekday = fecha.isoweekday()
                        mes_verbose = MESES_CHOICES[hoy.month - 1][1]

                if ver in ['D', 'W']:
                    clases = Clase.objects.filter(status=True,
                                                  activo=True,
                                                  materia__nivel__periodo=periodo,
                                                  materia__nivel__periodo__visible=True,
                                                  materia__nivel__periodo__visiblehorario=True,
                                                  materia__profesormateria__profesor=profesor,
                                                  materia__profesormateria__principal=True,
                                                  materia__profesormateria__tipoprofesor_id__in=[11, 12, 13, 1, 5, 8, 7, 10, 14, 15, 17],
                                                  tipoprofesor_id__in=[11, 12, 1, 5, 8, 7, 13, 10, 14, 15,17]).order_by('inicio')
                    clasesayudante = Clase.objects.values_list('id').filter(status=True,
                                                                            activo=True,
                                                                            materia__nivel__periodo=periodo,
                                                                            materia__nivel__periodo__visible=True,
                                                                            materia__nivel__periodo__visiblehorario=True,
                                                                            materia__profesormateria__profesor_id=profesor.id,
                                                                            profesorayudante_id=profesor.id,
                                                                            materia__profesormateria__principal=True).order_by('inicio')
                    if ver == 'D':
                        clases = clases.filter(materia__fechafinasistencias__gte=fecha, fin__gte=fecha, inicio__lte=fecha, dia=fecha.isoweekday())
                        clases_turnos = profesor.extraer_clases_y_turnos_practica(fecha, periodo, fecha, fecha.isoweekday())
                    if ver == 'W':
                        f_init = semana[0]
                        f_finish = semana[6]
                        clases = clases.filter(materia__fechafinasistencias__gte=f_finish, fin__gte=f_finish, inicio__lte=f_init)
                        clases_turnos = profesor.extraer_clases_y_turnos_practica(f_finish, periodo, f_init)

                    clases = Clase.objects.filter(Q(pk__in=clases.values_list('id')) | Q(pk__in=clasesayudante) | Q(pk__in=clases_turnos[0].values_list('id'))).distinct()
                    idturnostutoria = []
                    if DetalleDistributivo.objects.values("id").filter(distributivo__profesor=profesor, distributivo__periodo=periodo, criteriodocenciaperiodo__criterio_id__in=[7]).exists():
                        # if HorarioTutoriaAcademica.objects.values("id").filter(status=True, profesor=profesor, periodo=periodo).exists():
                        #     idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor=profesor, periodo=periodo).distinct()
                        if ver == 'D':
                            if HorarioTutoriaAcademica.objects.values("id").filter(status=True, profesor=profesor, periodo=periodo, fecha_fin_horario_tutoria__gte=fecha, dia=fecha.isoweekday()).exists():
                                idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor=profesor, periodo=periodo, fecha_fin_horario_tutoria__gte=fecha, dia=fecha.isoweekday()).distinct()
                        if ver == 'W':
                            if HorarioTutoriaAcademica.objects.values("id").filter(status=True, profesor=profesor, periodo=periodo, fecha_fin_horario_tutoria__gte=f_finish).exists():
                                idturnostutoria = HorarioTutoriaAcademica.objects.values_list('turno_id').filter(status=True, profesor=profesor, periodo=periodo, fecha_fin_horario_tutoria__gte=f_finish).distinct()
                    clasecomplexivo = complexivo = ComplexivoClase.objects.filter(status=True, activo=True, materia__profesor__profesorTitulacion_id=profesor.id, materia__status=True)
                    sesiones = Sesion.objects.filter(Q(turno__id__in=clases.values_list('turno__id').distinct()) | Q(turno__complexivoclase__in=complexivo) | Q(turno__id__in=idturnostutoria)).distinct()

                data['dia_verbose'] = dia_verbose
                data['mes_verbose'] = mes_verbose
                data['semana_verbose'] = semana_verbose
                data['numsemana'] = numerosemana
                data['calenadrio_mes'] = calenadrio_mes
                data['fecha_dia'] = fecha_dia
                data['dia_isoweekday'] = dia_isoweekday
                data['pdia'] = pdia
                data['pmes'] = pmes
                data['panio'] = panio
                data['semana'] = semana
                data['mes'] = MESES_CHOICES[pmes - 1]
                data['ws'] = [0, 7, 14, 21, 28, 35]
                data['dwnm'] = dwnm
                data['dwn'] = dwn
                data['lista_ver'] = [['D', 'Día'], ['W', 'Semana'], ['M', 'Mes']]
                data['ver'] = ver
                data['profesor'] = profesor
                data['hoy'] = hoy
                data['h_year'] = hoy.year
                data['h_month'] = hoy.month
                data['h_day'] = hoy.day
                data['sesiones'] = sesiones
                data['clases'] = clases
                data['clasecomplexivo'] = clasecomplexivo
                data['modal'] = request.POST['modal']
                template = get_template("docentes/calendarioclases.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", "mensaje": u"Datos cargados correctamente", "html": json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al obtener los datos. %s" % ex.__str__()})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            return HttpResponseRedirect(request.path)
        else:
            return HttpResponseRedirect("/")
