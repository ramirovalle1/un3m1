# -*- coding: UTF-8 -*-
import sys

from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.core.checks import messages
from django.db import transaction
from django.db.models import Q, Case, When, Value
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template

from decorators import secure_module, last_access
from sagest.forms import ResolucionForm, SesionForm, ResolucionSesionForm, TipoResolucionForm
from sagest.funciones import encrypt_id
from sagest.models import Resoluciones, TipoResolucion, SesionResolucion
from settings import EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addtipo':
            try:
                form = TipoResolucionForm(request.POST)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                sesion = TipoResolucion(nombre=form.cleaned_data['nombre'])
                sesion.save(request)
                log(f'Adiciono tipo de resolución {sesion}', request, 'add')

                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'edittipo':
            try:
                id = encrypt_id(request.POST['id'])
                tipo = TipoResolucion.objects.get(id=id)
                form = TipoResolucionForm(request.POST)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                tipo.nombre = form.cleaned_data['nombre']
                tipo.save(request)
                log(f'Edito tipo de resoucion {tipo}', request, 'edit')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'deltipo':
            try:
                sesion = TipoResolucion.objects.get(pk=encrypt_id(request.POST['id']))
                sesion.status = False
                sesion.save(request)
                log(u'Elimino Sesion: %s' % sesion, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'addsesion':
            try:
                idp = encrypt_id(request.POST['idp'])
                tipo = TipoResolucion.objects.get(id=idp)
                form = SesionForm(request.POST)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                sesion = SesionResolucion(nombre=form.cleaned_data['nombre'],
                                          orden=form.cleaned_data['orden'],
                                          fecha=hoy,
                                          tipo=tipo)
                sesion.save(request)
                log(f'Adiciono una sesión de resolución {sesion}', request, 'add')

                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editsesion':
            try:
                id = encrypt_id(request.POST['id'])
                sesion = SesionResolucion.objects.get(id=id)
                form = SesionForm(request.POST)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                sesion.nombre = form.cleaned_data['nombre']
                sesion.orden = form.cleaned_data['orden']
                sesion.save(request)
                log(f'Edito sesión de resolución {sesion}', request, 'edit')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delsesion':
            try:
                sesion = SesionResolucion.objects.get(pk=encrypt_id(request.POST['id']))
                sesion.status = False
                sesion.save(request)
                log(u'Elimino Sesion: %s' % sesion, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        if action == 'addresolucion':
            try:
                idp = encrypt_id(request.POST['idp'])
                id = encrypt_id(request.POST['id'])

                form = ResolucionSesionForm(request.POST, request.FILES)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})

                sesion_ = None
                if id == 0:
                    sesion_ = SesionResolucion.objects.get(id=idp)
                    tipo = sesion_.tipo
                else:
                    tipo = TipoResolucion.objects.get(id=id)
                resolucion = Resoluciones(tipo=tipo,
                                          sesion=sesion_,
                                          orden=form.cleaned_data['orden'],
                                          fecha=form.cleaned_data['fecha'],
                                          resuelve=form.cleaned_data['resuelve'],
                                          numeroresolucion=form.cleaned_data['numeroresolucion'])
                resolucion.save(request)
                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre('documento_resolucion', newfile._name)
                    resolucion.archivo = newfile
                    resolucion.save(request)
                log(f'Adiciono resolución {resolucion}', request, 'add')

                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editresolucion':
            try:
                id = encrypt_id(request.POST['id'])
                resolucion = Resoluciones.objects.get(id=id)
                form = ResolucionSesionForm(request.POST, instancia=resolucion)
                if not form.is_valid():
                    transaction.set_rollback(True)
                    form_error = [{k: v[0]} for k, v in form.errors.items()]
                    return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                resolucion.fecha = form.cleaned_data['fecha']
                resolucion.orden = form.cleaned_data['orden']
                resolucion.resuelve = form.cleaned_data['resuelve']
                resolucion.numeroresolucion = form.cleaned_data['numeroresolucion']
                resolucion.save(request)

                if 'archivo' in request.FILES:
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre('documento_resolucion', newfile._name)
                    resolucion.archivo = newfile
                    resolucion.save(request)
                log(f'Edito Resolución {resolucion}', request, 'edit')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'moverresolucion':
            try:
                id = encrypt_id(request.POST['id'])
                resolucion = Resoluciones.objects.get(id=id)
                tipo =request.POST.get('tipo','')
                idrecibe =request.POST.get('recibe', '')
                if not tipo or not idrecibe:
                    raise NameError('Por favor seleccione una carpeta de destino.')

                if tipo == 'tiporesolucion':
                    resolucion.tipo_id = idrecibe
                    resolucion.sesion = None
                else:
                    sesion = SesionResolucion.objects.get(id=idrecibe)
                    resolucion.tipo = sesion.tipo
                    resolucion.sesion = sesion
                resolucion.save(request)
                log(f'Muevo resolución a otra ubicación {resolucion}', request, 'edit')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delresolucion':
            try:
                resolucion = Resoluciones.objects.get(pk=encrypt_id(request.POST['id']))
                resolucion.status = False
                resolucion.save(request)
                log(u'Elimino resolución: %s' % resolucion, request, "del")
                res_js = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                res_js = {'error': True, 'mensaje': msg_err}
            return JsonResponse(res_js)

        elif action == 'changefilefolder':
            try:
                with transaction.atomic():
                    idfolder_ = encrypt_id(request.POST['idfolder'])
                    idfile = encrypt_id(request.POST['idfile'])
                    sesion = SesionResolucion.objects.get(id=idfolder_)
                    resolucion = Resoluciones.objects.get(id=idfile)
                    resolucion.sesion = sesion
                    resolucion.tipo = sesion.tipo
                    resolucion.save(request, update_fields=['sesion','tipo'])
                    log(u'Cambio Ubicación de resolución: %s' % resolucion, request, "change")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        if action == 'changefolderfolder':
            try:
                with transaction.atomic():
                    idfolderdestino_ = encrypt_id(request.POST['idfolder'])
                    idfolder_ = encrypt_id(request.POST['idfile'])
                    folderdestino = SesionResolucion.objects.get(id=idfolderdestino_)
                    folder = SesionResolucion.objects.get(id=idfolder_)
                    for resolucion in folder.resoluciones():
                        resolucion.sesion = folderdestino
                        resolucion.tipo = folderdestino.tipo
                        resolucion.save(request, update_fields=['sesion', 'tipo'])
                        log(u'Cambio Ubicación de resolución: %s' % resolucion, request, "change")
                    res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            if action == 'addtipo':
                try:
                    data['form'] = TipoResolucionForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'edittipo':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    tipo = TipoResolucion.objects.get(id=id)
                    data['form'] = TipoResolucionForm(initial=model_to_dict(tipo))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'sesiones':
                try:
                    data['idtipo'] = id = request.GET['id']
                    data['filtro'] = tipo = TipoResolucion.objects.get(id=encrypt_id(id))
                    data['title'] = f'{tipo.nombre} | Sesiones '
                    data['subtitle'] = f'{tipo.nombre} > Sesiones'
                    url_vars, filtro, desde, hasta, search = f'&action={action}&id={id}', \
                                                             Q(status=True, tipo=tipo),\
                                                             request.GET.get('desde',''),\
                                                             request.GET.get('hasta',''), request.GET.get('s','')
                    if desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'
                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'
                    if search:
                        data['s'] = s = search.strip()
                        url_vars += f'&s={s}'
                        tipos = SesionResolucion.objects.filter(filtro).filter(nombre__unaccent__icontains=s).order_by('-fecha_creacion')
                    else:
                        tipos = SesionResolucion.objects.filter(filtro).order_by('orden')
                    paging = MiPaginador(tipos, 11)
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
                    data['url_vars'] = url_vars
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['listado'] = page.object_list

                    filtro = filtro & Q(sesion__isnull=True)
                    if search:
                        resoluciones = Resoluciones.objects.filter(filtro).filter(Q(numeroresolucion__unaccent__icontains=s) | Q(resuelve__icontains=s)).order_by('-fecha')
                    else:
                        resoluciones = Resoluciones.objects.filter(filtro).order_by('-fecha')
                    paging = MiPaginador(resoluciones, 11)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador2' in request.session:
                            paginasesion = int(request.session['paginador2'])
                        if 'page2' in request.GET:
                            p = int(request.GET['page2'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador2'] = p
                    data['paging2'] = paging
                    data['page2'] = page
                    data['rangospaging2'] = paging.rangos_paginado(p)
                    data['listado2'] = page.object_list
                    data['url_vars2'] = url_vars
                    return render(request, "ver_resoluciones/sesiones.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addsesion':
                try:
                    data['idp'] =id= encrypt_id(request.GET['id'])
                    tipo=TipoResolucion.objects.get(id=id)
                    form = SesionForm()
                    form.fields['orden'].initial = tipo.orden_sesion_next()
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editsesion':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    sesion = SesionResolucion.objects.get(id=id)
                    data['form'] = SesionForm(initial=model_to_dict(sesion))
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'resoluciones':
                try:
                    data['idsesion'] = id = request.GET['id']
                    sesion = SesionResolucion.objects.get(id=encrypt_id(id))
                    data['idtipo'] = sesion.tipo.id
                    data['title'] = f'{sesion.nombre} | Resoluciones'
                    data['subtitle'] = f'{sesion.tipo} > {sesion.nombre} > Resoluciones'
                    url_vars, filtro, desde, hasta, search = f'&action={action}&id={id}', \
                                                            Q(status=True, sesion=sesion),  \
                                                            request.GET.get('desde',''),\
                                                            request.GET.get('hasta',''), request.GET.get('s','')
                    if desde:
                        data['desde'] = desde
                        filtro = filtro & Q(fecha__gte=desde)
                        url_vars += f'&desde={desde}'
                    if hasta:
                        data['hasta'] = hasta
                        filtro = filtro & Q(fecha__lte=hasta)
                        url_vars += f'&hasta={hasta}'
                    if search:
                        data['s'] = s = search.strip()
                        filtro = filtro & Q(numeroresolucion__unaccent__icontains=s) | Q(resuelve__icontains=s)
                        url_vars += f'&s={s}'
                    tipos = Resoluciones.objects.filter(filtro).order_by('orden')
                    paging = MiPaginador(tipos, 20)
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
                    data['listado'] = page.object_list
                    data['url_vars'] = url_vars
                    return render(request, "ver_resoluciones/resoluciones.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addresolucion':
                try:
                    id=request.GET['id']
                    idex=request.GET['idex']
                    data['idp'] = idp = encrypt_id(request.GET['id']) if id else 0
                    data['id'] = id = encrypt_id(request.GET['idex']) if idex else 0
                    if idp > 0:
                        sesion = SesionResolucion.objects.get(id=idp)
                        orden = sesion.orden_resolucion_next()
                    elif id > 0:
                        tipo = TipoResolucion.objects.get(id=id)
                        orden = tipo.orden_resolucion_next()
                    form = ResolucionSesionForm()
                    form.fields['orden'].initial = orden
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'editresolucion':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    resolucion = Resoluciones.objects.get(id=id)
                    data['form'] = ResolucionSesionForm(initial=model_to_dict(resolucion), instancia=resolucion)
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            elif action == 'resolucionesall':
                data['title'] = u'Gestión de Resoluciones'
                coordinacion = perfilprincipal.inscripcion.carrera.coordinacion_carrera().id if perfilprincipal.inscripcion else None

                search = None
                tipo = 0
                desde = hasta = ''

                filtro = Q(status=True)

                if 's' in request.GET:
                    search = request.GET['s']

                if 'tipore' in request.GET:
                    tipo = int(request.GET['tipore'])

                if 'desde' in request.GET:
                    desde = request.GET['desde']
                if 'hasta' in request.GET:
                    hasta = request.GET['hasta']

                url_vars = ' '

                if search:
                    data['search'] = search
                    # ss = search.split(' ')
                    # if len(ss) == 1:
                    filtro = filtro & (Q(numeroresolucion__icontains=search) | Q(resuelve__icontains=search))
                    url_vars += "&s={}".format(search)

                if tipo > 0:
                    data['tipo'] = tipo
                    filtro = filtro & Q(tipo__id=tipo)
                    url_vars += "&tipo={}".format(tipo)

                if desde:
                    data['desde'] = desde
                    filtro = filtro & Q(fecha__gte=desde)
                    url_vars += "&desde={}".format(desde)

                if hasta:
                    data['hasta'] = hasta
                    filtro = filtro & Q(fecha__lte=hasta)
                    url_vars += "&hasta={}".format(hasta)

                if coordinacion == 7:
                    resoluciones = Resoluciones.objects.filter(filtro).annotate(tipo_ordenado=Case(When(tipo=4, then=Value(0)), default=Value(1))).order_by('tipo_ordenado', '-fecha_creacion')
                else:
                    resoluciones = Resoluciones.objects.filter(filtro).annotate(tipo_ordenado=Case(When(tipo=4, then=Value(1)), default=Value(0))).order_by('tipo_ordenado', '-fecha_creacion')

                paging = MiPaginador(resoluciones, 20)
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
                data['resoluciones'] = page.object_list
                data['search'] = search if search else ""
                data['tiposlist'] = TipoResolucion.objects.filter(status=True)
                data['url_vars'] = url_vars
                return render(request, "ver_resoluciones/view.html", data)

            elif action == 'moverresolucion':
                try:
                    data['id'] = id = encrypt_id(request.GET['id'])
                    data['resolucion'] = Resoluciones.objects.get(id=id)
                    data['tipos'] = TipoResolucion.objects.select_related().filter(status=True)
                    template = get_template('ver_resoluciones/modal/formmoverresolucion.html')
                    return JsonResponse({'result': True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje': f'Error: {ex}'})

            return HttpResponseRedirect(request.path)

        else:
            try:
                data['title'] = u'Categorías resolución'
                data['subtitle'] = u'Tipos de categorías'
                url_var, filtro = '', Q(status=True)
                tipos = TipoResolucion.objects.filter(filtro).order_by('-fecha_creacion')
                paging = MiPaginador(tipos, 10)
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
                data['listado'] = page.object_list
                return render(request, "ver_resoluciones/categoriaresoluciones.html", data)
            except Exception as ex:
                pass
