# -*- coding: latin-1 -*-
from datetime import date, datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.models import Actividad, MESES_CHOICES


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
        data['title'] = u'Calendario de actividades de la institución'
        fecha = datetime.now().date()
        panio = fecha.year
        pmes = fecha.month

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'anterior':
                mes = int(request.GET['mes'])
                anio = int(request.GET['anio'])
                pmes = mes - 1
                if pmes == 0:
                    pmes = 12
                    panio = anio - 1
                else:
                    panio = anio

            elif action == 'proximo':
                mes = int(request.GET['mes'])
                anio = int(request.GET['anio'])
                pmes = mes + 1
                if pmes == 13:
                    pmes = 1
                    panio = anio + 1
                else:
                    panio = anio

        fechainicio = date(panio, pmes, 1)
        try:
            fechafin = date(panio, pmes, 31)
        except Exception as ex:
            try:
                fechafin = date(panio, pmes, 30)
            except Exception as ex:
                try:
                    fechafin = date(panio, pmes, 29)
                except Exception as ex:
                    fechafin = date(panio, pmes, 28)
        actividades = Actividad.objects.filter((Q(inicio__lte=fechainicio) & Q(fin__gte=fechainicio)) |
                                               (Q(inicio__lte=fechafin) & Q(fin__gte=fechafin)) |
                                               (Q(inicio__lte=fechainicio) & Q(fin__gte=fechafin)) |
                                               (Q(inicio__gte=fechainicio) & Q(fin__lte=fechafin))).order_by('id')
        s_anio = panio
        s_mes = pmes
        s_dia = 1
        data['mes'] = MESES_CHOICES[s_mes - 1]
        data['actividades'] = actividades
        data['ws'] = [0, 7, 14, 21, 28, 35]
        lista = {}
        listaactividades = {}
        for i in range(1, 43, 1):
            dia = {i: 'no'}
            actividaddia = {i: None}
            lista.update(dia)
            listaactividades.update(actividaddia)
        comienzo = False
        fin = False
        for i in lista.items():
            try:
                fecha = date(s_anio, s_mes, s_dia)
                if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                    comienzo = True
            except Exception as ex:
                pass
            if comienzo:
                try:
                    fecha = date(s_anio, s_mes, s_dia)
                except Exception as ex:
                    fin = True
            if comienzo and fin is False:
                dia = {i[0]: s_dia}
                s_dia += 1
                lista.update(dia)
                actividadesdias = Actividad.objects.filter((Q(inicio__lte=fecha) & Q(fin__gte=fecha))).order_by('id')
                diaact = []
                for actividad in actividadesdias:
                    diasemana = fecha.isoweekday()
                    adicionar = False
                    if diasemana == 1 and actividad.lunes:
                        adicionar = True
                    if diasemana == 2 and actividad.martes:
                        adicionar = True
                    if diasemana == 3 and actividad.miercoles:
                        adicionar = True
                    if diasemana == 4 and actividad.jueves:
                        adicionar = True
                    if diasemana == 5 and actividad.viernes:
                        adicionar = True
                    if diasemana == 6 and actividad.sabado:
                        adicionar = True
                    if diasemana == 7 and actividad.domingo:
                        adicionar = True
                    if adicionar:
                        act = actividad.tipo.representacion + ',' + actividad.id.__str__()
                        diaact.append(act)
                listaactividades.update({i[0]: diaact})
        data['dias_mes'] = lista
        data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
        data['daymonth'] = 1
        data['s_anio'] = s_anio
        data['s_mes'] = s_mes
        data['lista'] = lista
        data['listaactividades'] = listaactividades
        data['dia_actual'] = datetime.now().date().day
        data['mostrar_dia_actual'] = fecha.month == datetime.now().date().month and fecha.year == datetime.now().date().year
        return render(request, "calendario/view.html", data)