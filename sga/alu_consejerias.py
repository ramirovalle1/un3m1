# -*- coding: latin-1 -*-
from datetime import datetime, date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from googletrans import Translator

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ConsejeriaAcademicaDetalleForm
from sga.funciones import log, convertir_fecha
from sga.models import MESES_CHOICES, ConsejeriaAcademicaDetalle, InscripcionConsejeriaAcademica


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    coordinacion = inscripcion.mi_coordinacion()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'listar':
            try:
                fecha = convertir_fecha(request.POST['idfecha'])
                data['consejeriaacademicadetalle'] = consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.filter((Q(consejeria__todos=True) | Q(consejeria__coordinacion=coordinacion)),status=True,fecha=fecha, consejeria__periodo=periodo).order_by('horadesde')
                data['consejeriaacademica'] = consejeriaacademicadetalle[0].consejeria
                data['form2'] = ConsejeriaAcademicaDetalleForm()
                data['inscripcion'] = inscripcion
                template = get_template("alu_consejerias/listar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'confirmar':
            try:
                consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.get(pk=request.POST['id'])
                inscripcionconsejeriaacademica = InscripcionConsejeriaAcademica(inscripcion=inscripcion,
                                                                                consejeriaacademicadetalle=consejeriaacademicadetalle)
                inscripcionconsejeriaacademica.save(request)
                log(u'Confirmo Consejerias Academica: %s' % inscripcionconsejeriaacademica, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.get(pk=request.POST['id'])
                inscripcionconsejeriaacademica = consejeriaacademicadetalle.inscripcionconsejeriaacademica_set.filter(status=True, inscripcion=inscripcion)[0]
                inscripcionconsejeriaacademica.status = False
                inscripcionconsejeriaacademica.save(request)
                log(u'Elimino Consejerias Academica: %s' % inscripcionconsejeriaacademica, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                translator = Translator()
                return JsonResponse({"result": "bad", "ex": translator.translate(ex.__str__(), 'es').text, "mensaje": u"Error al eliminar los datos."})

        if action == 'detalle':
            try:
                data['inscripcionconsejeriaacademicas'] = InscripcionConsejeriaAcademica.objects.filter(inscripcion=inscripcion, consejeriaacademicadetalle__consejeria__periodo=periodo, status=True).order_by('-consejeriaacademicadetalle__fecha')
                template = get_template("alu_consejerias/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'confirmar':
                try:
                    data['title'] = u'Confirmar Consejerias Académicas'
                    data['consejeriaacademicadetalle'] = ConsejeriaAcademicaDetalle.objects.get(pk=request.GET['id'])
                    return render(request, "alu_consejerias/confirmar.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Consejerias Académicas'
                    data['consejeriaacademicadetalle'] = ConsejeriaAcademicaDetalle.objects.get(pk=request.GET['id'])
                    return render(request, "alu_consejerias/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Consejeria UNEMI'
            hoy = datetime.now().date()
            fecha = datetime.now().date()
            panio = fecha.year
            pmes = fecha.month
            if 'mover' in request.GET:
                mover = request.GET['mover']

                if mover == 'anterior':
                    mes = int(request.GET['mes'])
                    anio = int(request.GET['anio'])
                    pmes = mes - 1
                    if pmes == 0:
                        pmes = 12
                        panio = anio - 1
                    else:
                        panio = anio

                elif mover == 'proximo':
                    mes = int(request.GET['mes'])
                    anio = int(request.GET['anio'])
                    pmes = mes + 1
                    if pmes == 13:
                        pmes = 1
                        panio = anio + 1
                    else:
                        panio = anio

        s_anio = panio
        s_mes = pmes
        s_dia = 1
        data['mes'] = MESES_CHOICES[s_mes - 1]
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
                actividaddias = ConsejeriaAcademicaDetalle.objects.filter((Q(consejeria__todos=True) | Q(consejeria__coordinacion=coordinacion)),status=True, fecha=fecha,consejeria__status=True,consejeria__periodo=periodo, fecha__gte=hoy)
                diaact = []
                if actividaddias.exists():
                    valor = ""
                    for actividaddia in actividaddias:
                        # &#13;
                        cadena = u"Hora: %s a %s, Motivo: %s; " % (str(actividaddia.horadesde),str(actividaddia.horahasta),str(actividaddia.consejeria.motivo))
                        valor = valor + cadena
                else:
                    valor = ""
                act = [valor, (fecha < datetime.now().date() and valor == ""),1 ,fecha.strftime('%d-%m-%Y')]
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
        data['archivo'] = None
        data['check_session'] = False
        data['fechainicio'] = date(datetime.now().year, 1, 1)
        data['fechafin'] = datetime.now().date()
        return render(request, "alu_consejerias/view.html", data)