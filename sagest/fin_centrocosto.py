# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.commonviews import anio_ejercicio
from sagest.forms import CostosForm, CentroCostoSaldoForm
from sagest.models import AnioEjercicio, CentroCosto
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcostos':
            try:
                form = CostosForm(request.POST)
                if form.is_valid():
                    registro = CentroCosto(nombre=form.cleaned_data['nombre'])
                    registro.save(request)
                    registro.saldo_periodo(anio)
                    log(u'Registro nuevo costo: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'asignar':
            try:
                form = CentroCostoSaldoForm(request.POST)
                if form.is_valid():
                    costo = CentroCosto.objects.get(pk=int(request.POST['id']))
                    saldocosto = form.cleaned_data['partida']
                    saldocosto.centrocosto = costo
                    saldocosto.save(request)
                    log(u'Registro asigno saldo: %s' % costo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'editcosto':
            try:
                form = CostosForm(request.POST)
                if form.is_valid():
                    registro = CentroCosto.objects.get(pk=int(request.POST['id']))
                    registro.nombre = form.cleaned_data['nombre']
                    registro.save(request)
                    log(u'Registro modificado Rubros: %s' % registro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        if action == 'deletecosto':
            try:
                campo = CentroCosto.objects.get(pk=request.POST['id'], status=True)
                if campo.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": "El campo se encuentra en uso."})
                campo.delete()
                log(u'Elimino campos contratos: %s' % campo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addcostos':
                try:
                    data['title'] = u'Nuevo Costo'
                    data['form'] = CostosForm()
                    return render(request, "fin_centrocosto/addcostos.html", data)
                except Exception as ex:
                    pass

            if action == 'editcostos':
                try:
                    data['title'] = u'Modificación Centro de Costo'
                    data['costo'] = costo = CentroCosto.objects.get(pk=request.GET['id'])
                    form = CostosForm(initial={'nombre': costo.nombre})
                    data['form'] = form
                    return render(request, "fin_centrocosto/editcosto.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecosto':
                try:
                    data['title'] = u'Eliminar Costo'
                    data['costo'] = CentroCosto.objects.get(pk=request.GET['id'])
                    return render(request, 'fin_centrocosto/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Centro de Costos'
            search = None
            tipo = None
            if 's' in request.GET:
                search = request.GET['s']
            if search:
                costo = CentroCosto.objects.filter(nombre__icontains=search)
            else:
                costo = CentroCosto.objects.filter(status=True)
            paging = MiPaginador(costo, 25)
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
            data['anio'] = anio
            data['mianio'] = anio
            data['costos'] = page.object_list
            data['anios'] = AnioEjercicio.objects.all()
            return render(request, 'fin_centrocosto/view.html', data)