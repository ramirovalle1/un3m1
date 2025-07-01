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
from django.contrib import messages


# Proceso Solicitud Copias
from django.forms import model_to_dict
from helpdesk.forms import SolicitudCopiasForm, ConfiguracionCopiaForm, JornadaImpresoraForm, ImpresoraForm, DetalleJornadaImpresoraForm
from helpdesk.models import ConfiguracionCopia, DetalleJornadaImpresora, SolicitudCopia, HistorialSolicitudCopia, Impresora, JornadaImpresora, ESTADO_SOLICITUD_COPIA
from sga.models import Profesor
import sys
from sga.templatetags.sga_extras import encrypt

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
        data['action'] = action = request.POST['action']

        # Gestionar solicitud copias
        if action == 'del':
            with transaction.atomic():
                try:
                    instancia = SolicitudCopia.objects.get(pk=int(encrypt(request.POST['id'])))
                    # if not instancia.puede_eliminar():
                    #     return JsonResponse({'error': True,
                    #                          "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                    #                         safe=False)
                    if instancia.estado != 1:
                        return JsonResponse({'error': True,
                                             "message": u"Acción no permitida. Sólo podrá eliminar mientras su solicitud esté en estado solicitado."},
                                            safe=False)
                    instancia.status = False
                    for historialsolicitudcopia in instancia.historialsolicitudcopia_set.filter(status=True):
                        historialsolicitudcopia.status = False
                        historialsolicitudcopia.save(request)
                    instancia.save(request)
                    log(u'Eliminó Solicitud de Solicitud de copias: %s' % instancia, request, "del")
                    # log(u'Eliminó Historial de Solicitud de copias: %s' % instancia.historialsolicitudcopia_set.filter(status=True), request, "del")
                    res_json = {"error": False}
                    return JsonResponse(res_json, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        elif action == 'atender':
            with transaction.atomic():
                try:
                    solicitudcopia = SolicitudCopia.objects.get(pk=int(encrypt(request.POST['idpadre'])))
                    observacionhistorial = request.POST['observacionhistorial']
                    estadohistorial = int(request.POST['estadohistorial'])
                    #  validar que se ingrese la observación y estado de la solicitud a atender
                    if not (observacionhistorial and estadohistorial):
                        return JsonResponse(
                            {'result': False, "mensaje": "Por favor, ingrese una observación y seleccione el estado."})
                    # validar que no exista registro con estado 2 = Atendido
                    if HistorialSolicitudCopia.objects.filter(status=True, solicitudcopia_id=solicitudcopia.id, estado=estadohistorial).exists():
                        return JsonResponse(
                            {'result': False, "mensaje": "Advertencia, ésta solicitud ya fue registrada como atendida."})

                    instancia = HistorialSolicitudCopia(solicitudcopia_id=solicitudcopia.id,
                                                        fecha=datetime.now().date(),
                                                        persona=persona,
                                                        observacion=observacionhistorial,
                                                        estado=estadohistorial
                                                        )
                    solicitudcopia.estado = 2
                    solicitudcopia.save(request)
                    instancia.save(request)
                    log(u'Atendió la solicitud en Gestión solicitud de copias: %s' % instancia, request, "atender")
                    return JsonResponse({"result": True, "mensaje": "Solicitud atendida exitosamente."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        # Configuración copias
        elif action == 'addconfiguracioncopia':
            with transaction.atomic():
                try:
                    form = ConfiguracionCopiaForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = ConfiguracionCopia(cantidad=form.cleaned_data['cantidad'],
                                              tiempo=form.cleaned_data['tiempo'])
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó Configuración Copia de Gestión Solicitud copias: %s' % instancia, request, "addconfiguracioncopia")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editconfiguracioncopia':
            with transaction.atomic():
                try:
                    filtro = ConfiguracionCopia.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ConfiguracionCopiaForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        filtro.cantidad = form.cleaned_data['cantidad']
                        filtro.tiempo = form.cleaned_data['tiempo']
                        filtro.save(request)
                        log(u'Editó Configuración Copia de Gestión Solicitud copias: %s' % filtro, request, "editconfiguracioncopia")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'delconfiguracioncopia':
            with transaction.atomic():
                try:
                    instancia = ConfiguracionCopia.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        return JsonResponse({'error': True, "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                        safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Configuración Copia de Gestión Solicitud copias: %s' % instancia, request, "delconfiguracioncopia")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # Jornada Impresora
        elif action == 'addjornadaimpresora':
            with transaction.atomic():
                try:
                    form = JornadaImpresoraForm(request.POST)
                    if form.is_valid() and form.validador():
                        instance = JornadaImpresora(
                                             dia=form.cleaned_data['dia'],
                                             comienza=form.cleaned_data['comienza'],
                                             termina=form.cleaned_data['termina']
                                             )

                        instance.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó Jornada Impresora: %s' % instance, request, "addjornadaimpresora")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editjornadaimpresora':
            with transaction.atomic():
                try:
                    id = int(encrypt(request.POST['id']))
                    filtro = JornadaImpresora.objects.get(pk=id)
                    form = JornadaImpresoraForm(request.POST)
                    if form.is_valid() and form.validador(id):
                        filtro.dia = form.cleaned_data['dia']
                        filtro.comienza = form.cleaned_data['comienza']
                        filtro.termina = form.cleaned_data['termina']
                        filtro.save(request)
                        log(u'Editó Jornada Impresora: %s' % filtro, request, "editjornadaimpresora")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'deljornadaimpresora':
            with transaction.atomic():
                try:
                    instancia = JornadaImpresora.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        return JsonResponse({'error': True, "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                        safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Jornada de Impresora: %s' % instancia, request, "deljornadaimpresora")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # Impresora
        elif action == 'addimpresora':
            with transaction.atomic():
                try:
                    form = ImpresoraForm(request.POST)
                    if form.is_valid() and form.validador():
                        instancia = Impresora(impresora=form.cleaned_data['impresora'],
                                              configuracioncopia=form.cleaned_data['configuracioncopia']
                        )
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó Impresora de Gestión Solicitud copias: %s' % instancia, request, "addimpresora")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editimpresora':
            with transaction.atomic():
                try:
                    filtro = Impresora.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = ImpresoraForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id):
                        filtro.impresora = form.cleaned_data['impresora']
                        filtro.configuracioncopia = form.cleaned_data['configuracioncopia']
                        filtro.save(request)
                        log(u'Editó Impresora de Gestión Solicitud copias: %s' % filtro, request, "editimpresora")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'delimpresora':
            with transaction.atomic():
                try:
                    instancia = Impresora.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        return JsonResponse({'error': True, "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                        safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Impresora de Gestión Solicitud copias: %s' % instancia, request, "delimpresora")
                    res_json = {"error": False}
                except Exception as ex:
                    transaction.set_rollback(True)
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        # Detalle impresora jornada
        elif action == 'adddetalleimpresora':
            with transaction.atomic():
                try:
                    form = DetalleJornadaImpresoraForm(request.POST)
                    idpadre = int(encrypt(request.POST['idpadre']))
                    if form.is_valid() and form.validador(idpadre=idpadre):
                        instancia = DetalleJornadaImpresora(impresora_id=idpadre,
                                                 jornadaimpresora=form.cleaned_data['jornadaimpresora'],
                                                 )
                        instancia.save(request)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                    log(u'Adicionó Detalle de jornadas en Impresora: %s' % instancia, request, "adddetalleimpresora")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'editdetalleimpresora':
            with transaction.atomic():
                try:
                    filtro = DetalleJornadaImpresora.objects.get(pk=int(encrypt(request.POST['id'])))
                    form = DetalleJornadaImpresoraForm(request.POST)
                    if form.is_valid() and form.validador(filtro.id, filtro.impresora.id):
                        filtro.jornadaimpresora = form.cleaned_data['jornadaimpresora']
                        filtro.save(request)
                        log(u'Editó Detalle de jornadas en Impresora: %s' % filtro, request, "editdetalleimpresora")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse(
                            {'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)


        elif action == 'deldetalleimpresora':
            with transaction.atomic():
                try:
                    instancia = DetalleJornadaImpresora.objects.get(pk=int(encrypt(request.POST['id'])))
                    if instancia.en_uso():
                        return JsonResponse({'error': True,
                                             "message": u"Este registro se encuentra en uso, no es posible eliminar."},
                                            safe=False)
                    instancia.status = False
                    instancia.save(request)
                    log(u'Eliminó Detalle de jornadas en Impresora: %s' % instancia, request, "deldetalleimpresora")
                    res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


    else:
        if 'action' in request.GET:

            data['action'] = action = request.GET['action']


            if action == 'detalle':
                try:
                    data = {}
                    data['solicitudcopia'] = instancia = SolicitudCopia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['detalle'] = instancia.historial_ordenascendente()
                    template = get_template("helpdesk_pro_solicitudcopia/modal/formdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False,
                                         "mensaje": u"Error al obtener los datos {}. \n Error on line {}".format(ex, sys.exc_info()[-1].tb_lineno)})


            elif action == 'atender':
                try:
                    data = {}
                    data['solicitudcopia'] = instancia = SolicitudCopia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['historial'] = instancia.historial_ordenascendente().first()
                    data['gestor'] = {'persona': persona,
                                      'fechaactual': datetime.now().date(),
                                      'estado': ESTADO_SOLICITUD_COPIA[1:],
                                      }
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formatendersolicitud.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False,
                                         "mensaje": u"Error al obtener los datos {}. \n Error on line {}".format(ex, sys.exc_info()[-1].tb_lineno)})


            # Configuración copias
            elif action == 'configuracioncopia':
                try:
                    data['title'] = u'Configuración velocidad de impresión'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(cantidad__icontains=search) | Q(tiempo__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = ConfiguracionCopia.objects.filter(filtro).order_by('-id')
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
                    return render(request, 'helpdesk_adm_gestionsolicitudcopia/viewconfiguracioncopia.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addconfiguracioncopia':
                try:
                    form = ConfiguracionCopiaForm()
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formconfiguracioncopia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editconfiguracioncopia':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    configuracioncopia = ConfiguracionCopia.objects.get(pk=id)
                    form = ConfiguracionCopiaForm(initial=model_to_dict(configuracioncopia))
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formconfiguracioncopia.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # Jornada Impresora
            elif action == 'jornadaimpresora':
                try:
                    data['title'] = u'Jornadas de impresoras'
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True), ''
                    if search:
                        # dia = unaccent(dia).upper()
                        filtro = filtro & (Q(comienza__icontains=search) | Q(termina__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = JornadaImpresora.objects.filter(filtro).order_by('-id')
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
                    return render(request, 'helpdesk_adm_gestionsolicitudcopia/viewjornadaimpresora.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addjornadaimpresora':
                try:
                    form = JornadaImpresoraForm()
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formjornadaimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editjornadaimpresora':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = JornadaImpresora.objects.get(pk=request.GET['id'])
                    form = JornadaImpresoraForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formjornadaimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # Impresoras
            elif action == 'impresora':
                try:
                    data['title'] = u'Impresoras'
                    search, filtro, url_vars = request.GET.get('s', '').strip(), Q(status=True), ''
                    if search:
                        filtro = filtro & (Q(impresora__codigotic__icontains=search) | Q(impresora__codigointerno__icontains=search)
                            | Q(impresora__codigogobierno__icontains=search) | Q(impresora__descripcion__icontains=search)
                            | Q(impresora__serie__icontains=search) | Q(impresora__modelo__icontains=search)
                            | Q(impresora__marcaactivo__descripcion__icontains=search) | Q(impresora__ubicacion__nombre__icontains=search)
                            | Q(impresora__ubicacion__responsable__cedula__icontains=search)
                            | Q(configuracioncopia__cantidad__icontains=search) | Q(configuracioncopia__tiempo__icontains=search)
                        )
                        # buscar responsable por cédula, apellidos y nombres
                        ss = search.strip().split(' ')
                        if len(ss) == 2:
                            filtro = filtro | ((Q(impresora__ubicacion__responsable__apellido1__icontains=ss.__getitem__(0)) & Q(impresora__ubicacion__responsable__apellido2__icontains=ss.__getitem__(1)))
                                            | (Q(impresora__ubicacion__responsable__nombres__icontains=f'{ss.__getitem__(0)} {ss.__getitem__(1)}')))
                        elif len(ss) == 3:
                            filtro = filtro | (Q(impresora__ubicacion__responsable__apellido1__icontains=ss.__getitem__(0)) & Q(impresora__ubicacion__responsable__apellido2__icontains=ss.__getitem__(1))
                                               & Q(impresora__ubicacion__responsable__nombres__icontains=f'{ss.__getitem__(2)}'))
                        elif len(ss) == 4:
                            filtro = filtro | (Q(impresora__ubicacion__responsable__apellido1__icontains=ss.__getitem__(0)) & Q(impresora__ubicacion__responsable__apellido2__icontains=ss.__getitem__(1))
                                    & Q(impresora__ubicacion__responsable__nombres__icontains=f'{ss.__getitem__(2)} {ss.__getitem__(3)}'))
                        else:
                            filtro = filtro | (Q(impresora__ubicacion__responsable__apellido1__icontains=search) |
                                    Q(impresora__ubicacion__responsable__apellido2__icontains=search) |
                                    Q(impresora__ubicacion__responsable__nombres__icontains=search))
                        # buscar responsable por cédula, apellidos y nombres
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = Impresora.objects.filter(filtro).order_by('-id')
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
                    return render(request, 'helpdesk_adm_gestionsolicitudcopia/viewimpresora.html', data)
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': '{}'.format(ex)})


            elif action == 'addimpresora':
                try:
                    form = ImpresoraForm()
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            elif action == 'editimpresora':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    instancia = Impresora.objects.get(pk=id)
                    form = ImpresoraForm(initial=model_to_dict(instancia))
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # Detalle impresora jornada
            if action == 'detalleimpresora':
                try:
                    data['title'] = u'Jornadas de disponibilidad de las impresoras'
                    data['idpadre']=idimpresora=int(encrypt(request.GET['id']))
                    search, filtro, url_vars = request.GET.get('s', ''), Q(status=True, impresora_id=idimpresora), ''
                    # Buscar por impresora jornadas (dia y hora de inicio y fin)
                    if search:
                        # buscar por dia
                        diaentero = 0
                        dias = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                        acento, sinacento = 'áéíóúüñÁÉÍÓÚÜÑ', 'aeiouunAEIOUUN'
                        diasinacento = search.lower().translate(str.maketrans(acento,sinacento))
                        if diasinacento in dias:
                            diaentero =  (dias.index(diasinacento)) + 1
                        # buscar por dia
                        filtro = filtro & (Q(jornadaimpresora__dia=diaentero) |
                                           Q(jornadaimpresora__comienza__icontains=search) |
                                           Q(jornadaimpresora__termina__icontains=search))
                        url_vars += '&s=' + search
                        data['s'] = search

                    listado = DetalleJornadaImpresora.objects.filter(filtro).order_by('-id')
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
                    data['listado'] = page.object_list
                    data['listcount'] = len(listado)
                    data['impresora']=Impresora.objects.get(id=idimpresora)
                    data["url_vars"] = f'{url_vars}&action={action}&id={encrypt(idimpresora)}'
                    request.session['viewactivo'] = 4
                    return render(request, 'helpdesk_adm_gestionsolicitudcopia/viewdetalleimpresora.html', data)
                except Exception as ex:
                    return render({'result': False, 'mensaje': '{}'.format(ex)})


            if action == 'adddetalleimpresora':
                try:
                    form = DetalleJornadaImpresoraForm()
                    data['idpadre']=request.GET['idp']
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formdetalleimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            if action == 'editdetalleimpresora':
                try:
                    data['id'] = id = int(encrypt(request.GET['id']))
                    data['filtro'] = filtro = DetalleJornadaImpresora.objects.get(pk=id)
                    form = DetalleJornadaImpresoraForm(initial=model_to_dict(filtro))
                    data['form'] = form
                    template = get_template("helpdesk_adm_gestionsolicitudcopia/modal/formdetalleimpresora.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Gestión solicitud de copias'
                # stardate = datetime.now().strftime('%Y-%m-%d')
                # enddate = stardate
                # ids=[]
                # horarios = Impresora.objects.filter(status=True, mostrar=True).order_by('responsableservicio__servicio_id').distinct('responsableservicio__servicio_id')
                # for horario in horarios:
                #     if horario.fechafin >= hoy:
                #         ids.append(horario.responsableservicio.servicio.id)
                search, filtro, url_vars, fechasrango, hora = request.GET.get('s', ''), Q(status=True), '', request.GET.get('fechas', '').strip(), request.GET.get('hora', '').strip()
                if search:
                    filtro = filtro & (Q(Q(horainicio__icontains=search) | Q(horafin__icontains=search)) | Q(profesor__persona__cedula=str(search)) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigotic__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigointerno__icontains=search) |
                                       Q(detallejornadaimpresora__impresora__impresora__codigogobierno__icontains=search)
                                       )
                    url_vars += '&s=' + search
                    data['s'] = search

                if fechasrango:
                    try:
                        fechasrango = fechasrango.split(' - ')
                        desde = datetime.strptime(fechasrango.__getitem__(0), '%d-%m-%Y').date()
                        hasta = datetime.strptime(fechasrango.__getitem__(1), '%d-%m-%Y').date()
                        filtro = filtro & (Q(fechaagendada__range=[desde, hasta]))
                        data[
                            'fechasrango'] = fechasrango = f"{desde.strftime('%d-%m-%Y')} - {hasta.strftime('%d-%m-%Y')}"
                        url_vars += '&fechas=' + fechasrango
                    except Exception as ex:
                        messages.error(request, u"Formato de fecha inválida. No se consideró en la búsqueda.")

                if hora:
                    hora = datetime.strptime(hora, '%H:%M').time()
                    filtro = filtro & (Q(horainicio__lte=hora, horafin__gte=hora))
                    data['hora'] = hora = hora.strftime('%H:%M')
                    url_vars += '&hora=' + hora

                listado = SolicitudCopia.objects.filter(filtro).order_by('estado', '-id')
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
                return render(request, 'helpdesk_adm_gestionsolicitudcopia/viewgestionsolicitudescopias.html', data)
            except Exception as ex:
                return render({'result': False, 'mensaje': '{}'.format(ex)})

def segundos_a_horaminutosegundo(tiempoensegundos):
    horas = int(tiempoensegundos / 60 / 60)
    tiempoensegundos -= horas * 60 * 60
    minutos = int(tiempoensegundos / 60)
    tiempoensegundos -= minutos * 60
    return f"{horas:02d}:{minutos:02d}:{tiempoensegundos:02d}"