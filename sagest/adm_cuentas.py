# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module
from sagest.forms import CuentaContableForm
from sagest.models import CuentaContable, TipoCuentaContable
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            f = CuentaContableForm(request.POST)
            if f.is_valid():
                try:
                    if CuentaContable.objects.filter(cuenta=f.cleaned_data['cuenta'],status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Registro Repetido."})
                    cuenta = CuentaContable(cuenta=f.cleaned_data['cuenta'],
                                            descripcion=f.cleaned_data['descripcion'],
                                            naturaleza=f.cleaned_data['naturaleza'],
                                            tipo=f.cleaned_data['tipo'],
                                            asociaccosto=f.cleaned_data['asociaccosto'],
                                            partida=f.cleaned_data['partida'],
                                            bodega=f.cleaned_data['bodega'],
                                            activosfijos=f.cleaned_data['activosfijos'])
                    cuenta.save(request)
                    log(u'Adiciono cuenta contablle: %s' % cuenta, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            cuenta = CuentaContable.objects.get(pk=request.POST['id'])
            f = CuentaContableForm(request.POST)
            if f.is_valid():
                try:
                    cuenta.cuenta = f.cleaned_data['cuenta']
                    cuenta.naturaleza = f.cleaned_data['naturaleza']
                    cuenta.descripcion = f.cleaned_data['descripcion']
                    cuenta.tipo = f.cleaned_data['tipo']
                    cuenta.asociaccosto = f.cleaned_data['asociaccosto']
                    cuenta.partida=f.cleaned_data['partida']
                    cuenta.bodega = f.cleaned_data['bodega']
                    cuenta.activosfijos = f.cleaned_data['activosfijos']
                    cuenta.save(request)
                    log(u'Editó cuenta contablle: %s' % cuenta, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                cuenta = CuentaContable.objects.get(pk=request.POST['id'])
                log(u'Eliminó cuenta contablle: %s' % cuenta, request, "del")
                cuenta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Crear cuenta'
                    data['form'] = CuentaContableForm()
                    return render(request, 'adm_cuentas/add.html', data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Modificar cuenta contable'
                    data['cuenta'] = cuenta = CuentaContable.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(cuenta)
                    form = CuentaContableForm(initial=initial)
                    data['form'] = form
                    return render(request, 'adm_cuentas/edit.html', data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar cuenta'
                    data['cuenta'] = CuentaContable.objects.get(pk=request.GET['id'])
                    return render(request, 'adm_cuentas/delete.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestión de cuentas contables'
            search = None
            tipo = None

            if 't' in request.GET:
                tipo = request.GET['t']
                data['tipoid'] = int(tipo) if tipo else ""

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                cuentas = CuentaContable.objects.filter(Q(cuenta__icontains=search) |
                                                        Q(descripcion__icontains=search) |
                                                        Q(tipo__nombre__icontains=search))
            elif tipo:
                cuentas = CuentaContable.objects.filter(tipo__id=tipo)
            else:
                cuentas = CuentaContable.objects.all()

            paging = MiPaginador(cuentas, 25)
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
            data['cuentas'] = page.object_list
            data['tipos_cuentas'] = TipoCuentaContable.objects.all()
            return render(request, "adm_cuentas/view.html", data)
