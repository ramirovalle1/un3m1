# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log, puede_realizar_accion, MiPaginador
from django.db.models import Q
from sga.templatetags.sga_extras import encrypt
from django.template.loader import get_template
from oma.models import ModeloEvaluativo, DetalleModeloEvaluativo, null_to_numeric
from oma.forms import ModeloEvaluativoForm, DetalleModeloEvaluativoForm, LogicaModeloEvaluativoForm



@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                f = ModeloEvaluativoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativo(nombre=f.cleaned_data['nombre'],
                                              fecha=datetime.now().date(),
                                              principal=f.cleaned_data['principal'],
                                              activo=f.cleaned_data['activo'],
                                              notamaxima=f.cleaned_data['notamaxima'],
                                              notaaprobar=f.cleaned_data['notaaprobar'],
                                              notarecuperacion=f.cleaned_data['notarecuperacion'],
                                              asistenciaaprobar=f.cleaned_data['asistenciaaprobar'],
                                              asistenciarecuperacion=f.cleaned_data['asistenciarecuperacion'],
                                              notafinaldecimales=f.cleaned_data['notafinaldecimales'],
                                              observaciones=f.cleaned_data['observaciones'])
                    modelo.save(request)
                    if not ModeloEvaluativo.objects.filter(principal=True).exists():
                        modelo.principal = True
                        modelo.save(request)
                    if modelo.principal:
                        for m in ModeloEvaluativo.objects.exclude(id=modelo.id):
                            m.principal = False
                            m.save(request)
                    log(u'Adicionado modelo evaluativo - oma: %s' % modelo, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                f = ModeloEvaluativoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    modelo.nombre = f.cleaned_data['nombre']
                    modelo.fecha = datetime.now().date()
                    modelo.activo = f.cleaned_data['activo']
                    modelo.principal = f.cleaned_data['principal']
                    modelo.notamaxima = f.cleaned_data['notamaxima']
                    modelo.notaaprobar = f.cleaned_data['notaaprobar']
                    modelo.notarecuperacion = f.cleaned_data['notarecuperacion']
                    modelo.asistenciaaprobar = f.cleaned_data['asistenciaaprobar']
                    modelo.asistenciarecuperacion = f.cleaned_data['asistenciarecuperacion']
                    modelo.notafinaldecimales = f.cleaned_data['notafinaldecimales']
                    modelo.observaciones = f.cleaned_data['observaciones']
                    modelo.save(request)
                    if modelo.principal:
                        for m in ModeloEvaluativo.objects.exclude(id=modelo.id):
                            m.principal = False
                            m.save(request)
                    if not ModeloEvaluativo.objects.filter(principal=True).exists():
                        modelo = ModeloEvaluativo.objects.order_by('-fecha')[0]
                        modelo.principal = True
                        modelo.save(request)
                    log(u'Modifico modelo evaluativo: %s' % modelo, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adddetalle':
            try:
                f = DetalleModeloEvaluativoForm(request.POST)
                if f.is_valid():
                    modelo = ModeloEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    if modelo.detallemodeloevaluativo_set.filter(nombre=f.cleaned_data['nombre']).exists():
                        return JsonResponse({"result": True, "mensaje": u"Ya existe un campo con este nombre."})
                    if modelo.detallemodeloevaluativo_set.filter(orden=f.cleaned_data['orden']).exists():
                        return JsonResponse({"result": True, "mensaje": u"Ya existe un campo con ese numero de orden."})
                    detalle = DetalleModeloEvaluativo(modelo=modelo,
                                                      nombre=f.cleaned_data['nombre'],
                                                      notaminima=f.cleaned_data['notaminima'],
                                                      notamaxima=f.cleaned_data['notamaxima'],
                                                      decimales=f.cleaned_data['decimales'],
                                                      migrarmoodle=f.cleaned_data['migrarmoodle'],
                                                      dependiente=f.cleaned_data['dependiente'],
                                                      dependeasistencia=f.cleaned_data['dependeasistencia'],
                                                      orden=f.cleaned_data['orden'],
                                                      determinaestadofinal=f.cleaned_data['determinaestadofinal'])
                    detalle.save(request)
                    log(u'Adiciono detalle de modelo evaluativo - oma: %s' % detalle, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Registro Exitoso'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        if action == 'editdetalle':
            try:
                f = DetalleModeloEvaluativoForm(request.POST)
                if f.is_valid():
                    detalle = DetalleModeloEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                    if DetalleModeloEvaluativo.objects.filter(modelo=detalle.modelo, nombre=detalle.nombre).exclude(id=detalle.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un campo con ese nombre."})
                    if DetalleModeloEvaluativo.objects.filter(modelo=detalle.modelo, orden=f.cleaned_data['orden']).exclude(id=detalle.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un campo con ese numero de orden."})
                    detalle.notaminima = f.cleaned_data['notaminima']
                    detalle.notamaxima = f.cleaned_data['notamaxima']
                    detalle.decimales = f.cleaned_data['decimales']
                    detalle.migrarmoodle = f.cleaned_data['migrarmoodle']
                    detalle.determinaestadofinal = f.cleaned_data['determinaestadofinal']
                    detalle.dependiente = f.cleaned_data['dependiente']
                    detalle.orden = f.cleaned_data['orden']
                    detalle.dependeasistencia = f.cleaned_data['dependeasistencia']
                    detalle.save(request)
                    log(u'Modifico detalle de modelo evaluativo: %s' % detalle, request, "edit")
                    return JsonResponse({"result": False, 'mensaje': 'Edicion Exitosa'})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al guardar los datos."})

        if action == 'delmodelo':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                log(u"Elimino modelo evaluativo: %s" % modelo, request, "del")
                modelo.delete()
                if not ModeloEvaluativo.objects.filter(principal=True).exists():
                    modelo = ModeloEvaluativo.objects.order_by('-fecha')[0]
                    modelo.principal = True
                    modelo.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        if action == 'deldetalle':
            try:
                detalle = DetalleModeloEvaluativo.objects.get(pk=int(encrypt(request.POST['id'])))
                if detalle.en_uso():
                    return JsonResponse({"result": "bad", "mensaje": u"El detalle se encuentra en uso."})
                log(u"Elimino campo de modelo evaluativo - oma: %s" % detalle, request, "del")
                detalle.status = False
                detalle.save()
                res_json = {'error': False}
            except Exception as ex:
                transaction.set_rollback(True)
                res_json = {'error': True, "message": "Error: {}".format(ex)}
                # return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})
            return JsonResponse(res_json, safe=False)

        if action == 'logica':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                f = LogicaModeloEvaluativoForm(request.POST)
                if f.is_valid():
                    modelo.logicamodelo = f.cleaned_data['logica']
                    modelo.save(request)
                log(u"Modifico logica calculo: %s" % modelo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'inactivar':
            try:
                modelo = ModeloEvaluativo.objects.get(pk=request.POST['id'])
                if modelo.activo == True:
                    modelo.activo = False
                else:
                    modelo.activo=True
                modelo.save(request)
                log(u"Inactivo Modelo Evaluativo: %s" % modelo, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    #puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['action'] = 'add'
                    data['title'] = u'Nuevo modelo evaluativo'
                    data['form'] = ModeloEvaluativoForm()
                    return render(request, "oma_modeloevaluativo/add.html", data)
                except Exception as ex:
                    pass

            if action == 'adddetalle':
                try:
                    #puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['action'] = action
                    data['title'] = u'Nuevo campo del modelo evaluativo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    ultimodetalle = null_to_numeric(modelo.detallemodeloevaluativo_set.filter(status=True).aggregate(ultimo=Max('orden'))['ultimo'])
                    data['form'] = DetalleModeloEvaluativoForm(initial={'orden': ultimodetalle + 1})
                    template = get_template("oma_modeloevaluativo/modal/formDetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'detalle':
                try:
                    data['title'] = u'Detalle modelo evaluativo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['campos'] = modelo.detallemodeloevaluativo_set.filter(status=True)
                    return render(request, "oma_modeloevaluativo/detalle.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    #puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['action'] = 'edit'
                    data['title'] = u'Editar modelo evaluativo'
                    data['id'] = ids = int(encrypt(request.GET['id']))
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=ids)
                    data['form'] = form = ModeloEvaluativoForm(initial={'nombre': modelo.nombre,
                                                                        'principal': modelo.principal,
                                                                        'activo': modelo.activo,
                                                                        'notamaxima': modelo.notamaxima,
                                                                        'notaaprobar': modelo.notaaprobar,
                                                                        'notarecuperacion': modelo.notarecuperacion,
                                                                        'asistenciaaprobar': modelo.asistenciaaprobar,
                                                                        'asistenciarecuperacion': modelo.asistenciarecuperacion,
                                                                        'notafinaldecimales': modelo.notafinaldecimales,
                                                                        'observaciones': modelo.observaciones})

                    return render(request, "oma_modeloevaluativo/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdetalle':
                try:
                    #puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Editar campo'
                    data['action'] = request.GET['action']
                    data['detalle'] = detalle = DetalleModeloEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = DetalleModeloEvaluativoForm(initial={'nombre': detalle.nombre,
                                                                'notaminima': detalle.notaminima,
                                                                'notamaxima': detalle.notamaxima,
                                                                'decimales': detalle.decimales,
                                                                'dependiente': detalle.dependiente,
                                                                'determinaestadofinal': detalle.determinaestadofinal,
                                                                'orden': detalle.orden,
                                                                'dependeasistencia': detalle.dependeasistencia})
                    form.editar()
                    data['form'] = form
                    template = get_template("oma_modeloevaluativo/modal/formDetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    return JsonResponse({"result": False, 'message': str(ex)})

            if action == 'logica':
                try:
                    data['title'] = u'Fórmulas matemáticas para el calculo del modelo'
                    data['modelo'] = modelo = ModeloEvaluativo.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['form'] = LogicaModeloEvaluativoForm(initial={'logica': modelo.logicamodelo})
                    return render(request, "oma_modeloevaluativo/logica.html", data)
                except Exception as ex:
                    pass

            if action == 'delmodelo':
                try:
                    #puede_realizar_accion(request, 'sga.puede_modificar_modelos_evaluativos')
                    data['title'] = u'Eliminar modelo evaluativo'
                    data['modelo'] = ModeloEvaluativo.objects.get(pk=request.GET['id'])
                    return render(request, "adm_modelosevaluativos/delmodelo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                search, desde, hasta, filtro = request.GET.get('s', ''), request.GET.get('desde', ''), request.GET.get('hasta', ''), Q(status=True)
                url_vars = ""
                data['title'] = u'Modelos evaluativos'

                if 's' in request.GET:
                    data['s'] = search = request.GET['s']
                    filtro &= Q(nombre__icontains=search)
                    url_vars += f"&s={search}"

                if desde:
                    data['desde'] = desde
                    filtro &= Q(fecha__gte=desde)
                    url_vars += '&desde=' + desde

                if hasta:
                    data['hasta'] = hasta
                    url_vars += "&hasta={}".format(hasta)
                    filtro = filtro & Q(fecha__lte=hasta)

                modeloevolutivo = ModeloEvaluativo.objects.filter(filtro)
                paging = MiPaginador(modeloevolutivo, 10)
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
                return render(request, "oma_modeloevaluativo/view.html", data)
            except Exception as ex:
                pass

                # data['modelos'] = modeloevolutivo  # ModeloEvaluativo.objects.all()


