# -*- coding: latin-1 -*-
from datetime import datetime, date, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ConsejeriaAcademicaForm, ConsejeriaAcademicaDetalleForm, ConsejeriaAcademicaDetalleAddForm
from sga.funciones import log, convertir_fecha, convertir_hora
from sga.models import MESES_CHOICES, ConsejeriaAcademica, ConsejeriaAcademicaDetalle, DocenteConsejeriaAcademica


def daterange(start_date, end_date):
    for n in range(int((end_date - start_date).days)):
        yield start_date + timedelta(n)

def controlar_horas(periodo, profesor, fecha, horadesde, horahasta):
    if ConsejeriaAcademicaDetalle.objects.filter(consejeria__periodo=periodo, fecha=fecha, consejeria__profesor=profesor, horadesde__lte=horadesde, horahasta__gte=horadesde).exists():
        return True
    if ConsejeriaAcademicaDetalle.objects.filter(consejeria__periodo=periodo, fecha=fecha, consejeria__profesor=profesor, horadesde__lte=horahasta, horahasta__gte=horahasta).exists():
        return True
    if ConsejeriaAcademicaDetalle.objects.filter(consejeria__periodo=periodo, fecha=fecha, consejeria__profesor=profesor, horadesde__gte=horadesde, horahasta__gte=horadesde, horadesde__lte=horahasta, horahasta__lte=horahasta).exists():
        return True
    return False


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
    # if not perfilprincipal.es_profesor():
    #     return HttpResponseRedirect("/?info=Solo los perfiles de profesor pueden ingresar al modulo.")
    profesor = persona.profesor()
    periodo = request.session['periodo']
    if not DocenteConsejeriaAcademica.objects.filter(profesor=profesor, status=True).exists():
        return HttpResponseRedirect("/?info=No tiene configuración, acerquese al Tics.")
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'add':
            try:
                form = ConsejeriaAcademicaForm(request.POST)
                if form.is_valid():
                    consejeria = ConsejeriaAcademica(periodo = periodo,
                                                     profesor = profesor,
                                                     motivo = form.cleaned_data['motivo'],
                                                     fechadesde = form.cleaned_data['fechadesde'],
                                                     fechahasta = form.cleaned_data['fechahasta'],
                                                     horadesde = form.cleaned_data['horadesde'],
                                                     horahasta = form.cleaned_data['horahasta'],
                                                     lunes = form.cleaned_data['lunes'],
                                                     martes = form.cleaned_data['martes'],
                                                     miercoles = form.cleaned_data['miercoles'],
                                                     jueves = form.cleaned_data['jueves'],
                                                     viernes = form.cleaned_data['viernes'],
                                                     sabado = form.cleaned_data['sabado'],
                                                     domingo = form.cleaned_data['domingo'])
                    consejeria.save(request)

                    fechas = []
                    inicio = form.cleaned_data['fechadesde']
                    fin = form.cleaned_data['fechahasta']
                    if inicio == fin:
                        fechas.append(inicio)
                    else:
                        for dia in daterange(inicio, (fin + timedelta(days=1))):
                            fechas.append(dia)

                    for fechalista in fechas:
                        bandera = False
                        dia_semanalista = fechalista.isoweekday()
                        if form.cleaned_data['lunes'] and dia_semanalista == 1:
                            bandera = True
                        if form.cleaned_data['martes'] and dia_semanalista == 2:
                            bandera = True
                        if form.cleaned_data['miercoles'] and dia_semanalista == 3:
                            bandera = True
                        if form.cleaned_data['jueves'] and dia_semanalista == 4:
                            bandera = True
                        if form.cleaned_data['viernes'] and dia_semanalista == 5:
                            bandera = True
                        if form.cleaned_data['sabado'] and dia_semanalista == 6:
                            bandera = True
                        if form.cleaned_data['domingo'] and dia_semanalista == 7:
                            bandera = True
                        if bandera:
                            if not controlar_horas(periodo, profesor, fechalista, form.cleaned_data['horadesde'], form.cleaned_data['horahasta']):
                                consejeriaacademicadetalle = ConsejeriaAcademicaDetalle(consejeria = consejeria,
                                                                                        fecha = fechalista,
                                                                                        horadesde=form.cleaned_data['horadesde'],
                                                                                        horahasta=form.cleaned_data['horahasta'])
                                consejeriaacademicadetalle.save(request)

                    if ConsejeriaAcademicaDetalle.objects.filter(consejeria=consejeria).count()==0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"No se guardo nigun regisro, fechas incorrectas en los días seleccionados"})
                    log(u'Adiciono nueva solicitud: %s' % consejeria, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddetalle':
            try:
                horadesde = convertir_hora(request.POST['horadesde'])
                horahasta = convertir_hora(request.POST['horahasta'])
                fecha = convertir_fecha(request.POST['idfecha'])
                motivo = request.POST['motivo']
                if not controlar_horas(periodo, profesor, fecha, horadesde, horahasta):
                    consejeria = ConsejeriaAcademica(periodo = periodo,
                                                     profesor = profesor,
                                                     motivo = motivo,
                                                     fechadesde = fecha,
                                                     fechahasta = fecha,
                                                     horadesde = horadesde,
                                                     horahasta = horahasta,
                                                     lunes = True if fecha.isoweekday()==1 else False,
                                                     martes = True if fecha.isoweekday()==2 else False,
                                                     miercoles = True if fecha.isoweekday()==3 else False,
                                                     jueves = True if fecha.isoweekday()==4 else False,
                                                     viernes = True if fecha.isoweekday()==5 else False,
                                                     sabado = True if fecha.isoweekday()==6 else False,
                                                     domingo = True if fecha.isoweekday()==7 else False)
                    consejeria.save(request)

                    consejeriaacademicadetalle = ConsejeriaAcademicaDetalle(consejeria = consejeria,
                                                                            fecha = fecha,
                                                                            horadesde=horadesde,
                                                                            horahasta=horahasta)
                    consejeriaacademicadetalle.save(request)

                    log(u'Adiciono nueva solicitud, sola: %s' % consejeria, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Ya tiene configurado un registro en esas horas."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editdetalle':
            try:
                horadesde = convertir_hora(request.POST['horadesde'])
                horahasta = convertir_hora(request.POST['horahasta'])
                if not horadesde <= horahasta:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"La hora desde debe ser mayor que la hora hasta"})
                consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.get(pk=int(request.POST['id']))
                consejeriaacademicadetalle.horadesde = horadesde
                consejeriaacademicadetalle.horahasta = horahasta
                consejeriaacademicadetalle.save(request)
                log(u'Edito hora consejeria: %s - [%s %s]' % (consejeriaacademicadetalle.consejeria, horadesde, horahasta), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletedetalle':
            try:
                consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.get(pk=int(request.POST['id']))
                log(u'Elimino hora consejeria: %s - [%s %s]' % (consejeriaacademicadetalle.consejeria, consejeriaacademicadetalle.horadesde, consejeriaacademicadetalle.horahasta), request, "add")
                consejeriaacademicadetalle.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'listar':
            try:
                fecha = convertir_fecha(request.POST['idfecha'])
                data['consejeriaacademicadetalle'] = consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.filter(status=True,fecha=fecha, consejeria__profesor__persona=persona, consejeria__periodo=periodo).order_by('horadesde')
                data['consejeriaacademica'] = consejeriaacademicadetalle[0].consejeria
                data['form2'] = ConsejeriaAcademicaDetalleForm()
                template = get_template("pro_consejerias/listar.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'listar_estudiante':
            try:
                fecha = convertir_fecha(request.POST['idfecha'])
                data['consejeriaacademicadetalle'] = consejeriaacademicadetalle = ConsejeriaAcademicaDetalle.objects.filter(status=True,fecha=fecha, consejeria__profesor__persona=persona, consejeria__periodo=periodo).order_by('horadesde')
                data['consejeriaacademica'] = consejeriaacademicadetalle[0].consejeria
                template = get_template("pro_consejerias/listar_estudiante.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return HttpResponseRedirect(request.path)

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'add':
                try:
                    data['title'] = u'Adicionar Configuración'
                    form = ConsejeriaAcademicaForm()
                    data['form'] = form
                    return render(request, "pro_consejerias/add.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Configuración Consejeria'
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

        # data['cuentasbanco'] = cuentas = CuentaBanco.objects.filter(banco__id=BANCO_PACIFICO_ID)
        # if 'cuenta' in request.GET:
        #     data['cuenta'] = CuentaBanco.objects.get(pk=int(request.GET['cuenta']))
        # else:
        #     if cuentas:
        #         data['cuenta'] = cuentas[0]
        #     else:
        #         data['cuenta'] = None
        # data['actividades'] = RecaudacionBanco.objects.filter(cuentabanco=data['cuenta'])
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
                actividaddias = ConsejeriaAcademicaDetalle.objects.filter(status=True, fecha=fecha,consejeria__status=True,consejeria__periodo=periodo, consejeria__profesor__persona=persona)
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

        persona = request.session['persona']
        data['check_session'] = False
        data['fechainicio'] = date(datetime.now().year, 1, 1)
        data['fechafin'] = datetime.now().date()
        data['form3'] = ConsejeriaAcademicaDetalleAddForm()
        return render(request, "pro_consejerias/view.html", data)