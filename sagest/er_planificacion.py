# -*- coding: UTF-8 -*-

import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template

from sagest.forms import PlanAccionPreventivaForm, CabeceraPlanAccionPreventivaForm, SubirEvidenciaForm, \
    EvaluacionRiesgoForm, DetalleEvaluacionRiesgoForm
from sagest.models import EvaluacionRiesgo, PlanAccionPreventiva, DetallePlanAccionPreventiva, \
    EvidenciaDetallePlanAccionPreventiva, DetalleEvaluacionRiesgo, GRADO_RIESGO, EvidenciaDetalleEvaluacionRiesgo
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, convertir_fecha, generar_nombre, log


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'detalle_planificacion':
            try:
                data['evaluacion'] = evaluacion = EvaluacionRiesgo.objects.get(pk=int(request.POST['id']))
                data['observacion'] = evaluacion.detalleevaluacionriesgo_set.all()
                template = get_template("er_planificacion/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'confirmacion':
            try:
                planificacion = DetallePlanAccionPreventiva.objects.get(pk=int(request.POST['id']))
                planificacion.planrealizado = 2 if int(request.POST['valor']) == 1 else 3
                planificacion.save(request)
                evaluacion = planificacion.detalleevaluacionriesgo.codigoevaluacion
                evaluacion.actualizar_estado(request)
                log(u'Confirmar planificación: %s' % planificacion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'revertir':
            try:
                planificacion = DetallePlanAccionPreventiva.objects.get(pk=int(request.POST['id']))
                if int(request.POST['valor']):
                    planificacion.planrealizado = 1
                    planificacion.save(request)
                    evaluacion = planificacion.detalleevaluacionriesgo.codigoevaluacion
                    evaluacion.actualizar_estado(request)
                    log(u'Confirmar planificación: %s' % planificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cerrar':
            try:
                planificacion = DetallePlanAccionPreventiva.objects.get(pk=int(request.POST['id']))
                planificacion.cerrada = True
                planificacion.save(request)
                evaluacion = planificacion.detalleevaluacionriesgo.codigoevaluacion
                evaluacion.actualizar_estado(request)
                log(u'Confirmar planificación: %s' % planificacion, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'subir_evidencia':
            try:
                planificacion = DetallePlanAccionPreventiva.objects.get(pk=int(request.POST['id']))
                form = SubirEvidenciaForm(planificacion, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("foto_", newfile._name)
                    foto = EvidenciaDetallePlanAccionPreventiva(detalleplanaccionpreventiva=planificacion,
                                                                archivo=newfile)
                    foto.save(request)
                    log(u'Adicionar evidencia a planificación: %s' % planificacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. "})

        if action == 'planificar':
            try:
                form = PlanAccionPreventivaForm(request.POST)
                if form.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    evaluacion = EvaluacionRiesgo.objects.get(pk=request.POST['id'])
                    if not datos:
                        return JsonResponse({"result": "bad", "mensaje": u"Debe ingresar datos"})
                    planaccion = PlanAccionPreventiva(codigoevaluacion=evaluacion,
                                                      fecha=form.cleaned_data['fecha'],
                                                      responsable=form.cleaned_data['responsablec'],
                                                      periodo=form.cleaned_data['periodo'])
                    planaccion.save(request)
                    for elemento in datos:
                        detalle = DetallePlanAccionPreventiva(planaccionpreventiva=planaccion,
                                                              detalleevaluacionriesgo_id=int(elemento['detalle']),
                                                              medida=elemento['medida'],
                                                              responsable_id=int(elemento['resp']),
                                                              fechainicio=convertir_fecha(elemento['fi']),
                                                              fechafin=convertir_fecha(elemento['ff']))
                        detalle.save(request)
                    evaluacion.actualizar_estado(request)
                    log(u'Planifico plan de acción: %s' % planaccion, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editarplanificacion':
            try:
                form = PlanAccionPreventivaForm(request.POST)
                if form.is_valid():
                        datos = json.loads(request.POST['lista_items1'])
                        planificacion = PlanAccionPreventiva.objects.get(pk=request.POST['id'])
                        planificacion.fecha = form.cleaned_data['fecha']
                        planificacion.periodo = form.cleaned_data['periodo']
                        planificacion.responsable = form.cleaned_data['responsablec']
                        planificacion.save(request)
                        planificacion.detalleplanaccionpreventiva_set.all().delete()
                        for elemento in datos:
                            detalle = DetallePlanAccionPreventiva(planaccionpreventiva=planificacion,
                                                                  detalleevaluacionriesgo_id=int(elemento['detalle']),
                                                                  medida=elemento['medida'],
                                                                  responsable_id=int(elemento['resp']),
                                                                  fechainicio=convertir_fecha(elemento['fi']),
                                                                  fechafin=convertir_fecha(elemento['ff']))
                            detalle.save(request)
                        log(u'Adiciono plan acción preventiva: %s' % planificacion, request, "add")
                        return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'add':
            try:
                form = EvaluacionRiesgoForm(request.POST)
                if form.is_valid():
                    evaluacion = EvaluacionRiesgo(fecha=form.cleaned_data['fecha'],
                                                  bloque=form.cleaned_data['bloque'],
                                                  responsable=form.cleaned_data['responsable'],
                                                  departamento=form.cleaned_data['departamento'],
                                                  seccion=form.cleaned_data['seccion'],
                                                  trabajador=form.cleaned_data['trabajador'],
                                                  trabajadoresexpuestos=form.cleaned_data['trabajadoresexpuestos'] if not form.cleaned_data['trabajador'] else 1,
                                                  observacion=form.cleaned_data['observacion'])
                    evaluacion.save(request)
                    log(u'Adiciono evaluación de riesgo: %s' % evaluacion, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminar':
            try:
                evaluacion = EvaluacionRiesgo.objects.get(pk=request.POST['id'])
                log(u'Elimino evaluación de riesgo: %s' % evaluacion, request, "del")
                evaluacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'gradoriesgo':
            try:
                probabilidad = int(request.POST['p'])
                severidad = int(request.POST['s'])
                nombre = GRADO_RIESGO[0][2]
                for elemento in GRADO_RIESGO:
                    if elemento[0] == probabilidad and elemento[1] == severidad:
                        nombre = elemento[2]
                        break
                return JsonResponse({"result": "ok", "nombre": nombre})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addplanaccionprev':
            try:
                form = DetalleEvaluacionRiesgoForm(request.POST)
                evaluacion = EvaluacionRiesgo.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    detalleevaluacion = DetalleEvaluacionRiesgo(codigoevaluacion=evaluacion,
                                                                agente=form.cleaned_data['agente'],
                                                                probabilidaddanio=form.cleaned_data['probabilidaddanio'],
                                                                severidaddanio=form.cleaned_data['severidaddanio'],
                                                                comentario=form.cleaned_data['comentario'])
                    detalleevaluacion.save(request)
                    log(u'Adiciono plan acción preventiva: %s' % detalleevaluacion, request, "add")
                    return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarplanaccionprev':
            try:
                detalleevaluacion = DetalleEvaluacionRiesgo.objects.get(pk=request.POST['id'])
                log(u'Elimino plan acción preventiva: %s' % detalleevaluacion, request, "del")
                detalleevaluacion.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        if action == 'editplanaccionprev':
            form = DetalleEvaluacionRiesgoForm(request.POST)
            detalleevaluacion = DetalleEvaluacionRiesgo.objects.get(pk=request.POST['id'])
            if form.is_valid():
                try:
                    detalleevaluacion.agente = form.cleaned_data['agente']
                    detalleevaluacion.probabilidaddanio = form.cleaned_data['probabilidaddanio']
                    detalleevaluacion.severidaddanio = form.cleaned_data['severidaddanio']
                    detalleevaluacion.comentario = form.cleaned_data['comentario']
                    detalleevaluacion.save(request)
                    log(u'Adiciono plan acción preventiva: %s' % detalleevaluacion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
            else:
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        if action == 'detalle_riesgo':
            try:
                data['detalleevaluacion'] = detalleevaluacion = DetalleEvaluacionRiesgo.objects.get(pk=int(request.POST['id']))
                data['comentario'] = detalleevaluacion
                template = get_template("er_planificacion/detalleriesgo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'subir_evidencia_dano':
            try:
                detalleevaluacion = DetalleEvaluacionRiesgo.objects.get(pk=int(request.POST['id']))
                form = SubirEvidenciaForm(detalleevaluacion, request.FILES)
                if form.is_valid():
                    newfile = request.FILES['archivo']
                    newfile._name = generar_nombre("foto_", newfile._name)
                    foto = EvidenciaDetalleEvaluacionRiesgo(detalleevaluacion=detalleevaluacion,
                                                            archivo=newfile)
                    foto.save(request)
                    log(u'Adicionar evidencia a evaluacion: %s' % detalleevaluacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. "})

        return JsonResponse({"result": "bad", "mensaje": "Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'detalleriesgos':
                try:
                    data['title'] = u'Listado de Riesgos'
                    data['evaluacion'] = evaluacion = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    data['riesgos'] = evaluacion.detalleevaluacionriesgo_set.all()
                    return render(request, "er_planificacion/detalleriesgos.html", data)
                except Exception as ex:
                    pass

            if action == 'planificar':
                try:
                    data['title'] = u'Planificar'
                    data['evaluacion'] = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    data['form'] = PlanAccionPreventivaForm()
                    data['form2'] = CabeceraPlanAccionPreventivaForm()
                    data['fecha'] = datetime.now().date()
                    return render(request, "er_planificacion/planificar.html", data)
                except Exception as ex:
                    pass

            if action == 'editarplanificacion':
                try:
                    data['title'] = u'Planificar'
                    data['planificacion'] = planificacion = PlanAccionPreventiva.objects.get(pk=request.GET['id'])
                    data['form'] = PlanAccionPreventivaForm(initial={'fecha': planificacion.fecha,
                                                                     'responsablec': planificacion.responsable,
                                                                     'periodo': planificacion.periodo})
                    data['form2'] = CabeceraPlanAccionPreventivaForm()
                    data['fecha'] = datetime.now().date()
                    return render(request, "er_planificacion/editarplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'detalleplanificacion':
                try:
                    data['title'] = u'Detalle planificación'
                    data['evaluacion'] = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    data['reporte_1'] = obtener_reporte('planificacion_preventiva')
                    return render(request, "er_planificacion/detalleplanificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'confirmacion':
                try:
                    data['title'] = u'Confirmar planificación'
                    data['planificacion'] = DetallePlanAccionPreventiva.objects.get(pk=int(request.GET['id']))
                    data['valor'] = int(request.GET['v'])
                    return render(request, "er_planificacion/confirmacion.html", data)
                except:
                    pass

            if action == 'revertir':
                try:
                    data['title'] = u'Confirmar planificación'
                    data['planificacion'] = DetallePlanAccionPreventiva.objects.get(pk=int(request.GET['id']))
                    data['valor'] = int(request.GET['v'])
                    return render(request, "er_planificacion/revertir.html", data)
                except:
                    pass

            if action == 'cerrar':
                try:
                    data['title'] = u'Confirmar cerrar la planificación'
                    data['planificacion'] = DetallePlanAccionPreventiva.objects.get(pk=int(request.GET['id']))
                    return render(request, "er_planificacion/cerrar.html", data)
                except:
                    pass

            if action == 'subir_evidencia':
                try:
                    data['title'] = u'Subir foto'
                    data['form'] = SubirEvidenciaForm()
                    data['planificacion'] = DetallePlanAccionPreventiva.objects.get(pk=int(request.GET['id']))
                    return render(request, "er_planificacion/subir_evidencia.html", data)
                except Exception as ex:
                    pass

            if action == 'add':
                try:
                    data['title'] = u'Adicionar evaluación'
                    form = EvaluacionRiesgoForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "er_planificacion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar evaluación'
                    data['evaluacion'] = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    return render(request, 'er_planificacion/eliminar.html', data)
                except Exception as ex:
                    pass

            if action == 'detalleevaluacion':
                try:
                    data['title'] = u'Detalle evaluación'
                    data['evaluacion'] = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    form = DetalleEvaluacionRiesgoForm()
                    data['form'] = form
                    return render(request, "er_planificacion/detalleevaluacion.html", data)
                except Exception as ex:
                    pass

            if action == 'addplanaccionprev':
                try:
                    data['title'] = u'Adicionar plan acción preventiva'
                    data['evaluacion'] = EvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    data['form'] = DetalleEvaluacionRiesgoForm()
                    return render(request, "er_planificacion/addplanaccionprev.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarplanaccionprev':
                try:
                    data['title'] = u'Eliminar evaluación'
                    data['detalleevaluacion'] = DetalleEvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    return render(request, 'er_planificacion/eliminarplanaccionprev.html', data)
                except Exception as ex:
                    pass

            if action == 'editplanaccionprev':
                try:
                    data['title'] = u'Modificar plan acción preventiva'
                    data['detalleevaluacion'] = detalleevaluacion = DetalleEvaluacionRiesgo.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(detalleevaluacion)
                    form = DetalleEvaluacionRiesgoForm(initial=initial)
                    data['form'] = form
                    return render(request, 'er_planificacion/editplanaccionprev.html', data)
                except Exception as ex:
                    pass

            if action == 'subir_evidencia_dano':
                try:
                    data['title'] = u'Subir foto'
                    data['form'] = SubirEvidenciaForm()
                    data['detalle'] = DetalleEvaluacionRiesgo.objects.get(pk=int(request.GET['id']))
                    return render(request, "er_planificacion/subir_evidencia_dano.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Planificación de evaluaciones de riesgo'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                evaluaciones = EvaluacionRiesgo.objects.filter(Q(departamento__nombre__icontains=search, status=True) |
                                                               Q(seccion__nombre__icontains=search, status=True) |
                                                               Q(bloque__nombre__icontains=search, status=True) |
                                                               Q(trabajador__nombres__icontains=search, status=True) |
                                                               Q(trabajador__aplellido1__icontains=search, status=True) |
                                                               Q(trabajador__aplellido2__icontains=search, status=True) |
                                                               Q(trabajador__cedula__icontains=search, status=True) |
                                                               Q(observacion__icontains=search))
            elif 'id' in request.GET:
                ids = request.GET['id']
                evaluaciones = EvaluacionRiesgo.objects.filter(id=ids)
            else:
                evaluaciones = EvaluacionRiesgo.objects.all()
            paging = MiPaginador(evaluaciones, 25)
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
            data['evaluaciones'] = page.object_list
            data['reporte_0'] = obtener_reporte('evaluacion_riesgo')
            return render(request, "er_planificacion/view.html", data)