# -*- coding: UTF-8 -*-
from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, null_to_decimal
from decorators import secure_module, last_access
from django.contrib.auth.decorators import login_required

# Proceso solicitud anteproyecto
from django.forms import model_to_dict
from edcon.forms import TipoAnteproyectoForm, RequisitoForm, ComponenteAprendizajeForm, ConfigTipoAnteproyectoRequisitoForm, ConfigTipoAnteComponenteApreForm
from edcon.models import SolicitudAnteproyecto, TipoAnteproyecto, Requisito, ComponenteAprendizaje, ConfigTipoAnteproyectoRequisito, ConfigTipoAnteComponenteApre
import sys
from sga.templatetags.sga_extras import encrypt
from django.contrib import messages

@login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        data['action'] = action = request.POST['action']

        # Gestionar solicitud anteproyecto
        if action == 'del':
            with transaction.atomic():
                try:
                    instancia = SolicitudAnteproyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.estado != 1:
                        raise NameError('Acción no permitida. Sólo podrá eliminar mientras el estado de la solicitud sea ingresado.')
                    instancia.status = False
                    for historial in instancia.historialsolicitudcopia_set.filter(status=True):
                        historial.status = False
                        historial.save(request)
                    instancia.save(request)
                    log(u'Eliminó solicitud en gestión solicitud anteproyecto: %s' % instancia, request, "del")
                    res_json = {"error": False}
                    return JsonResponse(res_json, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # tipo anteproyecto
        elif action == 'addtipoanteproyecto':
            with transaction.atomic():
                try:
                    form = TipoAnteproyectoForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = TipoAnteproyecto(descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó tipo anteproyecto en gestión solicitud anteproyecto: %s' % instancia, request, "addtipoanteproyecto")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'edittipoanteproyecto':
            with transaction.atomic():
                try:
                    instancia = TipoAnteproyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = TipoAnteproyectoForm(request.POST)
                    if form.is_valid() and form.validador(instancia.id):
                        instancia.descripcion = form.cleaned_data['descripcion']
                        instancia.save(request)
                        log(u'Editó tipo anteproyecto en gestión solicitud anteproyecto: %s' % instancia, request, "edittipoanteproyecto")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'deltipoanteproyecto':
            with transaction.atomic():
                try:
                    instancia = TipoAnteproyecto.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        raise NameError('Este registro se encuentra en uso, no es posible eliminar.')
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó tipo anteproyecto en gestión solicitud anteproyecto: %s' % instancia, request, "deltipoanteproyecto")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # Requisito
        elif action == 'addrequisito':
            with transaction.atomic():
                try:
                    form = RequisitoForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = Requisito(descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó requisito en gestión solicitud anteproyecto: %s' % instancia, request,
                        "addrequisito")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editrequisito':
            with transaction.atomic():
                try:
                    instancia = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = RequisitoForm(request.POST)
                    if form.is_valid() and form.validador(instancia.id):
                        instancia.descripcion = form.cleaned_data['descripcion']
                        instancia.save(request)
                        log(u'Editó requisito en gestión solicitud anteproyecto: %s' % instancia, request,
                            "editrequisito")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'delrequisito':
            with transaction.atomic():
                try:
                    instancia = Requisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        raise NameError('Este registro se encuentra en uso, no es posible eliminar.')
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó requisito en gestión solicitud anteproyecto: %s' % instancia, request,
                        "delrequisito")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # componenteaprendizaje
        elif action == 'addcomponenteaprendizaje':
            with transaction.atomic():
                try:
                    form = ComponenteAprendizajeForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = ComponenteAprendizaje(descripcion=form.cleaned_data['descripcion'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó componente aprendizaje en gestión solicitud anteproyecto: %s' % instancia, request,
                        "addcomponenteaprendizaje")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editcomponenteaprendizaje':
            with transaction.atomic():
                try:
                    instancia = ComponenteAprendizaje.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ComponenteAprendizajeForm(request.POST)
                    if form.is_valid() and form.validador(instancia.id):
                        instancia.descripcion = form.cleaned_data['descripcion']
                        instancia.save(request)
                        log(u'Editó componente aprendizaje en gestión solicitud anteproyecto: %s' % instancia, request,
                            "editcomponenteaprendizaje")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'delcomponenteaprendizaje':
            with transaction.atomic():
                try:
                    instancia = ComponenteAprendizaje.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        raise NameError(u"Este registro se encuentra en uso, no es posible eliminar.")
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó componente aprendizaje en gestión solicitud anteproyecto: %s' % instancia, request,
                        "delcomponenteaprendizaje")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # config tipo anteproyecto requisito
        elif action == 'addconfigtipoanteproyectorequisito':
            with transaction.atomic():
                    try:
                        form = ConfigTipoAnteproyectoRequisitoForm(request.POST)
                        if form.is_valid() and form.validador():
                            instancia = ConfigTipoAnteproyectoRequisito(tipoanteproyecto=form.cleaned_data['tipoanteproyecto'],
                                                  vigente=form.cleaned_data['vigente']
                                                  )
                            instancia.save(request)
                            for data in form.cleaned_data['requisitos']:
                                instancia.requisitos.add(data)
                            instancia.save(request)
                            # Proceso automático, si el usuario ingresa una configuracion vigente=true,
                            # se coloca en false las demás configuraciones del mismo tipo de anteproyecto, porque sólo debe
                            # haber una configuración vigente por cada tipo de anteproyecto.
                            if instancia.vigente:
                                instancia.desactivar_configuraciones(request)
                                # lista = ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=instancia.tipoanteproyecto, vigente=True).exclude(pk=instancia.id)
                                # for lis in lista:
                                #     lis.vigente = False
                                #     lis.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                 "mensaje": "Error en el formulario"})
                        log(u'Adicionó Requisitos de anteproyectos de Gestión solicitud de anteproyectos: %s' % instancia, request, "addconfigtipoanteproyectorequisito")
                        return JsonResponse({"result": False}, safe=False)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editconfigtipoanteproyectorequisito':
            with transaction.atomic():
                try:
                    filtro = ConfigTipoAnteproyectoRequisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ConfigTipoAnteproyectoRequisitoForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        filtro.tipoanteproyecto = form.cleaned_data['tipoanteproyecto']
                        filtro.vigente = form.cleaned_data['vigente']
                        filtro.save(request)
                        filtro.requisitos.clear()
                        for req in form.cleaned_data['requisitos']:
                            filtro.requisitos.add(req)
                        if filtro.vigente:
                            filtro.desactivar_configuraciones(request)
                        log(u'Editó Requisitos de anteproyectos de Gestión solicitud de anteproyectos: %s' % filtro, request, "editimpresora")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        if action == 'actualizarvigenterequisito':
            with transaction.atomic():
                try:
                    vigente = eval(request.POST['val'].capitalize())
                    # validar que haya una configuración vigente por cada tipo de anteproyecto
                    if not vigente:
                        return JsonResponse({"result": False, 'mensaje': u"Acción no permitida, debe haber una "
                                                                         u"configuración vigente por tipo de anteproyecto."})
                    # Proceso automático, si el usuario ingresa una configuracion como vigente=true, automáticamente
                    # se coloca en false las demás configuraciones del mismo tipo de anteproyecto, porque sólo debe
                    # haber una configuración vigente por tipo de anteporyecto.
                    registro = ConfigTipoAnteproyectoRequisito.objects.get(pk=int(request.POST['id']))
                    registro.vigente = vigente
                    registro.save(request)
                    if vigente:
                        lista = ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=registro.tipoanteproyecto, vigente=True).exclude(pk=int(request.POST['id']))
                        for p in lista:
                            p.vigente = False
                            p.save(request)
                    # # enviar los ids vigentes para renderizar
                    # activos = ConfigTipoAnteproyectoRequisito.objects.filter(status=True, tipoanteproyecto=registro.tipoanteproyecto, vigente=True)
                    log(u'Configurar requisitos de anteproyecto vigente en gestión de solicitud de anteproyectos: %s (%s)' % (registro, registro.vigente), request,"actualizarvigenterequisito")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        elif action == 'activarrequisitos':
            with transaction.atomic():
                try:
                    registro = ConfigTipoAnteproyectoRequisito.objects.get(pk=request.POST['id'])
                    registro.vigente = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    id_desactivar = []
                    if registro.vigente:
                        id_desactivar = registro.desactivar_configuraciones(request)
                    log(u'Configuración requisitos activo : %s (%s)' % (registro, registro.vigente), request, "activarrequisitos")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados', "id_desactivar": id_desactivar})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        elif action == 'delconfigtipoanteproyectorequisito':
            with transaction.atomic():
                try:
                    instancia = ConfigTipoAnteproyectoRequisito.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        raise NameError('Este registro se encuentra en uso, no es posible eliminar.')
                    if instancia.vigente == True:
                        raise NameError('Acción no permitida, no puede eliminar una configuración vigente.')
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Requisitos de anteproyectos de Gestión solicitud de anteproyectos: %s' % instancia, request, "delimpresora")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # config tipo anteproyecto componente aprendizaje
        elif action == 'addconfigtipoantecomponenteapre':
            with transaction.atomic():
                try:
                    form = ConfigTipoAnteComponenteApreForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = ConfigTipoAnteComponenteApre(
                            tipoanteproyecto=form.cleaned_data['tipoanteproyecto'],
                            vigente=form.cleaned_data['vigente']
                            )
                        instancia.save(request)
                        for data in form.cleaned_data['componentesaprendizajes']:
                            instancia.componentesaprendizajes.add(data)
                        instancia.save(request)
                        if instancia.vigente:
                            instancia.desactivar_configuraciones(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó componentes de anteproyectos en Gestión solicitud de anteproyectos: %s' % instancia,
                        request, "addconfigtipoantecomponenteapre")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editconfigtipoantecomponenteapre':
            with transaction.atomic():
                try:
                    filtro = ConfigTipoAnteComponenteApre.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ConfigTipoAnteComponenteApreForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        filtro.tipoanteproyecto = form.cleaned_data['tipoanteproyecto']
                        filtro.vigente = form.cleaned_data['vigente']
                        filtro.save(request)
                        filtro.componentesaprendizajes.clear()
                        for dato in form.cleaned_data['componentesaprendizajes']:
                            filtro.componentesaprendizajes.add(dato)
                        if filtro.vigente:
                            filtro.desactivar_configuraciones(request)
                        log(u'Editó componentes de aprendizajes de tipo anteproyectos de Gestión solicitud de anteproyectos: %s' % filtro,
                            request, "editconfigtipoantecomponenteapre")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

        elif action == 'activarcomponentes':
            with transaction.atomic():
                try:
                    registro = ConfigTipoAnteComponenteApre.objects.get(pk=request.POST['id'])
                    registro.vigente = eval(request.POST['val'].capitalize())
                    registro.save(request)
                    id_desactivar = []
                    if registro.vigente:
                        id_desactivar = registro.desactivar_configuraciones(request)
                    log(u'Configuración componentes activo : %s (%s)' % (registro, registro.vigente), request, "activarcomponentes")
                    return JsonResponse({"result": True, 'mensaje': 'Cambios guardados', "id_desactivar": id_desactivar})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": False})

        elif action == 'delconfigtipoantecomponenteapre':
            with transaction.atomic():
                try:
                    instancia = ConfigTipoAnteComponenteApre.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        raise NameError('Este registro se encuentra en uso, no es posible eliminar.')
                    if instancia.vigente == True:
                        raise NameError('Acción no permitida, no puede eliminar una configuración vigente.')
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó componentes de aprendizajes de tipo anteproyectos de Gestión solicitud de anteproyectos: %s' % instancia,
                        request, "delconfigtipoantecomponenteapre")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']


            # Tipo anteproyecto
            if action == 'tipoanteproyecto':
                try:
                    data['title'] = u'Tipo anteproyecto'
                    search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(descripcion__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = TipoAnteproyecto.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = f'{url_vars}&action={action}'
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 2
                    return render(request, 'adm_gestionsolicitudanteproyecto/viewtipoanteproyecto.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addtipoanteproyecto':
                try:
                    form = TipoAnteproyectoForm()
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formtipoanteproyecto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'edittipoanteproyecto':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    modelo = TipoAnteproyecto.objects.get(pk=id)
                    form = TipoAnteproyectoForm(initial=model_to_dict(modelo))
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formtipoanteproyecto.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # Requisito
            if action == 'requisito':
                try:
                    data['title'] = u'Requisito'
                    search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(descripcion__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = Requisito.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = f'{url_vars}&action={action}'
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 3
                    return render(request, 'adm_gestionsolicitudanteproyecto/viewrequisito.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addrequisito':
                try:
                    form = RequisitoForm()
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editrequisito':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    modelo = Requisito.objects.get(pk=id)
                    form = RequisitoForm(initial=model_to_dict(modelo))
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formrequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # componenteaprendizaje
            elif action == 'componenteaprendizaje':
                try:
                    data['title'] = u'Componentes de aprendizaje'
                    search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(descripcion__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = ComponenteAprendizaje.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = f'{url_vars}&action={action}'
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 4
                    return render(request, 'adm_gestionsolicitudanteproyecto/viewcomponenteaprendizaje.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addcomponenteaprendizaje':
                try:
                    form = ComponenteAprendizajeForm()
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formcomponenteaprendizaje.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editcomponenteaprendizaje':
                        try:
                            data['id'] = id = int(encrypt(request.GET['id']))
                            modelo = ComponenteAprendizaje.objects.get(pk=id)
                            form = ComponenteAprendizajeForm(initial=model_to_dict(modelo))
                            data['form'] = form
                            template = get_template(
                                "adm_gestionsolicitudanteproyecto/modal/formcomponenteaprendizaje.html")
                            return JsonResponse({"result": True, 'data': template.render(data)})
                        except Exception as ex:
                            pass


            # config tipo anteproyecto requisito
            elif action == 'configtipoanteproyectorequisito':
                        try:
                            data['title'] = u'Configuración requisitos'
                            search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                            if search:
                                filtro = filtro & (Q(tipoanteproyecto__descripcion__icontains=search) |
                                                   Q(requisitos__descripcion__icontains=search)
                                                   )
                                url_vars += '&s=' + search
                                data['s'] = search

                            listado = ConfigTipoAnteproyectoRequisito.objects.filter(filtro).order_by('-id').distinct()
                            paging = MiPaginador(listado, 10)
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
                            data["url_vars"] = f'{url_vars}&action={action}'
                            data['listado'] = page.object_list
                            data['listcount'] = len(listado)
                            request.session['viewactivo'] = 5
                            return render(request, 'adm_gestionsolicitudanteproyecto/viewconfigtipoanteproyectorequisito.html', data)
                        except Exception as ex:
                            return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addconfigtipoanteproyectorequisito':
                try:
                    form = ConfigTipoAnteproyectoRequisitoForm()
                    data['form'] = form
                    template = get_template("adm_gestionsolicitudanteproyecto/modal/formconfigtipoanteproyectorequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editconfigtipoanteproyectorequisito':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    instancia = ConfigTipoAnteproyectoRequisito.objects.get(pk=id)
                    # Validar que si la configuración está en uso, no pueda editar el registro sólo el campo vigente
                    if instancia.en_uso():
                        return JsonResponse({'error': True, "message": u"Este registro se encuentra en uso, no es posible editar."},
                                            safe=False)
                    form = ConfigTipoAnteproyectoRequisitoForm(initial=model_to_dict(instancia))
                    data['form'] = form
                    template = get_template("adm_gestionsolicitudanteproyecto/modal/formconfigtipoanteproyectorequisito.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # config tipo anteproyecto componente de aprendizaje
            elif action == 'configtipoantecomponenteapre':
                try:
                    data['title'] = u'Configuración componentes de aprendizajes'
                    search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(tipoanteproyecto__descripcion__icontains=search) |
                                           Q(componentesaprendizajes__descripcion__icontains=search)
                                           )
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = ConfigTipoAnteComponenteApre.objects.filter(filtro).order_by(
                        '-id').distinct()
                    paging = MiPaginador(listado, 10)
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
                    data["url_vars"] = f'{url_vars}&action={action}'
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    request.session['viewactivo'] = 6
                    return render(request,
                                  'adm_gestionsolicitudanteproyecto/viewconfigtipoantecomponenteapre.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})

            elif action == 'addconfigtipoantecomponenteapre':
                try:
                    form = ConfigTipoAnteComponenteApreForm()
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formconfigtipoantecomponenteapre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editconfigtipoantecomponenteapre':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    instancia = ConfigTipoAnteComponenteApre.objects.get(pk=id)
                    # Validar que si la configuración está en uso, no pueda editar el registro sólo el campo vigente
                    if instancia.en_uso():
                        return JsonResponse(
                            {'error': True, "message": u"Este registro se encuentra en uso, no es posible editar."},
                            safe=False)
                    form = ConfigTipoAnteComponenteApreForm(initial=model_to_dict(instancia))
                    data['form'] = form
                    template = get_template(
                        "adm_gestionsolicitudanteproyecto/modal/formconfigtipoantecomponenteapre.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)


        else:
            try:
                data['title'] = u'Gestión de solicitud de anteproyectos'
                search, filtro, url_vars, fechasrango  = request.GET.get('s', '').strip(), Q(status=True), '', request.GET.get('fechas', '').strip()
                if search:
                    # filtro = filtro & (Q(Q(horainicio__icontains=search) | Q(horafin__icontains=search)) | Q(profesor__persona__cedula=str(search)) |
                    #                    Q(detallejornadaimpresora__impresora__impresora__codigotic__icontains=search) |
                    #                    Q(detallejornadaimpresora__impresora__impresora__codigointerno__icontains=search) |
                    #                    Q(detallejornadaimpresora__impresora__impresora__codigogobierno__icontains=search)
                    #                    )
                    url_vars += '&s=' + search
                    data['s'] = search

                if fechasrango:
                    try:
                        fechasrango = fechasrango.split(' - ')
                        desde = datetime.strptime(fechasrango.__getitem__(0), '%d-%m-%Y').date()
                        hasta = datetime.strptime(fechasrango.__getitem__(1), '%d-%m-%Y').date()
                        filtro = filtro & (Q(fecha__range=[desde, hasta]))
                        data[
                            'fechasrango'] = fechasrango = f"{desde.strftime('%d-%m-%Y')} - {hasta.strftime('%d-%m-%Y')}"
                        url_vars += '&fechas=' + fechasrango
                    except Exception as ex:
                        messages.error(request, u"Formato de fecha inválida. No se consideró en la búsqueda.")

                listado = SolicitudAnteproyecto.objects.filter(filtro).order_by('estado','-fecha')
                paging = MiPaginador(listado, 10)
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
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                request.session['viewactivo'] = 1
                return render(request,
                              'adm_gestionsolicitudanteproyecto/viewgestionsolicitudanteproyecto.html',
                              data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})

