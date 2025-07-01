# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from django.db.models import Sum
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import RubricaForm, CriterioRubricaForm, DetalleCriterioRubricaForm
from sga.funciones import MiPaginador, log,null_to_decimal
from sga.models import RubricaMoodle, ItemRubricaMoodle, DetalleItemRubricaMoodle, CarreraRubricaMoodle, Carrera, \
    RubricaMoodleHistorial, ProfesorMateria
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
    # mis_carreras = Carrera.objects.filter(grupocoordinadorcarrera__group__in=persona.grupos()).distinct()
    if request.method == 'POST':
        action = request.POST['action']

        # if action == 'add':
        #     try:
        #         f = RubricaForm(request.POST)
        #         if f.is_valid():
        #             rubrica = RubricaMoodle(nombre=f.cleaned_data['nombre'],
        #                                     tipotarea=f.cleaned_data['tipotarea'],
        #                                     estado=f.cleaned_data['estado'])
        #             rubrica.save(request)
        #             for carrera in f.cleaned_data['carreras']:
        #                 c = CarreraRubricaMoodle(rubrica=rubrica,
        #                                          carrera=carrera)
        #                 c.save(request)
        #             log(u'Adiciono rubrica moodle: %s' % rubrica, request, "add")
        #             return JsonResponse({"result": "ok", "id": encrypt(rubrica.id)})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # if action == 'additem':
        #     try:
        #         f = CriterioRubricaForm(request.POST)
        #         if f.is_valid():
        #             rubrica = RubricaMoodle.objects.get(pk=request.POST['id'])
        #             item = ItemRubricaMoodle(rubrica=rubrica,
        #                                      item=f.cleaned_data['item'],
        #                                      orden=f.cleaned_data['orden'])
        #             item.save(request)
        #             log(u'Adiciono criterio rubrica moodle: %s' % item, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # if action == 'adddetalle':
        #     try:
        #         f = DetalleCriterioRubricaForm(request.POST)
        #         if f.is_valid():
        #             item = ItemRubricaMoodle.objects.get(pk=request.POST['id'])
        #             detalle = DetalleItemRubricaMoodle(item=item,
        #                                                descripcion=f.cleaned_data['descripcion'],
        #                                                valor=f.cleaned_data['valor'],
        #                                                orden=f.cleaned_data['orden'])
        #             detalle.save(request)
        #             log(u'Adiciono detalle criterio rubrica moodle: %s' % item, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'edit':
        #     try:
        #         rubrica = RubricaMoodle.objects.get(pk=request.POST['id'])
        #         f = RubricaForm(request.POST)
        #         if f.is_valid():
        #             rubrica.nombre = f.cleaned_data['nombre']
        #             rubrica.tipotarea = f.cleaned_data['tipotarea']
        #             rubrica.estado = f.cleaned_data['estado']
        #             rubrica.save(request)
        #             rubrica.carrerarubricamoodle_set.filter(status=True).delete()
        #             for carrera in f.cleaned_data['carreras']:
        #                 c = CarreraRubricaMoodle(rubrica=rubrica,
        #                                          carrera=carrera)
        #                 c.save(request)
        #
        #             log(u'Modifico rubrica moodle: %s' % rubrica, request, "edit")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'edititem':
        #     try:
        #         item = ItemRubricaMoodle.objects.get(pk=request.POST['id'])
        #         f = CriterioRubricaForm(request.POST)
        #         if f.is_valid():
        #             item.item = f.cleaned_data['item']
        #             item.orden = f.cleaned_data['orden']
        #             item.save(request)
        #             log(u'Modifico criterio rubrica moodle: %s' % item, request, "edit")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'editdetalle':
        #     try:
        #         detalle = DetalleItemRubricaMoodle.objects.get(pk=request.POST['id'])
        #         f = DetalleCriterioRubricaForm(request.POST)
        #         if f.is_valid():
        #             detalle.descripcion = f.cleaned_data['descripcion']
        #             detalle.orden = f.cleaned_data['orden']
        #             detalle.valor = f.cleaned_data['valor']
        #             detalle.save(request)
        #             log(u'Modifico detalle criterio rubrica moodle: %s' % detalle, request, "edit")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'del':
        #     try:
        #         r = RubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
        #         if not r.en_uso():
        #             log(u'Eliminó la rubrica moodle: %s' % r, request, "del")
        #             r.delete()
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'delitem':
        #     try:
        #         r = ItemRubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
        #         if not r.en_uso():
        #             log(u'Eliminó el criterio rubrica moodle: %s' % r, request, "del")
        #             r.delete()
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        # elif action == 'deldetalle':
        #     try:
        #         r = DetalleItemRubricaMoodle.objects.get(pk=int(request.POST['id']), status=True)
        #         if not r.en_uso():
        #             log(u'Eliminó el detalle criterio rubrica moodle: %s' % r, request, "del")
        #             r.delete()
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar ya se encuentra en uso."})
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
        #
        if action == 'detalle_rubrica':
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

        if action == 'aprobar_rubrica':
            try:
                if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                    rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.POST['id'])))
                    historial = RubricaMoodleHistorial(rubrica=rubrica,
                                                       observacion=request.POST['obs'],
                                                       estado=int(request.POST['st']))
                    historial.save(request)

                    if 2 == int(request.POST['st']):
                        rubrica.estado = True
                        rubrica.save(request)
                        log(u'Aprobó la rubrica del profesor (Director) %s' % (rubrica), request, "add")
                        # silabo.materia.crear_actualizar_silabo_curso()
                    else:
                        log(u'Rechazó la rubrica del profesor (Director) %s' % (rubrica), request, "add")
                    return JsonResponse({"result": "ok", "idm": rubrica.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Rubricas Moodle'
        if 'action' in request.GET:
            action = request.GET['action']

            # if action == 'add':
            #     try:
            #         data['title'] = u'Nueva Rubrica'
            #         form = RubricaForm()
            #         form.add(periodo)
            #         data['form'] = form
            #         return render(request, "adm_rubrica_director/add.html", data)
            #     except Exception as ex:
            #         pass
            #
            # if action == 'additem':
            #     try:
            #         data['title'] = u'Nuevo Criterio'
            #         data['rubrica'] = rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         form = CriterioRubricaForm()
            #         data['form'] = form
            #         return render(request, "adm_rubrica_director/additem.html", data)
            #     except Exception as ex:
            #         pass
            #
            # if action == 'adddetalle':
            #     try:
            #         data['title'] = u'Nuevo Detalle'
            #         data['item'] = item = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         form = DetalleCriterioRubricaForm()
            #         data['form'] = form
            #         return render(request, "adm_rubrica_director/adddetalle.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'edit':
            #     try:
            #         data['title'] = u'Editar Rubrica'
            #         r = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         idcarreras = r.carrerarubricamoodle_set.values_list('carrera_id', flat=True).filter(status=True)
            #         carreras = Carrera.objects.filter(pk__in=idcarreras)
            #         form = RubricaForm(initial={'nombre': r.nombre,
            #                                     'tipotarea': r.tipotarea,
            #                                     'carreras': carreras,
            #                                     'estado': r.estado})
            #         form.add(periodo)
            #         data['form'] = form
            #         data['rubrica'] = r
            #         return render(request, "adm_rubrica_director/edit.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'edititem':
            #     try:
            #         data['title'] = u'Editar Criterio'
            #         r = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         form = CriterioRubricaForm(initial={'item': r.item,
            #                                             'orden': r.orden})
            #         data['criterio'] = r
            #         data['form'] = form
            #         return render(request, "adm_rubrica_director/edititem.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'editdetalle':
            #     try:
            #         data['title'] = u'Editar Detalle'
            #         r = DetalleItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         form = DetalleCriterioRubricaForm(initial={'descripcion': r.descripcion,
            #                                                    'valor': r.valor,
            #                                                    'orden': r.orden})
            #         data['detalle'] = r
            #         data['form'] = form
            #         return render(request, "adm_rubrica_director/editdetalle.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'del':
            #     try:
            #         data['title'] = u'Eliminar Rubrica'
            #         data['rubrica'] = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
            #         return render(request, "adm_rubrica_director/del.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'delitem':
            #     try:
            #         data['title'] = u'Eliminar Criterio'
            #         data['item'] = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
            #         return render(request, "adm_rubrica_director/delitem.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'deldetalle':
            #     try:
            #         data['title'] = u'Eliminar Detalle'
            #         data['detalle'] = DetalleItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])), status=True)
            #         return render(request, "adm_rubrica_director/deldetalle.html", data)
            #     except Exception as ex:
            #         pass
            #
            # elif action == 'items':
            #     try:
            #         search = None
            #         ids = None
            #         data['title'] = u'Criterios'
            #         data['rubrica'] = rubrica = RubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         items = rubrica.itemrubricamoodle_set.filter(status=True).order_by('orden')
            #         if 's' in request.GET:
            #             search = request.GET['s']
            #             items = items.filter(item__icontains=search).distinct()
            #         data['items'] = items
            #         return render(request, "adm_rubrica_director/items.html", data)
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error. %s"%ex})
            #         pass
            #
            # if action == 'detalle':
            #     try:
            #         search = None
            #         ids = None
            #         data['title'] = u'Detalle Criterios'
            #         data['item'] = item = ItemRubricaMoodle.objects.get(pk=int(encrypt(request.GET['id'])))
            #         detalles = item.detalleitemrubricamoodle_set.filter(status=True).order_by('orden')
            #         if 's' in request.GET:
            #             search = request.GET['s']
            #             detalles = detalles.filter(descripcion__icontains=search).distinct()
            #         data['detalles'] = detalles
            #         return render(request, "adm_rubrica_director/detalle.html", data)
            #     except Exception as ex:
            #         return JsonResponse({"result": "bad", "mensaje": u"Error. %s"%ex})
            #         pass
            #
            return HttpResponseRedirect(request.path)
        else:
            try:
                idprofesores = ProfesorMateria.objects.values_list('profesor__id', flat=True).filter(status=True, principal=True, materia__nivel__periodo=periodo, materia__asignaturamalla__malla__carrera__in=persona.mis_carreras())
                search = None
                ids = None
                if 'id' in request.GET:
                    ids = request.GET['id']
                    rubricas = RubricaMoodle.objects.filter(id=int(encrypt(ids)), profesor__isnull=False)
                elif 's' in request.GET:
                    search = request.GET['s']
                    rubricas = RubricaMoodle.objects.filter(nombre__icontains=search, status=True, profesor__isnull=False, profesor__id__in=idprofesores).order_by('-id')
                else:
                    rubricas = RubricaMoodle.objects.filter(status=True, profesor__isnull=False, profesor__id__in=idprofesores).order_by('-id')
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
                data['estado_seleccionado'] = 1
                if 'estado_seleccionado' in request.GET:
                    data['estado_seleccionado'] = int(request.GET['estado_seleccionado'])
                return render(request, "adm_rubrica_director/view.html", data)
            except Exception as ex:
                pass
