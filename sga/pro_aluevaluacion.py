# -*- coding: UTF-8 -*-
import json
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from inno.models import RespuestaAlumnoDocente
from sga.commonviews import adduserdata
from sga.funciones import log
from sga.models import ProfesorMateria, miinstitucion, RespuestaEvaluacionAcreditacion, RespuestaRubrica, \
    DetalleRespuestaRubrica, RubricaPreguntas, TipoObservacionEvaluacion, ActividadDetalleDistributivoCarrera, Profesor, \
    ProfesorDistributivoHoras, CUENTAS_CORREOS, EncuestaProcesoEvaluativo, EncuestaProcesoEvaluativo_Pregunta, \
    EncuestaProcesoEvaluativo_RespuestaPregunta, EncuestaProcesoEvaluativo_DetalleRespuestaPregunta, Rubrica, \
    CriterioDocenciaPeriodo, CriterioInvestigacionPeriodo, CriterioGestionPeriodo
from sga.pro_aluevaluacion_threading import ActualizaEvaluacion, ActualizaRespuestaEvaluacion, ActualizaRespuestaRubrica
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt_alu, encrypt
from django.db.models.query_utils import Q
from posgrado.models import RespuestaEvaluacionAcreditacionPosgrado, RespuestaRubricaPosgrado, DetalleRespuestaRubricaPos, \
    InscripcionEncuestaSatisfaccionDocente, PreguntaEncuestaSatisfaccionDocente, RespuestaCuadriculaEncuestaSatisfaccionDocente, \
    OpcionCuadriculaEncuestaSatisfaccionDocente

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    data['inscripcion']=inscripcion = perfilprincipal.inscripcion
    data['periodo'] = periodo = request.session['periodo']
    data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
    if not matricula:
        try:
            return HttpResponseRedirect("/?info=Este modulo es para alumnos matriculados")
        except Exception as ex:
            pass
    data['proceso'] = proceso = matricula.nivel.periodo.proceso_evaluativo() if matricula else []

    if not proceso:
        return HttpResponseRedirect("/?info=Proceso de evaluación inactivo")

    # if proceso.tiene_cronograma_general_estudiante():
    #     isPass = False
    #     # for m in matricula.materias().filter(materia__inicioeval__isnull=False, materia__fineval__isnull=False):
    #     #     if m.materia.inicioeval <= datetime.now().date() <= m.materia.fineval:
    #     #         isPass = True
    #     #         break
    #
    #     if not isPass:
    #         coordinacion = matricula.inscripcion.coordinacion
    #         cronograma = proceso.cronograma_general_estudiante()
    #         if not cronograma.activo:
    #             return HttpResponseRedirect("/?info=Proceso de evaluación inactivo")
    #         if cronograma.cronogramas().filter(coordinacion=coordinacion).exists():
    #             cronograma_facultad = cronograma.cronogramas().filter(coordinacion=coordinacion)[0]
    #             if not cronograma_facultad.activo:
    #                 return HttpResponseRedirect("/?info=Proceso de evaluación inactivo para su facultad")
    #             if not (cronograma_facultad.fechainicio <= datetime.now().date() <= cronograma_facultad.fechafin):
    #                 return HttpResponseRedirect("/?info=Proceso de evaluación inactivo")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addencuesta':
                try:
                    with transaction.atomic():
                        profesormateria = ProfesorMateria.objects.get(pk=int(encrypt(request.POST['idp'])))
                        encuestaproceso = EncuestaProcesoEvaluativo.objects.get(pk=int(encrypt(request.POST['ide'])))
                        materiasignada = profesormateria.materia.materiaasignada_set.filter(matricula=matricula)[0]
                        if not encuestaproceso.activo:
                            return JsonResponse({"result": "bad", "mensaje": u"La encuesta no esta activa."})
                        if not encuestaproceso.estudiante:
                            return JsonResponse({"result": "bad", "mensaje": u"La encuesta no estas activo para estudiante."})
                        preguntasyrespuestas = json.loads(request.POST['lista_items1'])
                        respuestapregunta = EncuestaProcesoEvaluativo_RespuestaPregunta(materiaasignada=materiasignada,
                                                                                        profesormateria=profesormateria,
                                                                                        encuestaproceso=encuestaproceso,
                                                                                        fecharespuesta=datetime.now())
                        respuestapregunta.save(request)
                        for preguntayrespuesta in preguntasyrespuestas:
                            preguntaencuesta = EncuestaProcesoEvaluativo_Pregunta.objects.get(pk=int(preguntayrespuesta['id']))
                            if preguntaencuesta.obligatorio and not preguntayrespuesta['idop']:
                                return JsonResponse({"result": "bad", "mensaje": u"Hay pregunta que debe responder obligatoria."})
                            opcionpregunta =  preguntaencuesta.encuestaprocesoevaluativo_opcionpregunta_set.get(pk=int(encrypt(preguntayrespuesta['idop'])))
                            detallerespuestapregunta = EncuestaProcesoEvaluativo_DetalleRespuestaPregunta(respuestapregunta = respuestapregunta, opcionpregunta = opcionpregunta, respuestaopcionpregunta = preguntayrespuesta['idrsp'])
                            detallerespuestapregunta.save(request)
                    log(u'Resolvio encuesta: %s - %s - %s' % (respuestapregunta.materiaasignada, respuestapregunta.profesormateria, respuestapregunta.id), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'evaluar':
                try:
                    profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['pm']))
                    materia = profesormateria.materia
                    if RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=matricula.nivel.periodo, profesor=profesormateria.profesor, evaluador=persona, materia=materia, tipoinstrumento=1).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    with transaction.atomic():
                        materiaasignada = materia.materiaasignada_set.filter(matricula=matricula)[0]
                        if inscripcion.coordinacion_id == 7:
                            evaluacion = RespuestaEvaluacionAcreditacion(proceso=proceso,
                                                                         tipoinstrumento=1,
                                                                         profesor=profesormateria.profesor,
                                                                         tipoprofesor=profesormateria.tipoprofesor,
                                                                         evaluador=persona,
                                                                         materia=materia,
                                                                         materiaasignada=materiaasignada,
                                                                         fecha=datetime.now(),
                                                                         coordinacion=materia.coordinacion_materia(),
                                                                         accionmejoras=request.POST['accionmejoras'] ,
                                                                         formacioncontinua=request.POST['formacioncontinua'],
                                                                         carrera=materia.carrera())
                            evaluacion.save(request)
                        else:
                            respuestatut = False
                            if 'respuestatut' in request.POST:
                                if int(encrypt(request.POST['respuestatut'])) == 1:
                                    respuestatut = True
                            evaluacion = RespuestaEvaluacionAcreditacion(proceso=proceso,
                                                                         tipoinstrumento=1,
                                                                         profesor=profesormateria.profesor,
                                                                         tipoprofesor=profesormateria.tipoprofesor,
                                                                         evaluador=persona,
                                                                         materia=materia,
                                                                         materiaasignada=materiaasignada,
                                                                         fecha=datetime.now(),
                                                                         coordinacion=materia.coordinacion_materia(),
                                                                         # accionmejoras=request.POST['mejoras'] ,
                                                                         # tipomejoras_id=request.POST['nommejoras'],
                                                                         tutoriaacademica=respuestatut,
                                                                         carrera=materia.carrera())
                            evaluacion.save(request)
                            #evaluacionalumnodocente = RespuestaAlumnoDocente(respuestaevaluacion=evaluacion,
                            #                                                 nombrerespuesta=request.POST['id_nombrerespuesta'],
                            #                                                 comentario=request.POST['id_comentario'],
                            #                                                 id_pregunta=1,
                            #                                                 valor = request.POST['id_pregdocente'])
                            evaluacionalumnodocente = RespuestaAlumnoDocente(respuestaevaluacion=evaluacion,
                                                                             comentario=request.POST['id_comentario'],
                                                                             id_pregunta=1)
                            evaluacionalumnodocente.save(request)

                        listarespuesta = []
                        for elemento in request.POST['lista'].split(';'):
                            individuales = elemento.split(':')
                            rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                            rubrica = rubricapregunta.rubrica
                            if not RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica).exists():
                                respuestarubrica = RespuestaRubrica(respuestaevaluacion=evaluacion,
                                                                    rubrica=rubrica,
                                                                    valor=0)
                                respuestarubrica.save(request)
                            else:
                                respuestarubrica = RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica)[0]
                            listarespuesta.append(respuestarubrica.id)
                            detalle = DetalleRespuestaRubrica(respuestarubrica=respuestarubrica,
                                                              rubricapregunta=rubricapregunta,
                                                              valor=float(individuales[1]))
                            detalle.save(request)
                            respuestarubrica.save()
                        evaluacion.save()
                    # ActualizaEvaluacion(profesormateria.profesor.id, matricula.nivel.periodo.id)
                    log(u'Evaluacion de estudiante a profesor: %s' % materia, request, "add")
                    # send_html_mail("Evaluacion docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion()}, persona.lista_emails_envio(), [])
                    send_html_mail("Evaluación docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion(), 'tituloemail': "Evaluación docente realizada"}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'evaluarposgrado':
                try:
                    profesormateria = ProfesorMateria.objects.get(pk=int(request.POST['pm']))
                    materia = profesormateria.materia
                    if RespuestaEvaluacionAcreditacionPosgrado.objects.filter(proceso__periodo=matricula.nivel.periodo, profesor=profesormateria.profesor, evaluador=persona, materia=materia, tipoinstrumento=1).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    with transaction.atomic():
                        materiaasignada = materia.materiaasignada_set.filter(matricula=matricula)[0]

                        evaluacion = RespuestaEvaluacionAcreditacionPosgrado(proceso=proceso,
                                                                     tipoinstrumento=1,
                                                                     profesor=profesormateria.profesor,
                                                                     tipoprofesor=profesormateria.tipoprofesor,
                                                                     evaluador=persona,
                                                                     materia=materia,
                                                                     materiaasignada=materiaasignada,
                                                                     fecha=datetime.now(),
                                                                     coordinacion=materia.coordinacion_materia(),
                                                                     accionmejoras=request.POST['accionmejoras'] ,
                                                                     formacioncontinua=request.POST['formacioncontinua'],
                                                                     carrera=materia.carrera())
                        evaluacion.save(request)

                        # evaluacionalumnodocente = RespuestaAlumnoDocente(respuestaevaluacion=evaluacion,
                        #                                                  comentario=request.POST['id_comentario'],
                        #                                                  id_pregunta=1)
                        # evaluacionalumnodocente.save(request)

                        listarespuesta = []
                        for elemento in request.POST['lista'].split(';'):
                            individuales = elemento.split(':')
                            rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                            rubrica = rubricapregunta.rubrica
                            if not RespuestaRubricaPosgrado.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica).exists():
                                respuestarubrica = RespuestaRubricaPosgrado(respuestaevaluacion=evaluacion,
                                                                    rubrica=rubrica,
                                                                    valor=0)
                                respuestarubrica.save(request)
                            else:
                                respuestarubrica = RespuestaRubricaPosgrado.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica)[0]
                            listarespuesta.append(respuestarubrica.id)
                            detalle = DetalleRespuestaRubricaPos(respuestarubrica=respuestarubrica,
                                                              rubricapregunta=rubricapregunta,
                                                              valor=float(individuales[1]))
                            detalle.save(request)
                            respuestarubrica.save()
                        # evaluacion.save()
                    # ActualizaEvaluacion(profesormateria.profesor.id, matricula.nivel.periodo.id)
                    log(u'Evaluacion de estudiante a profesor: %s' % materia, request, "add")
                    # send_html_mail("Evaluacion docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion()}, persona.lista_emails_envio(), [])
                    send_html_mail("Evaluación docente realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion(), 'tituloemail': "Evaluación docente realizada"}, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'evaluardirectivos':
                try:
                    docente = Profesor.objects.get(pk=int(request.POST['pm']))
                    facultaddocente = ''
                    if ProfesorDistributivoHoras.objects.filter(periodo=matricula.nivel.periodo,profesor=docente,status=True).exists():
                        distri =  ProfesorDistributivoHoras.objects.get(periodo=matricula.nivel.periodo,profesor=docente,status=True)
                        facultaddocente = distri.coordinacion
                    else:
                        facultaddocente = docente.coordinacion
                    if RespuestaEvaluacionAcreditacion.objects.filter(proceso__periodo=matricula.nivel.periodo,profesor=docente,evaluador=persona,materia__isnull=True,tipoinstrumento=1).exists():
                        return JsonResponse({"result": "bad", 'mensaje': u'Evaluación ya existe.'})
                    with transaction.atomic():
                        evaluacion = RespuestaEvaluacionAcreditacion(proceso=proceso,
                                                                     tipoinstrumento=1,
                                                                     profesor=docente,
                                                                     evaluador=persona,
                                                                     fecha=datetime.now(),
                                                                     coordinacion=facultaddocente,
                                                                     accionmejoras=request.POST['mejoras'],
                                                                     tipomejoras_id=request.POST['nommejoras'])
                        evaluacion.save(request)
                        listarespuesta = []
                        for elemento in request.POST['lista'].split(';'):
                            individuales = elemento.split(':')
                            rubricapregunta = RubricaPreguntas.objects.get(pk=int(individuales[0]))
                            rubrica = rubricapregunta.rubrica
                            if not RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica).exists():
                                respuestarubrica = RespuestaRubrica(respuestaevaluacion=evaluacion,
                                                                    rubrica=rubrica,
                                                                    valor=0)
                                respuestarubrica.save(request)
                            else:
                                respuestarubrica = RespuestaRubrica.objects.filter(respuestaevaluacion=evaluacion, rubrica=rubrica)[0]
                            listarespuesta.append(respuestarubrica.id)
                            detalle = DetalleRespuestaRubrica(respuestarubrica=respuestarubrica,
                                                              rubricapregunta=rubricapregunta,
                                                              valor=float(individuales[1]))
                            detalle.save(request)
                            respuestarubrica.save()
                        evaluacion.save()
                    # for elemento in listarespuesta:
                    #     ActualizaRespuestaRubrica(elemento)
                    # ActualizaRespuestaEvaluacion(evaluacion.id)
                    ActualizaEvaluacion(docente.id, matricula.nivel.periodo.id)
                    log(u'Evaluacion del profesor por decano o directivo: %s' % docente, request, "add")
                    send_html_mail("Evaluación directivo realizada.", "emails/evaluaciondocente.html", {'sistema': request.session['nombresistema'], 'd': evaluacion, 't': miinstitucion(), 'tituloemail': "Evaluación directivo realizada" }, persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[2][1])
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'evaluarsatisfaccion':
                try:
                    eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.get(status=True, pk=int(request.POST['ide']))
                    for elemento in request.POST['lista'].split(';'):
                        individuales = elemento.split(':')
                        pregunta = PreguntaEncuestaSatisfaccionDocente.objects.get(pk=int(individuales[0]))
                        encuesta = pregunta.encuesta
                        if not RespuestaCuadriculaEncuestaSatisfaccionDocente.objects.filter(inscripcionencuesta=eInscripcion,
                                                                                             pregunta=pregunta).exists():
                            op = OpcionCuadriculaEncuestaSatisfaccionDocente.objects.filter(status=True,valor=int(individuales[1])).first()
                            respuesta = RespuestaCuadriculaEncuestaSatisfaccionDocente(inscripcionencuesta=eInscripcion,
                                                                                       opcioncuadricula=op,
                                                                                       pregunta=pregunta,
                                                                                       respuesta=float(individuales[1]))
                            respuesta.save(request)
                    eInscripcion.respondio = True
                    eInscripcion.save(request)
                    log(u'Respondió encuesta: %s' % eInscripcion, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'evaluar':
                try:
                    data['title'] = 'Evaluar docente'
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    if inscripcion.coordinacion_id == 9:
                        if inscripcion.carrera.modalidad == 3:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteroadmisionvirtual()
                        else:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteroadmision()
                    elif inscripcion.coordinacion_id == 7:
                        if profesormateria.tipoprofesor_id == 8:
                            ePeriodo = profesormateria.materia.nivel.periodo
                            rubricas = Rubrica.objects.filter(habilitado=True, proceso__periodo=ePeriodo,
                                                              para_tutor=True, para_hetero=True, rvigente=True).exclude(tiporubrica=4).distinct()
                            data['rubricas'] = rubricas
                        else:
                            estado = True
                            ePeriodo = profesormateria.materia.nivel.periodo
                            distributivo = profesormateria.profesor.distributivohoraseval(ePeriodo)
                            criteriosdocencia = CriterioDocenciaPeriodo.objects.filter(
                                detalledistributivo__distributivo=distributivo,
                                detalledistributivo__hetero=True)
                            criteriosinvestigacion = CriterioInvestigacionPeriodo.objects.filter(
                                detalledistributivo__distributivo=distributivo)
                            criteriosgestion = CriterioGestionPeriodo.objects.filter(
                                detalledistributivo__distributivo=distributivo,
                                detalledistributivo__hetero=True)

                            resultados = RespuestaEvaluacionAcreditacion.objects.values('evaluador_id').filter(
                                status=True,
                                tipoinstrumento=1,
                                proceso__periodo=ePeriodo,
                                # profesor=profesormateria.profesor,
                                materia=profesormateria.materia,
                                respuestarubrica__rubrica__para_hetero=True).exclude(respuestarubrica__rubrica__rvigente=True)

                            if resultados.exists():
                                estado = False

                            lista1 = Rubrica.objects.filter(rubricacriteriodocencia__criterio__in=criteriosdocencia,
                                                            para_materiapractica=False, habilitado=True,
                                                            rubricamodalidadtipoprofesor__modalidad=profesormateria.materia.nivel.modalidad,
                                                            proceso__periodo=ePeriodo,
                                                            para_hetero=True, rvigente=estado).exclude(para_tutor=True).distinct()

                            data['rubricas'] = rubricas = lista1
                    else:
                        if inscripcion.carrera.modalidad == 3:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_heterovirtual()
                        else:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricas_hetero()
                    data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True,activo=True).order_by('nombre')
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    if inscripcion.coordinacion_id == 7:
                        return render(request, "pro_aluevaluacion/evaluaripec.html", data)
                    else:
                        return render(request, "pro_aluevaluacion/evaluar.html", data)
                except Exception as ex:
                    pass

            if action == 'evaluarportipoprofesor':
                try:
                    data['respuestatut'] = respuestatut = request.GET['respuestatut']
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=request.GET['id'])
                    if inscripcion.coordinacion_id == 7:
                        if inscripcion.carrera.modalidad == 3:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricastipoprofesor_heterovirtual()
                        else:
                            data['rubricas'] = rubricas = profesormateria.mis_rubricastipoprofesor_hetero()
                        data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True,activo=True).order_by('nombre')
                        data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                        data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                        data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                        return render(request, "pro_aluevaluacion/evaluaripec.html", data)
                    else:
                        # data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteropregrado()
                        data['rubricas'] = rubricas = profesormateria.mis_rubricas_heteropregradoevaluar(int(encrypt(respuestatut)))
                        data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True,activo=True).order_by('nombre')
                        data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                        data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                        data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                        return render(request, "pro_aluevaluacion/evaluar.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluardirectivos':
                try:
                    data['profesormateria'] = docente = Profesor.objects.get(pk=request.GET['id'])
                    data['rubricas'] = rubricas = docente.mis_rubricas_heterodirectivos(matricula.nivel.periodo.id)
                    data['combomejoras'] = TipoObservacionEvaluacion.objects.filter(tipoinstrumento=1, tipo=1, status=True,activo=True).order_by('nombre')
                    data['tiene_docencia'] = rubricas.filter(tipo_criterio=1).exists()
                    data['tiene_investigacion'] = rubricas.filter(tipo_criterio=2).exists()
                    data['tiene_gestion'] = rubricas.filter(tipo_criterio=3).exists()
                    return render(request, "pro_aluevaluacion/evaluardirectivos.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluarmateria':
                try:
                    data['profesormateria'] = profesormateria = ProfesorMateria.objects.get(pk=int(encrypt_alu(request.GET['id'])))
                    data['encuestaproceso'] = profesormateria.puede_evaluar_encuesta_proceso_evaluacion(matricula, matricula.nivel.periodo)
                    return render(request, "pro_aluevaluacion/evaluarmateria.html", data)
                except Exception as ex:
                    pass

            elif action == 'evaluarsatisfaccion':
                try:
                    data['title'] = u'Encuesta de satisfaccion'
                    ahora = datetime.now().date()
                    eInscripcion = InscripcionEncuestaSatisfaccionDocente.objects.get(status=True, id=int(request.GET['id']))
                    data['eInscripcion'] = eInscripcion
                    data['eEncuesta'] = eInscripcion.encuesta
                    return render(request, "pro_aluevaluacion/evaluarsatisfaccion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Evaluación Docente'
                data['profesores'] = matricula.mis_profesores_acreditacion()

                if matricula.nivel.periodo.tipo.id == 3:
                    eNews = RespuestaEvaluacionAcreditacionPosgrado.objects.filter(tipoinstrumento=1, proceso=proceso,
                                                                                          evaluador=persona).order_by('materiaasignada__materia')

                    eOlds = RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=1, proceso=proceso,
                                                                                          evaluador=persona).order_by('materiaasignada__materia')

                    eEvaluaciones = []

                    for eNew in eNews:
                        eEvaluaciones.append({
                            "id": eNew.id,
                            "profesor": eNew.profesor,
                            "materia": eNew.materia,
                            "fecha": eNew.fecha
                        })

                    for eOld in eOlds:
                        eEvaluaciones.append({
                            "id": eOld.id,
                            "profesor": eOld.profesor,
                            "materia": eOld.materia,
                            "fecha": eOld.fecha
                        })

                    data['evaluaciones'] = eEvaluaciones
                    ahora = datetime.now().date()
                    eMateriasSatisfaccion = InscripcionEncuestaSatisfaccionDocente.objects.filter(status=True, materiaasignada__materia__nivel__periodo=periodo,
                                                                                                  inicio__lte=ahora, fin__gte=ahora, materiaasignada__matricula__inscripcion__persona=persona)
                    data['eMateriasSatisfaccion'] = eMateriasSatisfaccion
                    data['eRespuestasSatisfaccion'] = eMateriasSatisfaccion.filter(respondio=True)
                    return render(request, "pro_aluevaluacion/view_posgrado.html", data)
                else:
                    listadoc = []
                    data['evaluacionesencuesta'] = matricula.profesormateria_evaluado(matricula.nivel.periodo)
                    data['evaluaciones'] = respuestaeval = RespuestaEvaluacionAcreditacion.objects.filter(tipoinstrumento=1, proceso=proceso,  evaluador=persona).order_by('materiaasignada__materia')
                    # data['docentesdirectores'] = detdistributivo = DetalleDistributivo.objects.filter(distributivo__periodo=periodo,criteriogestionperiodo__isnull=False,hetero=True,status=True)
                    docentesdirectores=[]
                    if not matricula.retiradomatricula:
                        docentesdirectores = ActividadDetalleDistributivoCarrera.objects.values_list('actividaddetalle__criterio__distributivo__profesor_id',flat=True).filter(actividaddetalle__criterio__distributivo__periodo=matricula.nivel.periodo,
                                                                                                                                                                               actividaddetalle__criterio__criteriogestionperiodo__isnull=False,
                                                                                                                                                                               actividaddetalle__criterio__hetero=True,
                                                                                                                                                                               actividaddetalle__criterio__status=True,
                                                                                                                                                                               carrera=inscripcion.carrera,
                                                                                                                                                                               status=True).distinct()
                        for listadirectores in docentesdirectores:
                            profe = Profesor.objects.get(pk=listadirectores)
                            if profe.mis_rubricas_heterodirectivos(matricula.nivel.periodo.id):
                                if not respuestaeval.filter(profesor=profe, materia__isnull=True, materiaasignada__isnull=True).exists():
                                    listadoc.append(profe.id)
                    data['docentesdirectores'] = Profesor.objects.filter(pk__in=listadoc)
                    return render(request, "pro_aluevaluacion/view.html", data)
            except Exception as ex:
                pass
