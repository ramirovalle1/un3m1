# -*- coding: latin-1 -*-
import os
from datetime import datetime, timedelta,date
from django.forms import model_to_dict
import xlwt
from django.contrib.auth.decorators import login_required
from xlwt import *
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import  ActividadConvenioForm
from sga.funciones import log, MiPaginador, generar_nombre, bad_json
from django.db.models import Q
from sga.models import ConvenioEmpresa, TipoConvenio, TipoArchivoConvenio, ArchivoConvenio, EmpresaEmpleadora, Persona, \
    Empleador, miinstitucion, ConvenioCarrera, Carrera, CUENTAS_CORREOS, MovilidadTipoSolicitud, MovilidadBaseLegal, \
    MovilidadTipoEstancia, MESES_CHOICES,ActividadConvenio
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addactividad':
            try:
                f = ActividadConvenioForm(request.POST)
                fecha = datetime.strptime((request.POST['fecha']), '%d-%m-%Y').date()
                convenio = ConvenioEmpresa.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    actividad = ActividadConvenio(convenioempresa = convenio,
                                              actividad= f.cleaned_data['actividad'],
                                              fecha= fecha
                )

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("actividadconvenio_", newfile._name)
                        actividad.archivo = newfile

                    actividad.save(request)

                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editactividad':
            try:
                f = ActividadConvenioForm(request.POST)
                actividad = ActividadConvenio.objects.get(pk=request.POST['id'])
                if f.is_valid():
                    actividad.actividad = f.cleaned_data['actividad']

                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("actividadconvenio_", newfile._name)
                        actividad.archivo = newfile
                    actividad.save(request)
                    log(u'Editó actividad: %s' % actividad, request, "edit")

                return JsonResponse({"result": False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delactividad':
            try:
                # f = ActividadConvenioForm(request.POST)
                actividad = ActividadConvenio.objects.get(pk=request.POST['id'])
                actividad.status = False
                actividad.save(request)
                log(u'Eliminó actividad: %s' % actividad, request, "del")
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": str(ex)}
            return JsonResponse(res_json, safe=False)

        return HttpResponseRedirect(request.path)
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'actividades':
                try:
                    data['title'] = u'Actividades'
                    data['convenioempresa'] = convenioempresa = ConvenioEmpresa.objects.get(pk=int(request.GET['id']), status=True)
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
                            actividaddia = ActividadConvenio.objects.filter(fecha=fecha,
                                                                           status=True,convenioempresa=convenioempresa)
                            diaact = []
                            if actividaddia.exists():
                                valor = str(actividaddia[0].actividad)
                            else:
                                valor = ""
                            act = [valor, (fecha < datetime.now().date() and valor == ""), actividaddia.count(),
                                   fecha.strftime('%d-%m-%Y')]
                            diaact.append(act)
                            listaactividades.update({i[0]: diaact})
                    data['dias_mes'] = lista
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listaactividades'] = listaactividades
                    data['mostrar_dia_actual'] = fecha.month == datetime.now().date().month and fecha.year == datetime.now().date().year

                    data['actividades'] = actividades = convenioempresa.actividadconvenio_set.filter(status=True,fecha__month=s_mes, fecha__year=s_anio)


                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]

                    return render(request, "dir_convenios/viewactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['filtro'] = filtro = ConvenioEmpresa.objects.get(pk=int(request.GET['id']))
                    data['fecha'] = request.GET['fecha']
                    data['id'] = request.GET['id']
                    form = ActividadConvenioForm()
                    data['form2'] = form
                    template = get_template("dir_convenios/modal/actividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editactividad':
                try:
                    data['actividad'] = actividad = ActividadConvenio.objects.get(pk=int(request.GET['id']))
                    data['id'] = request.GET['id']
                    form = ActividadConvenioForm(initial=model_to_dict(actividad))
                    data['form2'] = form
                    template = get_template("dir_convenios/modal/actividad.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            fecha_actual = datetime.now().date()
            data['title'] = u'Convenios institucionales'

            departamento=persona.mi_departamentopersona()
            id, tipo, estado, desde, hasta, search, filtros, url_vars = request.GET.get('id', ''), request.GET.get('tipo', ''), request.GET.get('estado', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), request.GET.get('search', ''), Q(status=True), ''
            if id:
                filtros = filtros & Q(id=id)
            if tipo:
                data['tipo'] = tipo = int(tipo)
                url_vars += "&tipo={}".format(tipo)
                if tipo == 1:
                    filtros = filtros & Q(para_practicas=True)
                if tipo == 2:
                    filtros = filtros & Q(para_pasantias=True)
                if tipo == 3:
                    filtros = filtros & Q(para_practicas=True) | Q(para_pasantias=True)
            if estado:
                data['estado'] = estado = int(estado)
                url_vars += "&estado={}".format(estado)
                if estado == 1:
                    filtros = filtros & Q(fechafinalizacion__gte=fecha_actual)
                elif estado == 2:
                    filtros = filtros & Q(fechafinalizacion__lte=fecha_actual)
            if desde:
                data['desde'] = desde
                url_vars += "&desde={}".format(desde)
                filtros = filtros & Q(fechainicio__gte=desde)
            if hasta:
                data['hasta'] = hasta
                url_vars += "&hasta={}".format(hasta)
                filtros = filtros & Q(fechafinalizacion__lte=hasta)
            if search:
                data['search'] = search
                s = search.split()
                filtros = filtros & (Q(empresaempleadora__nombre__icontains=search) |
                                     Q(tipoconvenio__nombre__icontains=search))
                url_vars += '&search={}'.format(search)

            data["url_vars"] = url_vars

            convenio = ConvenioEmpresa.objects.filter(filtros,cargo_denominaciones= persona.mi_cargo_actual().denominacionpuesto).order_by('-pk')
            paging = MiPaginador(convenio, 20)
            p = 1
            try:
                paginasesion = 1
                if 'paginador' in request.session:
                    paginasesion = int(request.session['paginador'])
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                else:
                    p = paginasesion
                try:
                    page = paging.page(p)
                except:
                    p = 1
                page = paging.page(p)
            except:
                page = paging.page(p)
            request.session['paginador'] = p
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['convenioempresas'] = page.object_list
            data['total'] = len(convenio)
            return render(request, "dir_convenios/view.html", data)

CORREOS_ADICIONALES_ENVIOS_RESPONSABLES_INTERNOS=['vinculacion@unemi.edu.ec', 'rr.ii@unemi.edu.ec', 'practicaspreprofesionales@unemi.edu.ec']
#CORREOS_ADICIONALES_ENVIOS_RESPONSABLES_INTERNOS=['jsanchezm2@unemi.edu.ec', 'jplacesc@unemi.edu.ec']

def enviar_email_convenio(convenio):
    persona = Persona.objects.get(id=convenio.responsableinterno.id)
    send_html_mail(subject="RESPONSABLES INTERNOS DE LOS CONVENIOS",
                   html_template="emails/texto_responsables_internos_convenios.html",
                   data={'sistema': "SGA",
                       'nombre_convenio': convenio.empresaempleadora.nombre,
                       'nombre_persona': '{} {} {}'.format(persona.nombres, persona.apellido1,
                                                           persona.apellido2)
                   },
                   recipient_list=[persona.emails()]+CORREOS_ADICIONALES_ENVIOS_RESPONSABLES_INTERNOS,
                   recipient_list_cc=[],
                   cuenta=CUENTAS_CORREOS[4][1])

def enviar_email_convenio_departamento(persona, convenio):
    persona = Persona.objects.get(id=persona.id)
    send_html_mail(subject="RESPONSABLES INTERNOS DE LOS CONVENIOS",
                   html_template="emails/texto_responsables_internos_convenios.html",
                   data={'sistema': "SGA",
                       'nombre_convenio': convenio.empresaempleadora.nombre,
                       'nombre_persona': '{} {} {}'.format(persona.nombres, persona.apellido1,
                                                           persona.apellido2)
                   },
                   recipient_list=[persona.emails()]+CORREOS_ADICIONALES_ENVIOS_RESPONSABLES_INTERNOS,
                   recipient_list_cc=[],
                   cuenta=CUENTAS_CORREOS[4][1])
