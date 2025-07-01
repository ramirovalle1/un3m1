# -*- coding: latin-1 -*-
from googletrans import Translator
from django.contrib.auth.decorators import login_required
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import IpPermitidaForm
from sga.funciones import log, MiPaginador
from sga.models import IpPermitidas


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = IpPermitidaForm(request.POST)
                if not f.is_valid():
                    raise NameError('Formulario no valido')
                ippermitidas = IpPermitidas(ip=f.cleaned_data['ip'],
                                            observacion=f.cleaned_data['observacion'],
                                            habilitado=f.cleaned_data['habilitado'],
                                            valida_clase=f.cleaned_data['valida_clase'],
                                            )
                ippermitidas.save(request)
                log(u'Adiciono ip: %s' % ippermitidas, request, "add")
                return JsonResponse({"result": "ok", "id": ippermitidas.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'edit':
            try:
                ippermitidas = IpPermitidas.objects.get(pk=request.POST['id'])
                f = IpPermitidaForm(request.POST)
                if not f.is_valid():
                    raise NameError('Formulario no valido')
                ippermitidas.ip = f.cleaned_data['ip']
                ippermitidas.observacion = f.cleaned_data['observacion']
                ippermitidas.habilitado = f.cleaned_data['habilitado']
                ippermitidas.valida_clase = f.cleaned_data['valida_clase']
                ippermitidas.save(request)
                log(u'Modifico ip: %s' % ippermitidas, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

        elif action == 'delete':
            try:
                ippermitidas = IpPermitidas.objects.get(pk=request.POST['id'])
                log(u'Elimino ip: %s' % ippermitidas, request, "del")
                ippermitidas.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Ips Permitidas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar Ip'
                    data['form'] = IpPermitidaForm(initial={'habilitado': True, 'valida_clase': False})
                    return render(request, "adm_ippermitida/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Ip'
                    ippermitidas = IpPermitidas.objects.get(pk=request.GET['id'])
                    f = IpPermitidaForm(initial={'ip': ippermitidas.ip,
                                                 'observacion': ippermitidas.observacion,
                                                 'habilitado': ippermitidas.habilitado,
                                                 'valida_clase': ippermitidas.valida_clase})
                    data['form'] = f
                    data['ippermitida'] = ippermitidas
                    return render(request, "adm_ippermitida/edit.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete':
                try:
                    data['title'] = u'Eliminar Ip'
                    data['ippermitida'] = IpPermitidas.objects.get(pk=request.GET['id'])
                    return render(request, "adm_ippermitida/delete.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ippermitidas = IpPermitidas.objects.filter(Q(ip__icontains=search) | Q(observacion__icontains=search)).order_by('ip')
            elif 'id' in request.GET:
                ids = request.GET['id']
                ippermitidas = IpPermitidas.objects.filter(id=ids)
            else:
                ippermitidas = IpPermitidas.objects.all().order_by('ip')
            paging = MiPaginador(ippermitidas, 25)
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
            data['ippermitidas'] = page.object_list
            return render(request, "adm_ippermitida/view.html", data)
