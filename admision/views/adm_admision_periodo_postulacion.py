# -*- coding: UTF-8 -*-
import sys
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from bd.models import LogQuery
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from django.db import connection, transaction
from django.template import Context
from django.template.loader import get_template
from sga.funciones import log, puede_realizar_accion, puede_realizar_accion_is_superuser, logquery, MiPaginador
from admision.forms import PeriodoForm
from sga.templatetags.sga_extras import encrypt


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

        if action == 'savePeriodo':
            try:
                from admision.models import Periodo
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                form = PeriodoForm(request.POST)
                form.set_periodo(request.POST['periodo'])
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError(v[0])
                if id != 0:
                    ePeriodo = Periodo.objects.get(pk=id)
                    if Periodo.objects.values("id").filter(periodo_id=request.POST['periodo']).exclude(pk=ePeriodo.pk).exists():
                        raise NameError(u"Periodo seleccionado ya se encuentra registrado")
                    ePeriodo.periodo = form.cleaned_data['periodo']
                    ePeriodo.nombre = form.cleaned_data['nombre']
                    ePeriodo.inicio = form.cleaned_data['inicio']
                    ePeriodo.fin = form.cleaned_data['fin']
                    ePeriodo.activo = form.cleaned_data['activo']
                    ePeriodo.save(request)
                    log(u'Edito periodo de postulación de nivelación y admisión: %s' % ePeriodo, request, 'edit')
                else:
                    if Periodo.objects.values("id").filter(periodo_id=request.POST['periodo']).exists():
                        raise NameError(u"Periodo seleccionado ya se encuentra registrado")
                    ePeriodo = Periodo(periodo=request.POST['periodo'],
                                       nombre=form.cleaned_data['nombre'],
                                       inicio=form.cleaned_data['inicio'],
                                       fin=form.cleaned_data['fin'],
                                       activo=form.cleaned_data['activo'])
                    ePeriodo.save(request)
                    log(u'Adiciono periodo de postulación de nivelación y admisión: %s' % ePeriodo, request, 'add')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        elif action == 'deletePeriodo':
            try:
                from admision.models import Periodo
                id = int(encrypt((request.POST.get('id', encrypt('0')))))
                if id == 0:
                    raise NameError(u"No se encontro el parametro de registro a eliminar")
                if not Periodo.objects.values("id").filter(pk=id):
                    raise NameError(u"No se encontro el registro a eliminar")
                ePeriodo = deletePeriodo = Periodo.objects.get(pk=id)
                if not ePeriodo.puede_eliminar():
                    raise NameError(u"No puede eliminar registro de periodo porque existe datos conectados")
                ePeriodo.delete()
                log(u'Elimino periodo de postulación de nivelación y admisión: %s' % deletePeriodo, request, 'del')
                return JsonResponse({"result": True})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, 'mensaje': str(ex)})

        return JsonResponse({"result": False, "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'loadForm':
                try:
                    from admision.models import Periodo
                    id = int(encrypt((request.GET.get('id', encrypt('0')))))
                    ePeriodo = None
                    if id != 0:
                        ePeriodo = Periodo.objects.get(pk=id)
                    form = PeriodoForm()
                    if ePeriodo:
                        form.initial = model_to_dict(ePeriodo)
                        form.set_periodo(ePeriodo.periodo.pk)
                    data['form'] = form
                    data['idForm'] = 'frmPeriodo'
                    data['action'] = 'savePeriodo'
                    data['id'] = id
                    template = get_template("nivelacion_admision/adm_periodo_postulacion/form.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al obtener los datos. %s" % ex.__str__()})

            elif action == 'searchPeriodo':
                try:
                    from sga.models import Periodo
                    q = request.GET['q'].upper().strip()
                    ePeriodos = Periodo.objects.all()
                    search = q.strip()
                    ePeriodos = ePeriodos.filter(Q(nombre__icontains=search) | Q(id__icontains=search))
                    ePeriodos = ePeriodos.distinct().order_by('inicio', 'fin')[:15]
                    aData = {"results": [{"id": x.id, "name": "({}) - {}".format(x.pk, x.nombre)} for x in ePeriodos]}
                    return JsonResponse({"result": True, 'mensaje': '', 'aData': aData})
                except Exception as ex:
                    return JsonResponse({"result": True, 'mensaje': f'{ex.__str__()}', 'aData': {"results": []}})

            return HttpResponseRedirect(request.path)
        else:
            try:
                from admision.models import Periodo
                data['title'] = 'Periodos de postulación'
                data['subtitle'] = 'Administración de periodos de postulación de nivelación y admisión'
                filtros, s, url_vars = Q(status=True), request.GET.get('s', ''), ''
                if s:
                    if s.isdigit():
                        filtros = filtros & (Q(id=s))
                    else:
                        filtros = filtros & (Q(nombre__icontains=s) | Q(periodo__nombre__icontains=s))
                    data['s'] = f"{s}"
                    url_vars += f"&s={s}"
                ePeriodos = Periodo.objects.filter(filtros).order_by('-id')
                paging = MiPaginador(ePeriodos, 25)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['ePeriodos'] = page.object_list
                data['url_vars'] = url_vars
                return render(request, "nivelacion_admision/adm_periodo_postulacion/view.html", data)
            except Exception as ex:
                pass
