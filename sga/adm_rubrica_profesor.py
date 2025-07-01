# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models import Sum
from decorators import secure_module, last_access
from django.template.context import Context
from django.template.loader import get_template
from sga.commonviews import adduserdata
from sga.forms import CriterioRubricaForm, DetalleCriterioRubricaForm, RubricaProfesorForm
from sga.funciones import MiPaginador, log, null_to_decimal
from sga.models import RubricaMoodle, ItemRubricaMoodle, DetalleItemRubricaMoodle, CarreraRubricaMoodle, Carrera, \
    CodigoRubricaProfesor, TIPOS_TAREA,RubricaMoodleHistorial
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    perfilprincipal = request.session['perfilprincipal']
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addrubrica':
            try:
                f = RubricaProfesorForm(request.POST)
                if f.is_valid():
                    # c = f.cleaned_data['carrera']
                    # alias_carrera = c.alias
                    alias_carrera = "RUBRICA"
                    alias_usuario = persona.usuario.username
                    tipo = TIPOS_TAREA[int(f.cleaned_data['tipotarea']) - 1][1]
                    codigo = CodigoProfesorRubrica(profesor, f.cleaned_data['tipotarea'])
                    nombre = u"%s_%s_%s_%s" % (alias_carrera, alias_usuario, tipo, codigo)
                    rubrica = RubricaMoodle(nombre=nombre,
                                            tipotarea=f.cleaned_data['tipotarea'],
                                            estado=False,
                                            profesor=profesor)
                    rubrica.save(request)
                    # c = CarreraRubricaMoodle(rubrica=rubrica,carrera=f.cleaned_data['carrera'])
                    # c.save(request)
                    log(u'Adiciono rubrica moodle docente: %s' % rubrica, request, "add")
                    return JsonResponse({"result": "ok", "id": encrypt(rubrica.id)})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'additemrubrica':
            try:
                f = CriterioRubricaForm(request.POST)
                if f.is_valid():
                    rubrica = RubricaMoodle.objects.get(pk=request.POST['id'])
                    rubrica.insertar_solicitado_historial()
                    item = ItemRubricaMoodle(rubrica=rubrica,
                                             item=f.cleaned_data['item'],
                                             orden=f.cleaned_data['orden'])
                    item.save(request)
                    log(u'Adiciono criterio rubrica moodle (profesor): %s' % item, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'adddetallerubrica':
            try:
                f = DetalleCriterioRubricaForm(request.POST)
                if f.is_valid():
                    item = ItemRubricaMoodle.objects.get(pk=request.POST['id'])
                    rubrica = item.rubrica
                    rubrica.insertar_solicitado_historial()
                    detalle = DetalleItemRubricaMoodle(item=item,
                                                       descripcion=f.cleaned_data['descripcion'],
                                                       valor=f.cleaned_data['valor'],
                                                       orden=f.cleaned_data['orden'])
                    detalle.save(request)
                    log(u'Adiciono detalle criterio rubrica moodle (profesor): %s' % item, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editrubrica':
            try:
                rubrica = RubricaMoodle.objects.get(pk=request.POST['id'])
                f = RubricaProfesorForm(request.POST)
                if f.is_valid():
                    rubrica.nombre = f.cleaned_data['nombre']
                    rubrica.tipotarea = f.cleaned_data['tipotarea']
                    rubrica.estado = f.cleaned_data['estado']
                    rubrica.save(request)
                    log(u'Modifico rubrica moodle (profesor): %s' % rubrica, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'edititemrubrica':
            try:
                item = ItemRubricaMoodle.objects.get(pk=request.POST['id'])
                rubrica = item.rubrica
                rubrica.insertar_solicitado_historial()
                f = CriterioRubricaForm(request.POST)
                if f.is_valid():
                    item.item = f.cleaned_data['item']
                    item.orden = f.cleaned_data['orden']
                    item.save(request)
                    log(u'Modifico criterio rubrica moodle (profesor): %s' % item, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editdetallerubrica':
            try:
                detalle = DetalleItemRubricaMoodle.objects.get(pk=request.POST['id'])
                rubrica = detalle.item.rubrica
                rubrica.insertar_solicitado_historial()
                f = DetalleCriterioRubricaForm(request.POST)
                if f.is_valid():
                    detalle.descripcion = f.cleaned_data['descripcion']
                    detalle.orden = f.cleaned_data['orden']
                    detalle.valor = f.cleaned_data['valor']
                    detalle.save(request)
                    log(u'Modifico detalle criterio rubrica moodle (profesor): %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delrubrica':
            try:
                r = RubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
                if not r.en_uso():
                    log(u'Eliminó la rubrica moodle (profesor): %s' % r, request, "del")
                    r.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delitemrubrica':
            try:
                r = ItemRubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
                rubrica = r.rubrica
                rubrica.insertar_solicitado_historial()
                if not r.en_uso():
                    log(u'Eliminó el criterio rubrica moodle (profesor): %s' % r, request, "del")
                    r.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deldetallerubrica':
            try:
                r = DetalleItemRubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
                rubrica = r.item.rubrica
                rubrica.insertar_solicitado_historial()
                if not r.en_uso():
                    log(u'Eliminó el detalle criterio rubrica moodle (profesor): %s' % r, request, "del")
                    r.delete()
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'detalle_rubrica':
            try:
                if 'id' in request.POST:
                    arreglo = []
                    arreglosumatoria = []
                    arreglo_aux = []
                    data['rubrica'] = r = RubricaMoodle.objects.get(id=int(request.POST['id']))
                    data['criterios'] = criterios = r.itemrubricamoodle_set.filter(status=True).order_by('orden')
                    detalles = DetalleItemRubricaMoodle.objects.filter(status=True, item__rubrica=r)
                    if detalles:
                        ordenmaximo = detalles.order_by('-orden')[0].orden
                        i = 1
                        while i <= ordenmaximo:
                            sumatoria = (null_to_decimal(detalles.filter(orden=i).aggregate(sumatoria=Sum('valor'))['sumatoria'], 1))
                            arreglosumatoria.append(sumatoria)
                            i += 1

                        for c in criterios:
                            arreglo_aux.append([c.item, ''])
                            for d in c.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                                arreglo_aux.append([d.descripcion, d.valor])
                            arreglo.append(arreglo_aux)
                            arreglo_aux = []
                    data['arreglo'] = arreglo
                    data['arreglosumatoria'] = arreglosumatoria
                    data['historial'] = r.rubricamoodlehistorial_set.filter(status=True).order_by('-id')
                    template = get_template("pro_planificacion/detalle_rubrica.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': u'Nombre: %s' % r.nombre})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"No existe detalle."})

        elif action == 'publicar_rubrica':
            try:
                rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.POST['id'])))
                historial = RubricaMoodleHistorial(rubrica=rubrica,
                                                   observacion="RUBRICA APROBADA POR PROFESOR",
                                                   estado=2)
                historial.save(request)
                rubrica.estado = True
                rubrica.save(request)
                log(u'Publica rubrica (profesor): %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'duplicar_rubrica':
            try:
                rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.POST['id'])))
                rubricaoriginal=RubricaMoodle.objects.get(pk=int(encrypt(request.POST['id'])))
                alias_carrera = "RUBRICA"
                alias_usuario = persona.usuario.username
                tipo = TIPOS_TAREA[int(rubrica.tipotarea) - 1][1]
                codigo = CodigoProfesorRubrica(profesor, rubrica.tipotarea)
                nombre = u"%s_%s_%s_%s" % (alias_carrera, alias_usuario, tipo, codigo)

                rubricadup=rubrica
                rubricadup.pk=None
                rubricadup.estado=False
                rubricadup.nombre=nombre
                rubricadup.save(request)

                for item in rubricaoriginal.itemrubricamoodle_set.filter(status=True).order_by('orden'):
                    itemoriginal=rubricaoriginal.itemrubricamoodle_set.get(id=item.id)
                    item1=item
                    item1.pk=None
                    item1.rubrica=rubricadup
                    item1.save(request)
                    for deta in itemoriginal.detalleitemrubricamoodle_set.filter(status=True).order_by('orden'):
                        deta1=deta
                        deta1.pk=None
                        deta1.item=item1
                        deta1.save(request)

                historial = RubricaMoodleHistorial(rubrica=rubrica,
                                                  observacion="RUBRICA DUPLICADA POR PROFESOR",
                                                  estado=4)
                historial.save(request)
                log(u'Duplica rubrica (profesor): %s' % rubrica, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Rubricas Moodle'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addrubrica':
                try:
                    data['title'] = u'Nueva Rubrica'
                    form = RubricaProfesorForm()
                    # form.add(periodo, profesor)
                    data['form'] = form
                    return render(request, "adm_rubrica_profesor/addrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'additemrubrica':
                try:
                    data['title'] = u'Nuevo Criterio'
                    data['rubrica'] = rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CriterioRubricaForm()
                    data['form'] = form
                    return render(request, "adm_rubrica_profesor/additemrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'adddetallerubrica':
                try:
                    data['title'] = u'Nuevo Detalle'
                    data['item'] = item = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = DetalleCriterioRubricaForm()
                    data['form'] = form
                    return render(request, "adm_rubrica_profesor/adddetallerubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubrica':
                try:
                    data['title'] = u'Editar Rubrica'
                    r = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = RubricaProfesorForm(initial={'nombre': r.nombre,
                                                'tipotarea': r.tipotarea,
                                                'estado': r.estado})
                    data['form'] = form
                    data['rubrica'] = r
                    return render(request, "adm_rubrica_profesor/editrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'edititemrubrica':
                try:
                    data['title'] = u'Editar Criterio'
                    r = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = CriterioRubricaForm(initial={'item': r.item,
                                                        'orden': r.orden})
                    data['criterio'] = r
                    data['form'] = form
                    return render(request, "adm_rubrica_profesor/edititemrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editdetallerubrica':
                try:
                    data['title'] = u'Editar Detalle'
                    r = DetalleItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = DetalleCriterioRubricaForm(initial={'descripcion': r.descripcion,
                                                               'valor': r.valor,
                                                               'orden': r.orden})
                    data['detalle'] = r
                    data['form'] = form
                    return render(request, "adm_rubrica_profesor/editdetallerubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delrubrica':
                try:
                    data['title'] = u'Eliminar Rubrica'
                    data['rubrica'] = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_rubrica_profesor/delrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'delitemrubrica':
                try:
                    data['title'] = u'Eliminar Criterio'
                    data['item'] = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_rubrica_profesor/delitemrubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldetallerubrica':
                try:
                    data['title'] = u'Eliminar Detalle'
                    data['detalle'] = DetalleItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
                    return render(request, "adm_rubrica_profesor/deldetallerubrica.html", data)
                except Exception as ex:
                    pass

            elif action == 'itemsrubrica':
                try:
                    search = None
                    ids = None
                    data['title'] = u'Criterios'
                    data['rubrica'] = rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    items = rubrica.itemrubricamoodle_set.filter(status=True).order_by('orden')
                    if 's' in request.GET:
                        search = request.GET['s']
                        items = items.filter(item__icontains=search).distinct()
                    data['items'] = items
                    return render(request, "adm_rubrica_profesor/itemsrubrica.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error. %s"%ex})
                    pass

            elif action == 'detallerubrica':
                try:
                    search = None
                    ids = None
                    data['title'] = u'Detalle Criterios'
                    data['item'] = item = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
                    detalles = item.detalleitemrubricamoodle_set.filter(status=True).order_by('orden')
                    if 's' in request.GET:
                        search = request.GET['s']
                        detalles = detalles.filter(descripcion__icontains=search).distinct()
                    data['detalles'] = detalles
                    return render(request, "adm_rubrica_profesor/detallerubrica.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error. %s"%ex})
                    pass
            return HttpResponseRedirect(request.path)
        else:
            try:
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    rubricas = RubricaMoodle.objects.filter(id=int(encrypt(ids)))
                elif 's' in request.GET:
                    search = request.GET['s']
                    rubricas = RubricaMoodle.objects.filter(nombre__icontains=search, status=True,
                                                            profesor=profesor).order_by('-id')
                else:
                    rubricas = RubricaMoodle.objects.filter(status=True, profesor=profesor).order_by('-id')
                paging = MiPaginador(rubricas, 25)
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
                data['rubricas'] = page.object_list
                if 'volver' in request.GET:
                    if 'codigotareavirtual' in request.GET:
                        request.session['codigosemana'] =codigosemana=request.GET['codigosemana']
                        request.session['codigotareavirtual'] =codigotareavirtual=request.GET['codigotareavirtual']
                        request.session['volver'] =volver=request.GET['volver']
                        data['volver_action']=u"%s&codigosemana=%s&codigotareavirtual=%s"%(volver,codigosemana,codigotareavirtual)
                    elif 'codigoactividad' in request.GET:
                        request.session['codigosemana'] = codigosemana = request.GET['codigosemana']
                        request.session['codigoactividad'] = codigoactividad = request.GET['codigoactividad']
                        request.session['volver'] = volver = request.GET['volver']
                        data['volver_action'] = u"%s&codigosemana=%s&codigoactividad=%s" % (volver, codigosemana, codigoactividad)
                else:
                    if 'codigotareavirtual' in request.session:
                        codigosemana=request.session['codigosemana']
                        codigotareavirtual=request.session['codigotareavirtual']
                        volver=request.session['volver']
                        data['volver_action'] = u"%s&codigosemana=%s&codigotareavirtual=%s" % (volver, codigosemana, codigotareavirtual)
                    elif 'codigoactividad' in request.session:
                        codigosemana = request.session['codigosemana']
                        codigoactividad = request.session['codigoactividad']
                        volver = request.session['volver']
                        data['volver_action'] = u"%s&codigosemana=%s&codigoactividad=%s" % (volver, codigosemana, codigoactividad)
                return render(request, "adm_rubrica_profesor/view.html", data)
            except Exception as ex:
                pass


def CodigoProfesorRubrica(profesor, tipotarea):
    c_aux = CodigoRubricaProfesor.objects.filter(profesor=profesor, tipotarea=tipotarea, status=True)
    if c_aux:
        c = c_aux[0]
        c.codigo = c.codigo + 1
        c.save()
        return c.codigo
    else:
        c = CodigoRubricaProfesor(profesor=profesor,
                                  tipotarea=tipotarea,
                                  codigo=1)
        c.save()
        return c.codigo