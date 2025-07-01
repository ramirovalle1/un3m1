# -*- coding: UTF-8 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from decorators import secure_module, last_access
from sagest.forms import HojaRutaForm
from sagest.models import HojaRuta, DistributivoPersona
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


def rango_anios():
    if HojaRuta.objects.exists():
        inicio = datetime.now().year
        fin = HojaRuta.objects.order_by('fecha')[0].fecha.year
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = HojaRutaForm(request.POST, request.FILES)
                if form.is_valid():
                    if form.cleaned_data['ingreso'] and form.cleaned_data['horasalida'] >= form.cleaned_data['horaingreso']:
                        return JsonResponse({"result": "bad", "mensaje": u"Error en la hora de ingreso."})
                    registro = HojaRuta(fecha=form.cleaned_data['fecha'],
                                        ubicacion=form.cleaned_data['tipodestino'],
                                        destinointerno=form.cleaned_data['destinointerno'],
                                        destinoexterno=form.cleaned_data['destinoexterno'],
                                        actividad=form.cleaned_data['actividad'],
                                        horasalida=form.cleaned_data['horasalida'],
                                        horaingreso=form.cleaned_data['horaingreso'],
                                        observacion=form.cleaned_data['observacion'],
                                        solicitante=form.cleaned_data['solicitante'],
                                        trabajador=persona)
                    registro.save(request)
                    log(u'Registro de actividad hoja de ruta: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'registroingreso':
            try:
                form = HojaRutaForm(request.POST, request.FILES)
                if form.is_valid():
                    registro = HojaRuta.objects.get(pk=request.POST['id'])
                    if form.cleaned_data['horaingreso']:
                        if form.cleaned_data['horaingreso'] < registro.horasalida:
                            return JsonResponse({"result": "bad", "mensaje": u"Hora de ingreso incorrecta."})
                        registro.horaingreso = form.cleaned_data['horaingreso']
                        registro.observacion = form.cleaned_data['observacion']
                        registro.save(request)
                    log(u'Actualizo actividad hoja de ruta: %s' % persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Registro de nueva actividad'
                    data['form'] = HojaRutaForm()
                    return render(request, "th_hojaruta/add.html", data)
                except Exception as ex:
                    pass

            if action == 'registroingreso':
                try:
                    data['title'] = u'Modificacion de registro de actividad'
                    data['actividad'] = actividad = HojaRuta.objects.get(pk=request.GET['id'])
                    form = HojaRutaForm(initial={'fecha': actividad.fecha,
                                                 'tipodestino': actividad.ubicacion,
                                                 'destinointerno': actividad.destinointerno,
                                                 'destinoexterno': actividad.destinoexterno,
                                                 'solicitante': actividad.solicitante,
                                                 'actividad': actividad.actividad,
                                                 'horasalida': str(actividad.horasalida),
                                                 'observacion': actividad.observacion,
                                                 'ingreso': True})
                    form.editar()
                    data['form'] = form
                    return render(request, "th_hojaruta/registroingreso.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if not DistributivoPersona.objects.filter(persona=persona):
                return HttpResponseRedirect('/?info=Ud. no tiene asignado un cargo.')
            data['title'] = u'Hoja de actividades.'
            search = None
            ids = None
            data['anios'] = anios = rango_anios()
            if 'anio' in request.GET:
                request.session['aniohojaruta'] = int(request.GET['anio'])
            if 'aniohojaruta' not in request.session:
                request.session['aniohojaruta'] = anios[0]
            data['anioselect'] = anioselect = request.session['aniohojaruta']

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                plantillas = HojaRuta.objects.filter(Q(trabajador__nombres__icontains=search) |
                                                     Q(trabajador__apellido1__icontains=search) |
                                                     Q(trabajador__apellido2__icontains=search) |
                                                     Q(trabajador__cedula__icontains=search) |
                                                     Q(trabajador__pasaporte__icontains=search), fecha__year=anioselect).distinct().order_by('-id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                plantillas = HojaRuta.objects.filter(id=ids, fecha__year=anioselect).order_by('-fecha')
            else:
                plantillas = HojaRuta.objects.filter(fecha__year=anioselect).order_by('-fecha')
            paging = MiPaginador(plantillas, 20)
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
            data['ids'] = ids if ids else ""
            data['actividades'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'th_hojaruta/view.html', data)