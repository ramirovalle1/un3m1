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
from django.db.models import Q, Max, F, Sum
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, get_object_or_404
from sagest.forms import ComponenteActivoForm, GrupoBienForm, \
    ComponenteCatalogoActivoForm, TipoNotificacionForm, ComprobanteATForm, ActividadInformeGCForm
from sagest.models import ActivoTecnologico, ActivoFijo, \
    CatalogoBien, Marca, GruposCategoria, RangoVidaUtil, ComponenteActivo, ComponenteCatalogoActivo, HdDetalle_Incidente, \
    TipoNotificacion, Notificacionactivoresponsable, ComprobanteAT, ActividadInformeGC
from decorators import secure_module
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log
from django.template.loader import get_template
from django.forms import model_to_dict
from sga.models import Notificacion
from sagest.funciones import dominio_sistema_base
from sga.templatetags.sga_extras import encrypt

unicode = str


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    dominio_sistema = dominio_sistema_base(request)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            #VIEWACTIO 1 MARCAS
            if action == 'addmarca':
                try:
                    descripcion = request.POST['descripcion']
                    marca_esta_repetida = Marca.objects.filter(status=True, descripcion=descripcion)
                    if not marca_esta_repetida:
                        marca = Marca(descripcion=descripcion)
                        marca.save(request)
                        log(u'Adiciona marca: %s' % marca, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u'La marca ' + str(
                            descripcion) + ' ya se encuentra registrada'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al guardar la marca'})

            elif action == 'editmarca':
                try:
                    descripcion = request.POST['descripcion']
                    id = request.POST['id']
                    marca = Marca.objects.get(id=id)
                    if marca.descripcion != descripcion:
                        marca_esta_repetida = Marca.objects.filter(status=True, descripcion=descripcion)
                        if not marca_esta_repetida:
                            marca.descripcion = descripcion
                            marca.save(request)
                            log(u'Edita marca: %s' % marca, request, "act")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'La marca ' + str(
                                descripcion) + ' ya se encuentra registrada'})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al guardar la marca'})

            elif action == 'deletemarca':
                try:
                    idmarca = int(request.POST['id'])
                    marca = Marca.objects.get(id=idmarca)
                    marca.status = False
                    marca.save(request)
                    log(u'Elimina marca: %s' % marca, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al eliminar la marca'})

            #VIEWACTIO 2 GRUPO CATEGORIAS
            elif action == 'addgrupo':
                try:
                    descripcion = request.POST['descripcion']
                    identificador = request.POST['identificador']
                    existe_grupo = GruposCategoria.objects.filter(status=True, descripcion=descripcion.upper())
                    if not existe_grupo:
                        nuevogrupo = GruposCategoria(descripcion=descripcion,
                                                     identificador=identificador)
                        nuevogrupo.save(request)
                        log(u'Adicionar grupo: %s' % nuevogrupo, request, "add")
                        return JsonResponse({"result": "ok"})
                    return JsonResponse({"result": "bad", "mensaje": u'El nombre ingresado ya se encuentra registrado'})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al adicionar el grupo'})

            elif action == 'editgrupo':
                try:
                    id = int(request.POST['id'])
                    descripcion = request.POST['descripcion'].strip()
                    identificador = request.POST['identificador']
                    editgrupo = GruposCategoria.objects.get(id=id)
                    consultar = GruposCategoria.objects.filter(status=True, id=id)
                    if consultar:
                        if consultar[0].descripcion != descripcion.upper():
                            existe_grupo = GruposCategoria.objects.filter(status=True, descripcion=descripcion.upper())
                            if not existe_grupo:
                                editgrupo.descripcion = descripcion
                                editgrupo.identificador = identificador
                                editgrupo.save(request)
                                log(u'Edita grupo: %s' % editgrupo, request, "edit")
                                return JsonResponse({"result": "ok"})
                            else:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u'Ya existe un grupo con el mismo nombre: ' + str(
                                                         descripcion)})
                        else:
                            editgrupo.identificador = identificador
                            editgrupo.save(request)
                            log(u'Edita grupo: %s' % editgrupo, request, "edit")
                            return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al editar el grupo'})

            elif action == 'deletegruposcategoria':
                try:
                    idgrupo = int(request.POST['id'])
                    grupocat = GruposCategoria.objects.get(id=idgrupo)
                    grupocat.status = False
                    grupocat.save(request)
                    log(u'Elimina grupo: %s' % grupocat, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "ok", "mensaje": u'Error al eliminar el grupo'})

            if action == 'addactividadinforme':
                with transaction.atomic():
                    try:
                        idgrupo = int(encrypt(request.POST['id']))
                        form = ActividadInformeGCForm(request.POST)
                        if form.is_valid() and form.validador(idgrupo):
                            instancia = ActividadInformeGC(grupocategoria_id=idgrupo, descripcion=form.cleaned_data['descripcion'])
                            instancia.save(request)
                            diccionario = {'id': instancia.id,
                                           'descripcion':instancia.descripcion,
                                           'mostrar': instancia.activo,
                                           }
                            log(u'Agrego actividad de informe: %s' % instancia, request, "add")
                            return JsonResponse({'result': True, 'data_return': True, 'mensaje': u'Guardado con éxito', 'data': diccionario})
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            if action == 'editactividadinforme':
                with transaction.atomic():
                    try:
                        actividad = ActividadInformeGC.objects.get(pk=int(request.POST['id']))
                        if request.POST['name'] == 'mostrar':
                            actividad.activo = eval(request.POST['val'].capitalize())
                            actividad.save(request)
                            log(u'Edito estado mostrar de actividad : %s (%s)' % (actividad, actividad.activo), request,"edit")
                        if request.POST['name'] == 'descripcion_':
                            idgrupo=int(encrypt(request.POST['idgrupo']))
                            descripcion = request.POST['val'].strip()
                            if ActividadInformeGC.objects.filter(status=True, descripcion__unaccent=descripcion,grupocategoria_id=idgrupo).exclude(id=actividad.id).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'result': False, "mensaje": 'La actividad que desea guardar ya existe.'}, safe=False)
                            actividad.descripcion = request.POST['val']
                            actividad.save(request)
                            log(u'Edito descripcion: %s (%s)' % (actividad, actividad.descripcion), request, "edit")
                        return JsonResponse({"result": True, 'mensaje': 'Cambios guardados'})
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return JsonResponse({'result': False, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            if action == 'delactividadinforme':
                with transaction.atomic():
                    try:
                        instancia = ActividadInformeGC.objects.get(pk=int(request.POST['id']))
                        instancia.status = False
                        instancia.save(request)
                        log(u'Elimino requisito de servicio: %s' % instancia, request, "del")
                        res_json = {"error": False, "mensaje": 'Actividad eliminado'}
                    except Exception as ex:
                        res_json = {'error': True, "message": "Error: {}".format(ex)}
                    return JsonResponse(res_json, safe=False)

            # VIEWACTIVO 3 CLASIFICAR CATEGORIAS
            elif action == 'clasificar':
                try:
                    accion = request.POST['accion']
                    catalogo = CatalogoBien.objects.get(pk=int(request.POST['id']))
                    if accion == 'add':
                        catalogo.equipoelectronico = True
                        ids = ActivoTecnologico.objects.values_list("activotecnologico_id", flat=True).filter(activotecnologico__catalogo=catalogo, status=True)
                        activos = ActivoFijo.objects.filter(status=True, catalogo=catalogo).exclude(id__in=ids)
                        for activo in activos:
                            comprobante=ComprobanteAT.objects.filter(status=True,
                                                                     numerocomprobante=activo.numerocomprobante,
                                                                     tipocomprobante=activo.tipocomprobante).first()
                            if not comprobante:
                                comprobante=ComprobanteAT(numerocomprobante=activo.numerocomprobante,
                                                          tipocomprobante=activo.tipocomprobante,
                                                          origeningreso=activo.origeningreso,
                                                          descripcion=activo.observacion,
                                                          fechacompra=activo.fechacomprobante)
                                comprobante.save(request)
                                log(u'Agrego comprobante de activo tecnológico: %s' % comprobante, request, "add")


                            ultimocodigotics = ActivoTecnologico.objects.filter(codigotic__isnull=False).last()
                            codigotics_generado = int(ultimocodigotics.codigotic) + 1
                            activonew = ActivoTecnologico(activotecnologico=activo,
                                                          codigotic=codigotics_generado,
                                                          comprobanteat=comprobante)
                            activonew.save(request)
                            cantidad = activo.total_numerocomprobante_catalogo(catalogo)
                            comprobante.descripcion = comprobante.descripcion if comprobante.descripcion else activo.observacion
                            comprobante.cantidad=cantidad
                            comprobante.save(request)
                            log(u'Agrego activo tecnológico: %s' % activonew, request, "add")

                    else:
                        catalogo.equipoelectronico = False
                        ActivoTecnologico.objects.filter(activotecnologico__catalogo=catalogo, status=True).update(status=False)
                    catalogo.clasificado = True
                    catalogo.save(request)

                    log(u'Clasificó catálogo: %s' % catalogo, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'restaurarcatalogo':
                try:
                    with transaction.atomic():
                        instancia = CatalogoBien.objects.get(pk=int(request.POST['id']))
                        instancia.clasificado = False
                        instancia.equipoelectronico = False
                        instancia.save(request)
                        log(u'Restauro catalogo para reclasificar: %s' % instancia, request, "edit")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            # VIEWACTIVO 4 AGRUPAR CATEGORIAS
            elif action == 'agregaragrupo':
                try:
                    catalogo = CatalogoBien.objects.get(pk=int(request.POST['id']))
                    f = GrupoBienForm(request.POST)
                    if f.is_valid():
                        catalogo.grupo = f.cleaned_data['grupo']
                        catalogo.save(request)
                        log(u'Adicionó un grupo a catálogo: %s' % catalogo, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": True, "form": [{k: v[0]} for k, v in f.errors.items()], "mensaje": "Complete los datos requeridos."}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" %ex.__str__()})

            if action == 'agregarcomponente':
                try:
                    detcomponente = None
                    f = ComponenteCatalogoActivoForm(request.POST)
                    if f.is_valid():
                        idcatalogo = CatalogoBien.objects.get(pk=int(request.POST['id']))
                        idcomponente = int(request.POST['componente'])
                        componente_existe = ComponenteCatalogoActivo.objects.filter(status=True,componente_id=idcomponente, catalogo=idcatalogo)
                        if not componente_existe:
                            detcomponente = ComponenteCatalogoActivo(componente_id=idcomponente, catalogo=idcatalogo)
                            detcomponente.save(request)
                            log(u'Adicionar componente: %s' % detcomponente, request, "add")
                            return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'El componente ' + componente_existe.first().componente.__str__() + ' ya se encuentra registrado'})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u'Error al adicionar el componente'})

            elif action == 'deletecategoria':
                try:
                    with transaction.atomic():
                        instancia = CatalogoBien.objects.get(pk=int(request.POST['id']))
                        activos_t=ActivoTecnologico.objects.filter(activotecnologico__catalogo=instancia, status=True)
                        instancia.clasificado = False
                        instancia.equipoelectronico = False
                        instancia.save(request)
                        for activo_t in activos_t:
                            comprobante = ComprobanteAT.objects.filter(status=True,
                                                                       numerocomprobante=activo_t.activotecnologico.numerocomprobante,
                                                                       tipocomprobante=activo_t.activotecnologico.tipocomprobante).first()
                            activo_t.status=False
                            activo_t.save(request)
                            if comprobante:
                                comprobante.cantidad=comprobante.cantidad-1
                                comprobante.save(request)
                        log(u'Elimino activos de catalogo: %s' % instancia, request, "del")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'delcomponentegrupo':
                try:
                    idcomponente = int(request.POST['id'])
                    componente = ComponenteCatalogoActivo.objects.get(id=idcomponente)
                    componente.status = False
                    componente.save(request)
                    log(u'Elimina componente: %s' % componente, request, "del")
                    return JsonResponse({"error": False})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al eliminar la marca'})

            # VIEWACTIVO 5 COMPONENTES
            elif action == 'addcomponente':
                try:
                    f = ComponenteActivoForm(request.POST)
                    if f.is_valid():
                        componente = request.POST['descripcion']
                        componente_existe = ComponenteActivo.objects.filter(descripcion=componente, status=True)
                        if not componente_existe:
                            nuevocomponente = ComponenteActivo(descripcion=componente)
                            nuevocomponente.save(request)
                            log(u'Adicionar Componente: %s' % nuevocomponente, request, "add")
                            return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'El componente ' + str(
                                componente) + ' ya se encuentra registrado'})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u'Error al adicionar el componente'})

            elif action == 'editcomponente':
                try:
                    id = int(request.POST['id'])
                    f = ComponenteActivoForm(request.POST)
                    if f.is_valid():
                        componente = ComponenteActivo.objects.get(id=id)
                        componente.descripcion = f.cleaned_data['descripcion']
                        componente.save(request)
                        log(u'Editar componente: %s' % componente, request, "edit")
                        return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al editar el componente'})

            elif action == 'deletecomponente':
                try:
                    idcomponente = int(request.POST['id'])
                    componente = ComponenteActivo.objects.get(id=idcomponente)
                    componente.status = False
                    componente.save(request)
                    log(u'Se eliminó componente: %s' % componente, request, "del")
                    return HttpResponse(json.dumps({"result": "ok"}), content_type="application/json")
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u'Error al eliminar el componente'})

            # VIEWACTIVO 6 INVENTARIO TECNOLÓGICO
            elif action == 'detalle_mantenimiento':
                try:
                    data['activofijo'] = activofijo = ActivoFijo.objects.get(pk=int(request.POST['id']))
                    data['detallemantenimiento'] = HdDetalle_Incidente.objects.filter(incidente__activo=activofijo,
                                                                                      status=True,
                                                                                      incidente__status=True,
                                                                                      estado__id=3).order_by(
                        'incidente__fechareporte')
                    sgarantia = activofijo.mantenimientosactivospreventivos_set.filter(status=True).order_by()
                    data['mantenimientopreventivo'] = sgarantia.order_by('fecha')
                    mantenimientogarantia = activofijo.mantenimientosactivosgarantia_set.filter(status=True)
                    data['mantenimientogarantia'] = mantenimientogarantia.order_by('fechainicio')
                    data['costomantenimientogarantia'] = \
                        mantenimientogarantia.filter(status=True).aggregate(cantidad=Sum('valor'))['cantidad']
                    template = get_template("at_activostecnologicos/detallehelpdesk.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            # VIEWACTIVO 7 NOTIFICAR ACTIVOS
            elif action == 'deletenotificacion':
                try:
                    id = request.POST['id']
                    notiresponsable = Notificacionactivoresponsable.objects.get(pk=id)
                    noti = Notificacion.objects.get(status=True, object_id=notiresponsable.id, titulo=notiresponsable.asunto)
                    noti.status = False
                    noti.save(request)
                    log(u'Elimina Notificacion: %s' % (noti), request, "del")
                    notiresponsable.status = False
                    notiresponsable.save(request)
                    log(u'Elimina Notificacion responsable : %s' % (notiresponsable), request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            # VIEWACTIVO 8 TIPOS DE NOTIFICACIÓN
            elif action == 'addtiponotificacion':
                try:
                    f = TipoNotificacionForm(request.POST)
                    if f.is_valid():
                        tiponoti = request.POST['descripcion']
                        tiponoti_existe = TipoNotificacion.objects.filter(descripcion=tiponoti.upper(), status=True)
                        if not tiponoti_existe:
                            nuevotipo = TipoNotificacion(descripcion=tiponoti)
                            nuevotipo.save(request)
                            log(u'Adicionar Tipo Notificacion: %s' % nuevotipo, request, "add")
                            return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'El tipo de notificación ' + str(
                                tiponoti) + ' ya se encuentra registrado'})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u'Error al adicionar el componente'})

            elif action == 'edittiponotificacion':
                try:
                    id = int(request.POST['id'])
                    f = TipoNotificacionForm(request.POST)
                    if f.is_valid():
                        descripciontipo = f.cleaned_data['descripcion']
                        existetiponoti = TipoNotificacion.objects.filter(descripcion=descripciontipo.upper()).exists()
                        if not existetiponoti:
                            tiponoti = TipoNotificacion.objects.get(id=id)
                            tiponoti.descripcion = f.cleaned_data['descripcion']
                            tiponoti.save(request)
                            log(u'Editar Tipo Notificacion: %s' % tiponoti, request, "edit")
                            return HttpResponse(json.dumps({"result": False}), content_type="application/json")
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u'El tipo de notificación ' + str(
                                descripciontipo) + ' ya se encuentra registrado'})
                    else:
                        raise NameError('Error')

                except Exception as ex:
                    transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u'Error al editar el tipo de notificación'})

            elif action == 'deletiponotificacion':
                try:
                    id = request.POST['id']
                    tipo = TipoNotificacion.objects.get(status=True, pk=id)
                    tipo.status=False
                    tipo.save(request)
                    log(u'Elimina Tipo Notificacion: %s' % (tipo), request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            # VIEWACTIVO 9 COMPROBANTES
            elif action =='editcomprobante':
                try:
                    id = int(encrypt(request.POST['id']))
                    form=ComprobanteATForm(request.POST)
                    if not form.is_valid():
                        transaction.set_rollback(True)
                        form_error = [{k: v[0]} for k, v in form.errors.items()]
                        return JsonResponse({'result': True, "form": form_error, "mensaje": "Error en el formulario"})
                    comprobante=ComprobanteAT.objects.get(id=id)
                    comprobante.proveedor=form.cleaned_data['proveedor']
                    comprobante.contrato=form.cleaned_data['contrato']
                    # comprobante.origeningreso=form.cleaned_data['origeningreso']
                    # comprobante.tipocomprobante=form.cleaned_data['tipocomprobante']
                    # comprobante.numerocomprobante=form.cleaned_data['numerocomprobante']
                    # comprobante.fechacomprobante=form.cleaned_data['fechacomprobante']
                    # comprobante.cantidad=form.cleaned_data['cantidad']
                    comprobante.descripcion=form.cleaned_data['descripcion']
                    comprobante.save(request)
                    log(f'Edito comprobante proveedor: {comprobante}', request, 'edit')
                    return JsonResponse({'result': False,'mensaje':'Guardado con exito'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, 'mensaje': str(ex)})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action']= action = request.GET['action']

            #VIEWACTIO 2 GRUPO CATEGORIAS
            if action == 'grupocategorias':
                try:
                    data['title'] = u'Grupos categoría'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action={action}"
                    filtro = Q(status=True)
                    if search:
                        search = request.GET['s']
                        filtro = filtro & (Q(descripcion__icontains=search) | Q(identificador__icontains=search))
                        url_vars += f"&s={search}"
                    gruposcategoria = GruposCategoria.objects.filter(filtro).order_by('-id')
                    paging = MiPaginador(gruposcategoria, 25)
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
                    data['gruposcategoria'] = page.object_list
                    data['url_vars'] = url_vars
                    data['usuario'] = request.user
                    request.session['viewactivo']=2
                    return render(request, "at_activostecnologicos/gruposcategoria.html", data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            if action == 'actividadesinforme':
                try:
                    form = ActividadInformeGCForm()
                    data['idgrupo']=id=int(encrypt(request.GET['id']))
                    data['filtro'] = ActividadInformeGC.objects.filter(grupocategoria_id=id, status=True)
                    data['form'] = form
                    template = get_template("at_activostecnologicos/modal/formactividadesinforme.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # VIEWACTIVO 3 CLASIFICAR CATEGORIAS
            elif action == 'clasificarcategorias':
                try:
                    url_vars = f"&action={action}"
                    data['title'] = u'Listado de categorías por clasificar'
                    catalogo = CatalogoBien.objects.filter(status=True, clasificado=False)
                    paging = MiPaginador(catalogo, 25)
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
                    data['catalogos'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo']=3
                    return render(request, 'at_activostecnologicos/clasificar.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'desclasificados':
                try:
                    url_vars = f"&action={action}"
                    data['title'] = u'Listado de categorías desclasificadas'
                    catalogo = CatalogoBien.objects.filter(status=True, clasificado=True,equipoelectronico=False).order_by('-fecha_modificacion')
                    paging = MiPaginador(catalogo, 25)
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
                    data['catalogos'] = page.object_list
                    data['url_vars'] = url_vars
                    template=get_template('at_activostecnologicos/modal/listadonopertenecientes.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar la ventana. %s" % ex})

            # VIEWACTIVO 4 AGRUPAR CATEGORIAS
            elif action == 'agruparcategorias':
                try:
                    data['title'] = u'Listado para agrupar por categorías'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action={action}"
                    search = None
                    ids = None
                    s = None
                    perfil = None
                    filtro = (Q(status=True) & Q(clasificado=True) & Q(equipoelectronico=True))
                    if 's' in request.GET:
                        s = request.GET['s']
                        data['s'] = s
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            filtro = filtro & (Q(descripcion__icontains=search) |
                                               Q(identificador__icontains=search))
                            url_vars += f"&s={search}"

                        else:
                            filtro = filtro & ((Q(descripcion__icontains=ss[0]) &
                                                Q(descripcion__icontains=ss[1])))
                            url_vars += f"&s={search}"

                    catalogobien = CatalogoBien.objects.filter(filtro)
                    paging = MiPaginador(catalogobien, 25)
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
                    data['perfil'] = perfil if perfil else ""
                    data['catalogos'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo'] = 4
                    return render(request, 'at_activostecnologicos/categorizar.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'agregaragrupo':
                try:
                    data['form2'] = GrupoBienForm()
                    data['id'] = request.GET['id']
                    data['action'] = request.GET['action']
                    template = get_template("at_activostecnologicos/formaddgrupo.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            elif action == 'agregarcomponente':
                try:
                    data['action'] = action
                    data['id'] = int(request.GET['id'])
                    form = ComponenteCatalogoActivoForm()
                    data['form'] = form
                    template = get_template('at_activostecnologicos/agregarcomponentes.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            if action == 'detallecomponente':
                try:
                    data['catalogo'] = catalogo = CatalogoBien.objects.get(pk=int(request.GET['id']))
                    data['title'] = catalogo._meta.verbose_name
                    template = get_template('at_activostecnologicos/detallecomponente.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            # VIEWACTIVO 5 COMPONENTES
            elif action =='componentes':
                try:
                    data['title'] = u'Listado de componentes'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action={action}"
                    filtro = Q(status=True)
                    if search:
                        filtro &= Q(descripcion__icontains=search)
                        url_vars += f"&s={search}"
                    componente = ComponenteActivo.objects.filter(filtro)
                    paging = MiPaginador(componente, 25)
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
                    data['componente'] = page.object_list
                    data['url_vars'] = url_vars
                    data['usuario'] = request.user
                    request.session['viewactivo'] = 5
                    return render(request, 'at_activostecnologicos/componentes.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action == 'addcomponente':
                try:
                    data['action'] = 'addcomponente'
                    form = ComponenteActivoForm()
                    data['form'] = form
                    template = get_template('at_activostecnologicos/addcomponente.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editcomponente':
                try:
                    data['title'] = u'Editar Componente'
                    data['action'] = 'editcomponente'
                    data['id'] = id = int(request.GET['id'])
                    componente = ComponenteActivo.objects.get(id=id)
                    data['form'] = ComponenteActivoForm(initial=model_to_dict(componente))
                    template = get_template('at_activostecnologicos/editcomponente.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            # VIEWACTIVO 6 INVENTARIO TECNOLÓGICO
            elif action =='inventariotecnologico':
                try:
                    url_vars = f"&action={action}"
                    data['title'] = u'Equipo Tecnológico'
                    search = request.GET.get('s', '').strip()
                    ids = None
                    data['codigo'] = codigo = int(request.GET.get('codigo')) if request.GET.get('codigo') else 0
                    data['baja'] = baja = int(request.GET.get('baja')) if request.GET.get('baja') else 0
                    data['rangosemaforo'] = RangoVidaUtil.objects.filter(status=True).order_by('anio', 'descripcion')
                    data['grupocatalogo'] = GruposCategoria.objects.filter(status=True)

                    if codigo == 0:
                        activos = ActivoFijo.objects.filter(Q(archivobaja__isnull=True) | Q(archivobaja=''),
                                                            catalogo__equipoelectronico=True, catalogo__status=True,
                                                            status=True).order_by('descripcion')
                        url_vars += f"&codigo={codigo}"

                    else:
                        activos = ActivoFijo.objects.filter(
                            Q(archivobaja__isnull=True) | Q(archivobaja=''), catalogo__equipoelectronico=True,
                            catalogo__status=True, catalogo__grupo__id=codigo, status=True).order_by(
                            'descripcion')
                        url_vars += f"&codigo={codigo}"

                    if search:
                        activos = activos.filter(
                            Q(codigogobierno__icontains=search) | Q(descripcion__icontains=search) | Q(codigointerno__icontains=search),
                            status=True)
                    url_vars += f"&s={search}"

                    if baja == 1 or baja == 0:
                        activos = activos.filter(statusactivo=1)
                        url_vars += f"&baja={baja}"

                    else:
                        if baja == 2:
                            activos = activos.filter(statusactivo=2)
                            url_vars += f"&baja={baja}"

                    data['totales'] = activos.values('id').count()

                    paging = MiPaginador(activos, 15)
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
                    data['listadocatalogo'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo']=6
                    return render(request, "at_activostecnologicos/historia_act_tecnologico.html", data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            # VIEWACTIVO 7 NOTIFICAR ACTIVOS
            elif action =='notificaractivos':
                try:
                    data['title'] = u'Listado de Notificaciones'
                    search, url_vars, codigo = request.GET.get('s', ''), '', request.GET.get('codigo', '')
                    url_vars = f"&action={action}"
                    filtro = Q(status=True)

                    if codigo:
                        codigo = int(codigo)
                        if codigo != 0:
                            filtro = filtro & (Q(tipo_id=int(codigo)))
                            url_vars += f"&codigo={codigo}"

                    if search:
                        data['s'] = search = request.GET['s'].strip()
                        ss = search.split(' ')

                        if len(ss) == 1:
                            filtro = filtro & (Q(activo__descripcion__icontains=search) |
                                               Q(activo__codigogobierno__icontains=search) |
                                               Q(asunto__icontains=search) |
                                               Q(detalle__icontains=search) |
                                               Q(tipo__descripcion__icontains=search) |
                                               Q(activo__codigointerno__icontains=search) |
                                               Q(activo__modelo__icontains=search) |
                                               Q(responsable__nombres__icontains=search) |
                                               Q(responsable__apellido1__icontains=search) |
                                               Q(responsable__apellido2__icontains=search))
                        else:
                            filtro = filtro & (Q(responsable__apellido1__unaccent__icontains=ss[0]) &
                                               Q(responsable__apellido2__unaccent__icontains=ss[1]))
                        url_vars += f"&s={search}"
                    componente = Notificacionactivoresponsable.objects.filter(filtro).order_by('estado')
                    paging = MiPaginador(componente, 25)
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
                    data['notificaciones'] = page.object_list
                    data['codigo'] = codigo
                    data['tipos'] = TipoNotificacion.objects.filter(status=True)
                    data['url_vars'] = url_vars
                    request.session['viewactivo']=7
                    return render(request, 'at_activostecnologicos/notificaciondeactivos.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            # VIEWACTIVO 8 TIPOS DE NOTIFICACIÓN
            elif action =='tiposnotificaciones':
                try:
                    data['title'] = u'Listado de Tipos de Notificación'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action={action}"
                    filtro = Q(status=True)
                    if search:
                        filtro &= Q(asunto__icontains=search) | Q(detalle__icontains=search)
                        url_vars += f"&s={search}"
                    tiponoti = TipoNotificacion.objects.filter(filtro)
                    paging = MiPaginador(tiponoti, 25)
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
                    data['componente'] = page.object_list
                    data['url_vars'] = url_vars
                    request.session['viewactivo']=8
                    return render(request, 'at_activostecnologicos/listadotiponotificacion.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            if action == 'addtiponotificacion':
                try:
                    data['action'] = 'addtiponotificacion'
                    form = TipoNotificacionForm()
                    data['form'] = form
                    template = get_template('at_activostecnologicos/addtiponotificacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'edittiponotificacion':
                try:
                    data['action'] = 'edittiponotificacion'
                    data['id'] = id = int(request.GET['id'])
                    tiponoti = TipoNotificacion.objects.get(id=id)
                    data['form'] = TipoNotificacionForm(initial=model_to_dict(tiponoti))
                    template = get_template('at_activostecnologicos/edittiponotificacion.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error mostrar el formulario. %s" % ex})

            # VIEWACTIVO 9 COMPROBANTES
            elif action =='comprobantes':
                try:
                    data['title'] = u'Listado comprobantes'
                    search, url_vars = request.GET.get('s', ''), ''
                    url_vars = f"&action={action}"
                    filtro = Q(status=True)
                    if search:
                        filtro &= Q(numerocomprobante__icontains=search)
                        url_vars += f"&s={search}"
                    comprobantes = ComprobanteAT.objects.filter(filtro).order_by('numerocomprobante')
                    paging = MiPaginador(comprobantes, 20)
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
                    request.session['viewactivo'] = 9
                    return render(request, 'at_activostecnologicos/proveedorestecnologicos.html', data)
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            elif action =='editcomprobante':
                try:
                    data['id']=id=int(encrypt(request.GET['id']))
                    data['comprobante']=comprobante=ComprobanteAT.objects.get(id=id)
                    form=ComprobanteATForm(initial=model_to_dict(comprobante))
                    data['form']=form
                    template=get_template('at_activostecnologicos/modal/formcomprobante.html')
                    return JsonResponse({'result':True,'data':template.render(data)})
                except Exception as ex:
                    messages.error(f'{ex}')
                    return HttpResponseRedirect(request.path)

            return HttpResponseRedirect(request.path)

        else:
            try:
                search, url_vars = request.GET.get('s', ''), ''
                data['title'] = u'Marcas'
                url_vars = f""
                filtro = Q(status=True)
                if search:
                    filtro = filtro & Q(descripcion__icontains=search)
                    url_vars += f"&s={search}"
                marcas = Marca.objects.filter(filtro).order_by('-id')
                paging = MiPaginador(marcas, 25)
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
                data['marcas'] = page.object_list
                data['url_vars'] = url_vars
                data['usuario'] = request.user
                request.session['viewactivo']=1
                return render(request, "at_activostecnologicos/marcas.html", data)
            except Exception as ex:
                pass






