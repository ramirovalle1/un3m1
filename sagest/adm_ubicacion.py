# -*- coding: UTF-8 -*-
import json
import sys

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from sagest.forms import UbicacionesForm
from sagest.funciones import encrypt_id
from sagest.models import Ubicacion
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from sga.models import Persona
from sga.templatetags.sga_extras import encrypt
from utils.filtros_genericos import filtro_persona_select


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addubicacion':
            try:
                f = UbicacionesForm(request.POST)
                if f.is_valid():
                    ubicacion = Ubicacion(codigo=f.cleaned_data['codigo'],
                                          nombre=f.cleaned_data['nombre'],
                                          observacion=f.cleaned_data['observacion'],
                                          bloquepertenece=f.cleaned_data['bloquepertenece'],
                                          responsable=f.cleaned_data['responsable'])
                    ubicacion.save(request)
                    log(u'Adiciono una nueva Ubicación: %s' % ubicacion, request, "add")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                 transaction.set_rollback(True)
                 return JsonResponse({'result': True, 'mensaje': f'{ex}'})

        elif action == 'editubicacion':
            try:
                f = UbicacionesForm(request.POST)
                if f.is_valid():
                    ubicacion = Ubicacion.objects.get(pk=request.POST['id'])
                    ubicacion.codigo = f.cleaned_data['codigo']
                    ubicacion.nombre = f.cleaned_data['nombre']
                    ubicacion.observacion = f.cleaned_data['observacion']
                    ubicacion.bloquepertenece = f.cleaned_data['bloquepertenece']
                    ubicacion.responsable = f.cleaned_data['responsable']
                    ubicacion.save(request)
                    log(u'Edito una  ubicacion: %s' % ubicacion, request, "edit")
                    return JsonResponse({'result': False, 'mensaje': 'Guardado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'{ex}'})

        if action == 'deleteubicacion':
            try:
                ubicacion = Ubicacion.objects.get(pk=encrypt_id(request.POST['id']))
                ubicacion.status = False
                ubicacion.save(request)
                log(u'Elimino una ubicacion: %s' % ubicacion, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'addubicacion':
                try:
                    data['title'] = u'Adicionar ubicación'
                    form = UbicacionesForm()
                    form.fields['responsable'].queryset = Persona.objects.none()
                    data['form'] = form
                    template = get_template('adm_ubicacion/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'editubicacion':
                try:
                    data['title'] = u'Editar Ubicación'
                    ubicacion = Ubicacion.objects.get(pk=encrypt(request.GET['id']))
                    form = UbicacionesForm(initial=model_to_dict(ubicacion))
                    data['id'] = request.GET['id']
                    data['form'] = form
                    form.fields['responsable'].queryset = Persona.objects.none()
                    if ubicacion.responsable:
                        form.fields['responsable'].queryset = Persona.objects.filter(id=ubicacion.responsable.id)
                    template = get_template('adm_ubicacion/add.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    messages.error(request, f'{ex}')

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            try:

                data['title'] = u'Gestión de Ubicación'
                search = None
                ids = None
                url_vars = ''
                if 's' in request.GET:
                    data['s'] = search = request.GET['s']
                if search:
                    url_vars += f'&s={search}'
                    ubicacion = Ubicacion.objects.filter((Q(nombre__icontains=search) | Q(observacion__icontains=search) |
                                                          Q(codigo__icontains=search) | Q(responsable__nombres__icontains=search) |
                                                          Q(responsable__apellido1__icontains=search) |
                                                          Q(responsable__apellido2__icontains=search)),status=True )
                elif 'id' in request.GET:
                    ids = request.GET['id']
                    url_vars += f'&id={ids}'
                    ubicacion = Ubicacion.objects.filter(id=ids)
                else:
                    ubicacion = Ubicacion.objects.filter(status=True).order_by('id')
                paging = MiPaginador(ubicacion, 10)
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
                data['url_vars'] = url_vars
                data['listubicaciones'] = page.object_list
                return render(request, "adm_ubicacion/view.html", data)
            except Exception as ex:
                messages.error(request, f'{ex}')