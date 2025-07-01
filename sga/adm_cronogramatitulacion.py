# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import CronogramaNucleoConocimientoComplexivoForm, CronogramaAprobacionExamenComplexivoForm, \
    CronogramaPropuestaPracticaComplexivoForm, CronogramaRevisionEstudianteComplexivoForm
from sga.funciones import log
from sga.models import AlternativaTitulacion, CronogramaExamenComplexivo, DetalleRevisionCronograma


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'complexivonucleoconocimiento':
                try:
                    f= CronogramaNucleoConocimientoComplexivoForm(request.POST)
                    if f.is_valid():
                        cronograma= CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechanucleobasicoinicio'],f.cleaned_data['fechanucleoproffin']):
                           return JsonResponse({"result": "bad", "mensaje": u"No se encuentra dentro del rango del periodo de titulación"})
                        if not f.cleaned_data['fechanucleobasicoinicio'] <= f.cleaned_data['fechanucleoproffin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio no puede mayor a fecha fin"})
                        cronograma.fechanucleobasicoinicio = f.cleaned_data['fechanucleobasicoinicio']
                        cronograma.fechanucleoproffin = f.cleaned_data['fechanucleoproffin']
                        cronograma.save(request)
                        log(u"Asigna clases a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id,cronograma.alternativatitulacion.paralelo,cronograma.alternativatitulacion.carrera), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

            if action == 'complexivoaprobacionexamen':
                try:
                    f= CronogramaAprobacionExamenComplexivoForm(request.POST)
                    if f.is_valid():
                        cronograma= CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaaprobexameninicio'],f.cleaned_data['fechaaprobexamenfin']):
                           return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas de aprobacion de examen complexivo con periodo de titulación"})
                        if not f.cleaned_data['fechaaprobexameninicio'] <= f.cleaned_data['fechaaprobexamenfin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de aprobacion de examen complexivo no puede ser mayor que la fecha fin"})
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechasubircalificacionesinicio'],f.cleaned_data['fechasubircalificacionesfin']):
                           return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas subida de calificaciones de examen complexivo con periodo de titulación"})
                        if not f.cleaned_data['fechasubircalificacionesinicio'] <= f.cleaned_data['fechasubircalificacionesfin']:
                            return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio subida de calificaciones de examen complexivo no puede ser mayor que la fecha fin"})
                        if f.cleaned_data['fechaaprobexamengraciainicio'] and f.cleaned_data['fechaaprobexamengraciafin']:
                            if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaaprobexamengraciainicio'],f.cleaned_data['fechaaprobexamengraciafin']):
                               return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas de aprobación de examen de gracia con periodo de titulación"})
                            if not f.cleaned_data['fechaaprobexamengraciainicio'] <= f.cleaned_data['fechaaprobexamengraciafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio de aprobación de examen de gracia no puede ser mayor que la fecha fin"})
                        if f.cleaned_data['fechasubircalificacionesgraciainicio'] and f.cleaned_data['fechasubircalificacionesgraciafin']:
                            if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechasubircalificacionesgraciainicio'],f.cleaned_data['fechasubircalificacionesgraciafin']):
                               return JsonResponse({"result": "bad", "mensaje": u"No se encuentra en rango las fechas subida de calificaciones de examen de gracia con periodo de titulación"})
                            if not f.cleaned_data['fechasubircalificacionesgraciainicio'] <= f.cleaned_data['fechasubircalificacionesgraciafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha inicio subida de calificaciones de examen de gracia no puede ser mayor que la fecha fin"})
                        cronograma.fechaaprobexameninicio = f.cleaned_data['fechaaprobexameninicio']
                        cronograma.fechaaprobexamenfin = f.cleaned_data['fechaaprobexamenfin']
                        cronograma.fechaaprobexamengraciainicio = f.cleaned_data['fechaaprobexamengraciainicio']
                        cronograma.fechaaprobexamengraciafin = f.cleaned_data['fechaaprobexamengraciafin']
                        cronograma.fechasubircalificacionesinicio = f.cleaned_data['fechasubircalificacionesinicio']
                        cronograma.fechasubircalificacionesfin = f.cleaned_data['fechasubircalificacionesfin']
                        cronograma.fechasubircalificacionesgraciainicio = f.cleaned_data['fechasubircalificacionesgraciainicio']
                        cronograma.fechasubircalificacionesgraciafin = f.cleaned_data['fechasubircalificacionesgraciafin']
                        cronograma.save(request)
                        log(u"Asigna aprobarexamen a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id,cronograma.alternativatitulacion.paralelo,cronograma.alternativatitulacion.carrera), request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

            if action == 'complexivopropuestapractica':
                try:
                    f= CronogramaPropuestaPracticaComplexivoForm(request.POST)
                    if f.is_valid():
                        cronograma= CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaeleccionpropuestainicio'], f.cleaned_data['fechaeleccionpropuestafin']):
                            return JsonResponse({"result": "bad","mensaje": u"No se encuentra en rango las fechas elección de tema/línea de investigación con periodo de titulación"})
                        if not f.cleaned_data['fechaeleccionpropuestainicio'] <= f.cleaned_data['fechaeleccionpropuestafin']:
                            return JsonResponse({"result": "bad","mensaje": u"La fecha inicio de elección de tema/línea de investigación no puede ser mayor que la fecha fin"})
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechapropuestainicio'], f.cleaned_data['fechapropuestafin']):
                            return JsonResponse({"result": "bad","mensaje": u"No se encuentra en rango las fechas ejecución y revisión con periodo de titulación"})
                        if not f.cleaned_data['fechapropuestainicio'] <= f.cleaned_data['fechapropuestafin']:
                            return JsonResponse({"result": "bad","mensaje": u"La fecha inicio de ejecución y revisión no puede ser mayor que la fecha fin"})
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechaentregadocumentoinicio'], f.cleaned_data['fechaentregadocumentofin']):
                            return JsonResponse({"result": "bad","mensaje": u"No se encuentra en rango las fechas entrega de carpetas al tribunal con periodo de titulación"})
                        if not f.cleaned_data['fechaentregadocumentoinicio'] <= f.cleaned_data['fechaentregadocumentofin']:
                            return JsonResponse({"result": "bad","mensaje": u"La fecha inicio de entrega de carpetas al tribunal no puede ser mayor que la fecha fin"})
                        if cronograma.alternativatitulacion.grupotitulacion.esta_en_fecha_periodo(f.cleaned_data['fechadefensaevaluacioninicio'], f.cleaned_data['fechadefensaevaluacionfin']):
                            return JsonResponse({"result": "bad","mensaje": u"No se encuentra en rango las fechas evaluación del tribunal con periodo de titulación"})
                        if not f.cleaned_data['fechadefensaevaluacioninicio'] <= f.cleaned_data['fechadefensaevaluacionfin']:
                            return JsonResponse({"result": "bad","mensaje": u"La fecha inicio de evaluación del tribunal no puede ser mayor que la fecha fin"})
                        cronograma.fechapropuestainicio = f.cleaned_data['fechapropuestainicio']
                        cronograma.fechapropuestafin = f.cleaned_data['fechapropuestafin']
                        cronograma.fechaeleccionpropuestafin = f.cleaned_data['fechaeleccionpropuestafin']
                        cronograma.fechaeleccionpropuestainicio = f.cleaned_data['fechaeleccionpropuestainicio']
                        cronograma.fechaentregadocumentoinicio = f.cleaned_data['fechaentregadocumentoinicio']
                        cronograma.fechaentregadocumentofin = f.cleaned_data['fechaentregadocumentofin']
                        cronograma.fechardefensaevaluacioninicio = f.cleaned_data['fechadefensaevaluacioninicio']
                        cronograma.fechardefensaevaluacionfin = f.cleaned_data['fechadefensaevaluacionfin']
                        cronograma.save(request)
                        log(u"Asigna propuesta práctica a cronograma con alternativa %s - [%s] %s" % (cronograma.alternativatitulacion_id,cronograma.alternativatitulacion.paralelo,cronograma.alternativatitulacion.carrera), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

            if action == 'complexivorevisionestudiante' or action == 'editcomplexivorevisionestudiante' :
                try:
                    f = CronogramaRevisionEstudianteComplexivoForm(request.POST)
                    if f.is_valid():
                        if action == 'complexivorevisionestudiante':
                            cronograma= CronogramaExamenComplexivo.objects.get(pk=request.POST['id'])
                            revision = DetalleRevisionCronograma()
                        else:
                            revision = DetalleRevisionCronograma.objects.get(pk=request.POST['id'])
                            cronograma = revision.cronograma
                        if cronograma.registrar_revision() or action == 'editcomplexivorevisionestudiante' :
                            if f.cleaned_data['fechainicio'] < cronograma.fechapropuestainicio \
                                    or f.cleaned_data['fechainicio'] > cronograma.fechapropuestafin \
                                    or f.cleaned_data['fechafin'] < cronograma.fechapropuestainicio \
                                    or f.cleaned_data['fechafin'] > cronograma.fechapropuestafin \
                                    or f.cleaned_data['calificacioninicio'] < cronograma.fechapropuestainicio \
                                    or f.cleaned_data['calificacioninicio'] > cronograma.fechapropuestafin \
                                    or f.cleaned_data['calificacionfin'] < cronograma.fechapropuestainicio \
                                    or f.cleaned_data['calificacionfin'] > cronograma.fechapropuestafin:
                                return JsonResponse({"result": "bad", "mensaje": u"Las fechas deben estar dentro del rango definidos para la realizacion de la propuesta.."})
                            if f.cleaned_data['fechafin'] < f.cleaned_data['fechainicio']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de fin de desarrolo de propuesta no puede ser mayor a la fecha de inicio de la misma"})
                            if f.cleaned_data['calificacioninicio'] < f.cleaned_data['fechafin']:
                                return JsonResponse({"result": "bad", "mensaje": u"la fecha de calificacion debe ser posterior a la fecha de realizacion de propuesta"})
                            if f.cleaned_data['calificacionfin'] < f.cleaned_data['calificacioninicio']:
                                return JsonResponse({"result": "bad", "mensaje": u"La fecha de calificacion final no puede ser menor a la fecha de calificacion inicial"})
                            if action == 'editcomplexivorevisionestudiante':
                                if revision.anterior():
                                    anterior =  revision.anterior()
                                    if f.cleaned_data['fechainicio'] < anterior.calificacionfin:
                                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de revisión debe ser mayor a la fecha de calificacion de la revisión anterior"})
                                if revision.posterior():
                                    posterior = revision.posterior()
                                    if f.cleaned_data['calificacionfin']> posterior.fechainicio:
                                        return JsonResponse({"result": "bad", "mensaje": u"La Fecha de calificación debe ser menor a la fecha de revision del registro revision posterior"})
                            else:
                                if cronograma.detallerevisioncronograma_set.filter(status=True).exists():
                                    ultima = cronograma.ultima_revision()
                                    if f.cleaned_data['fechainicio'] < ultima.calificacionfin:
                                        return JsonResponse({"result": "bad", "mensaje": u"La fecha de revision de propuesta debe ser mayor a la fecha de calificacion del registro de revision anterior"})


                            revision.cronograma = cronograma
                            revision.fechainicio = f.cleaned_data['fechainicio']
                            revision.fechafin = f.cleaned_data['fechafin']
                            revision.calificacioninicio = f.cleaned_data['calificacioninicio']
                            revision.calificacionfin = f.cleaned_data['calificacionfin']
                            revision.save(request)
                            log(u"Adiciona revisión estudiante a cronograma con alternativa %s - [%s] %s" % (
                                cronograma.alternativatitulacion_id, cronograma.alternativatitulacion.paralelo,
                                cronograma.alternativatitulacion.carrera), request, "add")
                            return JsonResponse({"result": "ok"})
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

            if action == 'deleterevision':
                try:
                    revision = DetalleRevisionCronograma.objects.get(pk=request.POST['id'])
                    revision.status = False
                    revision.save(request)
                    log(u"Elimina revisión propuesta %s de cronograma %s con alternativa %s - [%s] %s" % (
                        revision.id,revision.cronograma_id, revision.cronograma.alternativatitulacion_id,
                        revision.cronograma.alternativatitulacion.paralelo,
                        revision.cronograma.alternativatitulacion.carrera), request, "delete")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error, no se guardaron los cambios."})

            if action=='newcronograma':
                try:
                    alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alt'])
                    if alternativa.tipotitulacion.tipo==2:
                        if not CronogramaExamenComplexivo.objects.filter(alternativatitulacion=alternativa).exists():
                            cronograma = CronogramaExamenComplexivo()
                            cronograma.alternativatitulacion = alternativa
                            cronograma.save(request)
                            log(u"Crea cronograma %s con alternativa %s - [%s] %s" % (
                                cronograma.id, cronograma.alternativatitulacion_id,
                                cronograma.alternativatitulacion.paralelo,
                                cronograma.alternativatitulacion.carrera), request, "Add")
                        else:
                            cronograma=CronogramaExamenComplexivo.objects.get(alternativatitulacion=request.POST['alt'])
                        return JsonResponse({"result": "ok", "action":"examencomplexivo", "id":cronograma.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'nucleoconocimiento':
                try:
                    data['title'] = u'Editar Nucleo Conocimiento'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))

                    data['form'] = CronogramaNucleoConocimientoComplexivoForm(initial={
                        'fechanucleobasicoinicio' : cronograma.fechanucleobasicoinicio,
                        'fechanucleoproffin': cronograma.fechanucleoproffin
                    })
                    return render(request, "adm_cronogramatitulacion/complexivonucleoconocimiento.html", data)
                except Exception as ex:
                    pass
            if action == 'aprobacionexamen':
                try:
                    data['title'] = u'Cronograma Aprobacion Examen Complexivo'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    form = CronogramaAprobacionExamenComplexivoForm(initial={
                        'fechaaprobexameninicio': cronograma.fechaaprobexameninicio,
                        'fechaaprobexamenfin':cronograma.fechaaprobexamenfin,
                        'fechaaprobexamengraciainicio':cronograma.fechaaprobexamengraciainicio,
                        'fechaaprobexamengraciafin': cronograma.fechaaprobexamengraciafin,
                        'fechasubircalificacionesinicio':cronograma.fechasubircalificacionesinicio,
                        'fechasubircalificacionesfin': cronograma.fechasubircalificacionesfin
                        # 'fechasubircalificacionesgraciainicio': cronograma.fechasubircalificacionesgraciainicio,
                        # 'fechasubircalificacionesgraciafin': cronograma.fechasubircalificacionesgraciafin
                    })
                    form.quitar_campos()
                    data['form'] = form
                    return render(request, "adm_cronogramatitulacion/complexivoaprobacionexamen.html", data)
                except Exception as ex:
                    pass

            if action == 'propuestapractica':
                try:
                    data['title'] = u'Cronograma Propuesta Practica Complexivo'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaPropuestaPracticaComplexivoForm(initial={
                        'fechaeleccionpropuestainicio' : cronograma.fechaeleccionpropuestainicio,
                        'fechaeleccionpropuestafin' : cronograma.fechaeleccionpropuestafin,
                        'fechapropuestainicio': cronograma.fechapropuestainicio,
                        'fechapropuestafin': cronograma.fechapropuestafin,
                        'fechaentregadocumentoinicio' : cronograma.fechaentregadocumentoinicio,
                        'fechaentregadocumentofin' : cronograma.fechaentregadocumentofin,
                        'fechadefensaevaluacioninicio' : cronograma.fechardefensaevaluacioninicio,
                        'fechadefensaevaluacionfin' : cronograma.fechardefensaevaluacionfin
                    })
                    return render(request, "adm_cronogramatitulacion/complexivopropuestapractica.html", data)
                except Exception as ex:
                    pass

            if action == 'revisionestudiante':
                try:
                    data['title'] = u'Cronograma Revisión Propuesta Práctica'
                    data['cronograma'] = cronograma=CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['form'] = CronogramaRevisionEstudianteComplexivoForm()
                    return render(request, "adm_cronogramatitulacion/complexivorevisionestudiante.html", data)
                except Exception as ex:
                    pass

            if action == 'editrevision':
                try:
                    data['title'] = u'Cronograma Revisión Propuesta Práctica'
                    data['revision']=revision = DetalleRevisionCronograma.objects.get(pk=int(request.GET['id']))
                    data['cronograma'] = revision.cronograma
                    data['form'] = CronogramaRevisionEstudianteComplexivoForm(initial={
                        'fechafin': revision.fechafin,
                        'fechainicio': revision.fechainicio,
                        'calificacionfin': revision.calificacionfin,
                        'calificacioninicio': revision.calificacioninicio
                    })
                    return render(request, "adm_cronogramatitulacion/editcomplexivorevisionestudiante.html", data)
                except Exception as ex:
                    pass

            if action == 'deleterevision':
                try:
                    data['title'] = u"Eliminar Revisión"
                    revision = DetalleRevisionCronograma.objects.get(pk=request.GET['id'])
                    data['mensaje'] = u"Esta seguro de eliminar la revisión: %s" % (request.GET['no'])
                    data['revision'] = revision
                    data['cronograma'] = revision.cronograma
                    return render(request, "adm_cronogramatitulacion/deleterevision.html", data)
                except Exception as ex:
                    pass

            if action == 'examencomplexivo':
                try:
                    data['title'] = u'CRONOGRAMA DE EXAMEN COMPLEXIVO'
                    data['cronograma'] = cronograma = CronogramaExamenComplexivo.objects.get(pk=int(request.GET['id']))
                    data['revisiones'] = cronograma.detallerevisioncronograma_set.filter(status=True).order_by('id')
                    data['alternativa'] = AlternativaTitulacion.objects.get(pk=cronograma.alternativatitulacion_id)
                    return render(request, "adm_cronogramatitulacion/viewexamencomplexivo.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)