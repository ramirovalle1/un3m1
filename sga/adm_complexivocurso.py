# -*- coding: UTF-8 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import ComplexivoMateriaForm, ComplexivoClaseForm
from sga.funciones import log
from sga.models import AlternativaTitulacion, ComplexivoMateria, ComplexivoClase, Turno, ComplexivoMateriaAsignada

@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access

def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':

        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'addmateria' or action == 'editmateria':
                try:
                    f = ComplexivoMateriaForm(request.POST)
                    if f.is_valid():
                        alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alternativa'])
                        if alternativa.get_cronograma():
                            fechainicio = alternativa.get_cronograma().get().fechanucleobasicoinicio
                            fechafin = alternativa.get_cronograma().get().fechanucleoproffin
                            inicio = f.cleaned_data['fechainicio']
                            fin = f.cleaned_data['fechafin']
                            horatotal = f.cleaned_data['horatotal']
                            # horasemanal = f.cleaned_data['horasemanal']
                            # if horatotal < horasemanal:
                            #     return JsonResponse(
                            #         {"result": 'bad', "mensaje": u"Las horas semanales exceden a las horas totales"}))
                            if inicio > fin:
                                return JsonResponse({"result": 'bad', "mensaje": u"Fechas incorrectas"})
                            if not ((inicio >= fechainicio and inicio < fechafin) and ( fin > fechainicio and fin <= fechafin)):
                                return JsonResponse({"result": 'bad', "mensaje": u"Las fechas no concuerdan con el periodo de clases"})
                        else:
                            return JsonResponse({"result": 'bad', "mensaje": u"Error, Fechas no asignadas al cronograma"})

                        if action == 'addmateria':
                            if horatotal > alternativa.get_horasrestantes():
                                return JsonResponse({"result": 'bad', "mensaje": u"Las horas totales superan a las horas disponibles"})

                            materia = ComplexivoMateria()
                            materia.asignatura_id = request.POST['asignatura']
                            materia.alternativa_id = request.POST['alternativa']

                            materia.fechainicio = inicio
                            materia.fechafin = fin
                        else:
                            materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                            if horatotal > alternativa.get_horasrestantes(materia.id):
                                return JsonResponse({"result": 'bad', "mensaje": u"Las horas totales superan a las horas disponibles por el modelo de titulacion"})

                        if alternativa.get_sesion():
                            materia.sesion = alternativa.get_sesion().sesion
                        else:
                            if 'sesion'in request.POST:
                                materia.sesion = f.cleaned_data['sesion']
                        if 'profesor' in request.POST:
                            materia.profesor_id = request.POST['profesor']
                        materia.horatotal = f.cleaned_data['horatotal']
                        #materia.horasemanal = f.cleaned_data['horasemanal']
                        materia.save(request)
                        if action == 'addmateria':
                            log(u"Adiciono asignatura: %s" % materia, request, "add")
                        else:
                            log(u"Edito asignatura: %s" % materia, request, "edit")
                    else:
                         raise NameError('Error')
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})
            if action == 'deletemateria':
                try:
                    materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                    if not materia.tiene_horario() and not materia.tiene_asignacion() :
                        materia.status = False
                        materia.save(request)
                        log(u"Elimino asignatura: %s" % materia, request, "delete")
                        return JsonResponse({"result": "ok", "id": materia.id})
                    else:
                        return JsonResponse({"result": "bad", "id": materia.id, "mensaje": u"Error, la materia esta asignada a un curso u horario."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos.(%s)" % ex})

            # ---------------CLASES--------------------
            if action == 'editclase':
                try:
                    f = ComplexivoClaseForm(request.POST)
                    if f.is_valid():
                        turno = Turno.objects.get(pk=request.POST['turno'])
                        dia = request.POST['dia']
                        materia = ComplexivoMateria.objects.get(pk=request.POST['materia'])
                        clase = ComplexivoClase.objects.get(pk=request.POST['id'])
                        clase.fechainicio = materia.fechainicio
                        clase.fechafin = materia.fechafin
                        clase.aula_id = request.POST['aula']
                        clase.save(request)
                        log(u"Edito clase: %s" % clase, request, "edit")
                    else:
                         raise NameError('Error')
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos.(%s)" % ex})
            if action == 'addaula':
                try:
                    f = ComplexivoClaseForm(request.POST)
                    if f.is_valid():
                        materia = ComplexivoMateria.objects.get(pk=request.POST['id'])
                        clases = materia.complexivoclase_set.filter(status=True)
                    for clase in clases:
                        clase.aula= f.cleaned_data['aula']
                        clase.save(request)
                        log(u"Edito aula: %s" % clase, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar el aula.(%s)" % ex})
            if action == 'matricular':
                try:
                    alternativa = AlternativaTitulacion.objects.get(pk=request.POST['alt'])
                    inscritos = alternativa.matriculatitulacion_set.filter(estado=1)
                    materias = alternativa.complexivomateria_set.filter(status=True)
                    if materias.count()>0:
                        for inscrito in inscritos:
                            for materia in materias:
                                matricula = ComplexivoMateriaAsignada()
                                if not ComplexivoMateriaAsignada.objects.values('id').filter(matricula=inscrito, materia=materia).exists():
                                    matricula.materia= materia
                                    matricula.matricula = inscrito
                                    matricula.save(request)
                                    log(u"Adiciono matricula a asignatura: %s" % matricula, request, "add")
                        return JsonResponse({"result": "ok", "mensaje":u"Inscripción correcta"})
                    else:
                        return JsonResponse({"result": "ok", "mensaje":u"No existen materias"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error de inscripción.(%s)" % ex})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            # -----------MATERIAS------------------
            if action == 'materias':
                try:
                    data['title'] = u'Materias Complexivo'
                    data['alternativa'] = alternativa = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    data['materias'] = ComplexivoMateria.objects.filter(alternativa=alternativa, status=True).order_by('id')
                    return render(request, 'adm_complexivocurso/viewmateria.html', data)
                except Exception as ex:
                    pass
            elif action == 'addmateria':
                try:
                    data['title']= u'Añadir Materia Complexivo'
                    alternativa = AlternativaTitulacion.objects.get(pk=request.GET['alt'])
                    form = ComplexivoMateriaForm()
                    form.cargarprofesor(alternativa)
                    if alternativa.sesiontitulacion_set.values('id').all().exists():
                        form.initial={
                            'sesion': alternativa.get_sesion(),
                        }
                        form.tiene_sesion()
                    form.initial = {
                        'fechainicio': alternativa.get_cronograma().get().fechanucleobasicoinicio,
                        'fechafin': alternativa.get_cronograma().get().fechanucleoproffin
                    }
                    data['form'] = form
                    data['alternativa'] = alternativa
                    return render(request, 'adm_complexivocurso/addmateria.html', data)
                except Exception as ex:
                    pass
            elif action == 'editmateria':
                try:
                    data['title'] = u'Editar materia'
                    materia=ComplexivoMateria.objects.get(pk=request.GET['id'])
                    alternativa = AlternativaTitulacion.objects.get(pk=materia.alternativa_id)
                    form = ComplexivoMateriaForm(initial={
                                                        'sesion': materia.sesion,
                                                        'asignatura': materia.asignatura,
                                                        'profesor': materia.profesor,
                                                        'horatotal': materia.horatotal,
                                                        'horasemanal': materia.horasemanal,
                                                        'fechainicio': materia.fechainicio,
                                                        'fechafin': materia.fechafin,
                                                })

                    if alternativa.get_sesion():
                        form.tiene_sesion()
                    if materia.tiene_horario():
                        form.tiene_horario()
                    form.editar()
                    data['form'] = form
                    data['alternativa'] = alternativa
                    data['materia'] = materia
                    return render(request, 'adm_complexivocurso/editmateria.html', data)
                except Exception as ex:
                    pass
            elif action == 'deletemateria':
                try:
                    data['title'] = u'Eliminar materia'
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['alternativa'] = materia.alternativa_id
                    return render(request, "adm_complexivocurso/deletemateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'abrir':
                try:
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    materia.cerrado = False
                    materia.save(request)
                    log(u"Abrio materia de curso: %s" % materia, request, "open")
                    return HttpResponseRedirect('/adm_complexivocurso?action=materias&alt=' + str(materia.alternativa_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'cerrar':
                try:
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    materia.cerrado = True
                    materia.save(request)
                    # for materiaasignada in materia.materiaasignadacurso_set.all():
                    #     materiaasignada.cierre_materia_asignada()
                    log(u"Cerro materia de curso: %s" % materia, request, "close")
                    return HttpResponseRedirect('/adm_complexivocurso?action=materias&alt=' + str(materia.alternativa_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            # -----------Horarios------------------
            elif action == 'horario':
                try:
                    data['title'] = u'Horario'
                    materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['materia'] = materia
                    data['alternativa'] = materia.alternativa_id
                    data['semana'] = ['Lunes', 'Martes', 'Miercoles', 'Jueves', 'Viernes', 'Sabado', 'Domingo']
                    #data['turnos'] = materia.alternativa.get_sesion().sesion.turno_set.filter(pk__gte= 108) if materia.alternativa.get_sesion() else None
                    # data['turnos'] = turnos = materia.sesion.turno_set.all()
                    data['turnos'] = turnos = Turno.objects.filter(mostrar=True, status=True)
                    return render(request, "adm_complexivocurso/viewhorario.html", data)
                except Exception as ex:
                    pass
            elif action == 'addclase':
                try:
                    data['materia'] = materia =ComplexivoMateria.objects.get(pk=request.GET['materia'])
                    turno = request.GET['turno']
                    dia = request.GET['dia']

                    clase = ComplexivoClase()
                    clase.materia = materia
                    clase.turno_id = turno
                    clase.dia = dia
                    clase.fechainicio = materia.fechainicio
                    clase.fechafin = materia.fechafin
                    clase.save(request)
                    return HttpResponseRedirect('/adm_complexivocurso?action=horario&id=' + str(materia.id))
                except Exception as ex:
                    pass
            elif action == 'editclase':
                try:
                    data['title'] = u'Editar clase'
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    if clase.tiene_aula():
                        form = ComplexivoClaseForm(initial={'aula': clase.aula})
                    else:
                        form = ComplexivoClaseForm()
                    data['form'] = form
                    data['action'] = 'editclase'
                    data['clase'] = clase.id
                    data['turno'] = clase.turno_id
                    data['dia'] = clase.dia
                    data['materia'] = ComplexivoMateria.objects.get(pk=clase.materia_id)
                    return render(request, "adm_complexivocurso/addclase.html", data )
                except Exception as ex:
                    pass

            elif action == 'deleteclase':
                try:
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    if not clase.tiene_lecciones():
                        clase.delete()
                    else:
                        clase.activo = False
                        clase.save(request)
                    log(u"Elimino clase: %s" % clase, request, "delete")
                    return HttpResponseRedirect('/adm_complexivocurso?action=horario&id=' + str(clase.materia_id) )
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass
            elif action == 'addaula':
                try:
                    data['title'] = u"Añadir Aula a la Asignatura"
                    data['materia'] = materia = ComplexivoMateria.objects.get(pk=request.GET['id'])
                    data['alternativa'] = materia.alternativa_id
                    data['form'] = ComplexivoClaseForm()
                    return render(request, "adm_complexivocurso/addaula.html", data)
                except Exception as ex:
                    pass

            elif action == 'right':
                try:
                    clase = ComplexivoClase.objects.get(pk=request.GET['id'])
                    materia = clase.materia
                    sesion = clase.materia.sesion
                    for i in range(clase.dia + 1, 7):
                        if materia.completo_horas_semanales():
                            break
                        if sesion.dia_habilitado(i):
                            if not clase.materia.complexivoclase_set.values('id').filter(dia=i, turno=clase.turno).exists():
                                clase_clon = ComplexivoClase(materia=clase.materia,
                                                   turno=clase.turno,
                                                   fechainicio=clase.fechainicio,
                                                   fechafin=clase.fechafin,
                                                   aula=clase.aula,
                                                   dia=i,
                                                   activo=True)
                                clase_clon.save(request)
                    return HttpResponseRedirect('/adm_complexivocurso?action=horario&id='+str(clase.materia_id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return HttpResponseRedirect(request.path)
        else:
            return HttpResponseRedirect('/')