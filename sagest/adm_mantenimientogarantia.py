# -*- coding: latin-1 -*-
import io
import json
import os
import sys
import pyqrcode
from django.contrib import messages

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sagest.forms import  PeriodoGarantiaMantenimientoATForm
from sagest.models import PeriodoGarantiaMantenimientoAT
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from django.template.loader import get_template
from django.forms import model_to_dict
from sga.models import Notificacion
from sagest.funciones import dominio_sistema_base, encrypt_id
from sga.templatetags.sga_extras import encrypt

unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    dominio_sistema = dominio_sistema_base(request)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            # PERIODO
            if action =='addperiodo':
                with transaction.atomic():
                    try:
                        form=PeriodoGarantiaMantenimientoATForm(request.POST)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            form_error = [{k: v[0]} for k, v in form.errors.items()]
                            return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                        periodo=PeriodoGarantiaMantenimientoAT(nombre=form.cleaned_data['nombre'],
                                                               fechafin=form.cleaned_data['fechafin'],
                                                               fechainicio=form.cleaned_data['fechainicio'],
                                                               detalle=form.cleaned_data['detalle'])

                        periodo.save(request)
                        log(f'Adiciono periodo de mantenimiento de garantia: {periodo}', request, 'add')
                        return JsonResponse({'result': False,'mensaje':'Guardado con exito'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action =='editperiodo':
                with transaction.atomic():
                    try:
                        id=encrypt_id(request.POST['id'])
                        periodo=PeriodoGarantiaMantenimientoAT.objects.get(id=id)
                        form=PeriodoGarantiaMantenimientoATForm(request.POST,instancia=periodo)
                        if not form.is_valid():
                            transaction.set_rollback(True)
                            form_error = [{k: v[0]} for k, v in form.errors.items()]
                            return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                        periodo.nombre=form.cleaned_data['nombre']
                        periodo.fechafin=form.cleaned_data['fechafin']
                        periodo.fechainicio=form.cleaned_data['fechainicio']
                        periodo.detalle=form.cleaned_data['detalle']
                        periodo.save(request)
                        log(f'Edito periodo de mantenimiento de garantía: {periodo}', request, 'edit')
                        return JsonResponse({'result': False,'mensaje':'Guardado con éxito'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, 'mensaje': str(ex)})

            elif action == 'activarperiodo':
                with transaction.atomic():
                    try:
                        registro = PeriodoGarantiaMantenimientoAT.objects.get(pk=encrypt_id(request.POST['id']))
                        registro.mostrar = eval(request.POST['val'].capitalize())
                        registro.save(request)
                        log(u'Activo periodo: %s (%s)' % (registro, registro.mostrar), request, "edit")
                        return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": False})

            elif action == 'delperiodo':
                try:
                    with transaction.atomic():
                        instancia = PeriodoGarantiaMantenimientoAT.objects.get(pk=encrypt_id(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Elimino periodo de garantida de mantenimiento: %s' % instancia, request, "del")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action']= action = request.GET['action']
            # PERIODO
            if action =='addperiodo':
                try:
                    form=PeriodoGarantiaMantenimientoATForm()
                    data['form']=form
                    template=get_template('adm_mantenimientogarantia/modal/formperiodo.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action =='editperiodo':
                try:
                    id=encrypt_id(request.GET['id'])
                    periodo=PeriodoGarantiaMantenimientoAT.objects.get(id=id)
                    form=PeriodoGarantiaMantenimientoATForm(initial=model_to_dict(periodo))
                    data['form']=form
                    data['id']=id
                    template=get_template('adm_mantenimientogarantia/modal/formperiodo.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Periodos de garantía'
                search, url_vars,filtro = request.GET.get('s', ''), '', Q(status=True)
                if search:
                    filtro = filtro & Q(nombre__icontains=search)
                    url_vars += f"&s={search}"
                periodo = PeriodoGarantiaMantenimientoAT.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(periodo, 25)
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
                data['listado'] = page.object_list
                data['url_vars'] = url_vars
                request.session['viewactivo']=1
                return render(request, "adm_mantenimientogarantia/view.html", data)
            except Exception as ex:
                pass






