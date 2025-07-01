# -*- coding: UTF-8 -*-
from datetime import datetime, date, timedelta
from sga.funciones import remover_caracteres_especiales_unicode, generar_nombre
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.forms import  model_to_dict
from decorators import secure_module, last_access
#from migrar_moodle import carreras
from sagest.models import Rubro
from sga.commonviews import adduserdata
from sga.funciones import log
from inno.funciones import obtener_acta_compromiso_por_nivel, asignaturas_aprobadas_primero_nivel_especifico, obtener_acta_compromiso_por_nivel, obtener_materia_asignada_vinculacion_por_nivel_v2
from sga.funciones_templatepdf import generar_acta_compromiso_v3
from inno.models import ExtraProyectoVinculacionInscripcion
from sga.models import ProyectosInvestigacion, ProyectoVinculacionInscripcion, AsignaturaMalla, RecordAcademico, \
    Carrera, ProyectosInvestigacionCarreras, CarrerasParticipantes, ParticipantesMatrices,PeriodoInscripcionVinculacion,\
    CarreraInscripcionVinculacion, InformesProyectoVinculacionEstudiante, ItinerariosVinculacionMalla, Notificacion
from sga.forms import InformeProyectoVinculacionEstudianteForm


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
@last_access
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']

    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    carrera = inscripcion.carrera
    hoy = datetime.now().date()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                proyectosinvestigacion = ProyectosInvestigacion.objects.get(pk=request.POST['id'])
                periodoinscripcion = PeriodoInscripcionVinculacion.objects.get(pk=request.POST['periodo'])
                cupos = CarreraInscripcionVinculacion.objects.get(carrera__carrera=carrera, periodo=periodoinscripcion).diferencia()
                if ProyectoVinculacionInscripcion.objects.filter(status=True, periodo__periodo=periodo,inscripcion=inscripcion, estado__in=[1,2]).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya cuenta con una inscripción activa en este periodo"})
                if ProyectoVinculacionInscripcion.objects.filter(status=True, proyectovinculacion=proyectosinvestigacion,inscripcion=inscripcion).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya tiene una inscripción activa en este proyecto"})
                if ParticipantesMatrices.objects.filter(status=True, proyecto=proyectosinvestigacion,inscripcion=inscripcion).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra registrado en este proyecto"})
                if ParticipantesMatrices.objects.filter(status=True, estado = 0, inscripcion = inscripcion, actividad__isnull = True).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Tiene aún una participación en proceso"})
                if cupos==0:
                    return JsonResponse({"result": "bad", "mensaje": u"Cupo no disponible"})

                proyectovinculacioninscripcion = ProyectoVinculacionInscripcion(
                    proyectovinculacion=proyectosinvestigacion,
                    inscripcion=inscripcion,
                    periodo=periodoinscripcion
                )
                proyectovinculacioninscripcion.save(request)

                if inscripcion.carrera.modalidad == 3:
                    matricula = inscripcion.matricula_periodo(periodo)
                    materias_asignada_vinculacion = obtener_materia_asignada_vinculacion_por_nivel_v2(matricula.id)
                    pdf = materias_asignada_vinculacion.actacompromisovinculacion
                else:
                    pdf, response = generar_acta_compromiso_v3(proyectovinculacioninscripcion)
                if pdf:
                    extradetalle = ExtraProyectoVinculacionInscripcion(proyectoinscripcion=proyectovinculacioninscripcion, actacompromisovinculacion=pdf)
                    extradetalle.save(request)

                    # APROBADO AUTOMATICO
                    proyectovinculacioninscripcion.estado = 2
                    proyectovinculacioninscripcion.save(request)

                    if not ParticipantesMatrices.objects.filter(proyecto=proyectovinculacioninscripcion.proyectovinculacion, inscripcion=proyectovinculacioninscripcion.inscripcion, status=True).exists():
                        programas = ParticipantesMatrices(matrizevidencia_id=2,
                                                          proyecto=proyectovinculacioninscripcion.proyectovinculacion,
                                                          inscripcion=proyectovinculacioninscripcion.inscripcion,
                                                          horas=0,
                                                          preinscripcion=proyectovinculacioninscripcion
                                                          )
                        programas.save(request)

                        saludo = 'Estimada ' if proyectovinculacioninscripcion.inscripcion.persona.sexo_id == 1 else 'Estimado '
                        notificacion = Notificacion(
                            titulo=f"Estado de solicitud de participación en proyectos de vinculación",
                            cuerpo=f"{saludo}  {proyectovinculacioninscripcion.inscripcion.persona.nombre_completo_inverso()}, su preinscripción al proyecto de vinculación {programas.proyecto.nombre} ha sido aprobada automaticamente por el sistema.",
                            destinatario=proyectovinculacioninscripcion.inscripcion.persona,
                            url="/alu_proyectovinculacion?panel=3",
                            fecha_hora_visible=datetime.now() + timedelta(days=2),
                            content_type=None,
                            object_id=None,
                            prioridad=1,
                            app_label='sga')
                        notificacion.save()
                    # FIN APROBADO AUTOMATICO

                log(u'Solicitud Proyecto Vinculación: %s' % proyectovinculacioninscripcion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delete':
            try:
                proyectovinculacioninscripcion = ProyectoVinculacionInscripcion.objects.get(pk=request.POST['id'])
                proyectosinvestigacion = ProyectosInvestigacion.objects.get(pk=proyectovinculacioninscripcion.proyectovinculacion.id)

                proyectosinvestigacion.saldoo=proyectosinvestigacion.saldoo+1
                proyectosinvestigacion.save(request)

                if proyectovinculacioninscripcion.estado != 1:
                    return JsonResponse({"result": "bad", "mensaje": u"El registro esta en uso."})
                log(u'Elimino Solicitud proyecto Vinculacion: %s' % proyectovinculacioninscripcion, request, "del")
                proyectovinculacioninscripcion.delete()
                #proyectovinculacioninscripcion.saldo(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'cargarinforme':
            try:
                informe = InformesProyectoVinculacionEstudiante.objects.get(id=int(request.POST['id']))
                f = InformeProyectoVinculacionEstudianteForm(request.POST)
                if f.is_valid():
                    newfile = request.FILES['archivo']
                    extension = newfile._name.split('.')
                    tam = len(extension)
                    exte = extension[tam - 1]
                    if newfile.size > 4194304:
                        transaction.set_rollback(True)
                        return JsonResponse(
                            {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                    if not exte in ['pdf', 'jpg', 'jpeg', 'png', 'jpeg', 'peg']:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf,.jpg, .jpeg"})
                    persona_informe = persona.cedula
                    newfile._name = generar_nombre("{}__{}".format(persona_informe, informe.informedocente.nombre_input()),
                                                   newfile._name)
                    informe.archivo = newfile
                    informe.estado = 3
                    informe.fechasubidaarchivo = datetime.now().date()
                    informe.save(request)
                    log(u'Informe de Cumplimiento %s' % (informe), request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": u"Error al obtener los datos. {}".format(ex)})


        # if action == 'validacion':
        #     try:
        #         if not inscripcion.graduado():
        #             proyectosinvestigacion = ProyectosInvestigacion.objects.get(pk=request.POST['idproyecto'])
        #             nivelmallamatricula = proyectosinvestigacion.carrerasproyecto_set.filter(status=True, carrera=inscripcion.carrera)[0].nivelmalla.orden
        #             mallainscripcion = inscripcion.malla_inscripcion().malla
        #             asignaturas = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla=mallainscripcion, nivelmalla__id__lt=nivelmallamatricula, status=True, opcional=False)
        #             cantidadvalidacionreprobada = RecordAcademico.objects.filter(inscripcion=inscripcion, asignaturamalla__nivelmalla__id__lt=nivelmallamatricula,asignatura__id__in=asignaturas, aprobada=False, status=True).count()
        #             if cantidadvalidacionreprobada > 0:
        #                 return JsonResponse({"result": "bad", "mensaje": u"Solo los alumnos que tiene aprobadas todas las materias de los niveles que ha cursado hasta ahora y con notas mayor igual a %s puede solicitar ayudantia de catedra." % notamaximaperiodo})
        #             return JsonResponse({"result": "ok"})
        #         else:
        #             return JsonResponse({"result": "bad", "mensaje": u"Los alumnos graduados no pueden solicitar proyecto vinculación."})
        #
        #     except Exception as ex:
        #         pass


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Confirmar Solicitud Proyecto'
                    data['proyectosinvestigacion'] = ProyectosInvestigacion.objects.get(pk=request.GET['id'])
                    data['periodovinculacion'] = request.GET['periodo']
                    return render(request, "alu_proyectovinculacion/add.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar solicitud de proyecto vinculacion'
                    data['proyectovinculacioninscripcion'] = ProyectoVinculacionInscripcion.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_proyectovinculacion/delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'cargarinformesvinculacion':
                try:
                    data['title'] = u'Mis Informes De Proyecto de Vinculación'
                    data['fechaactual'] = datetime.now().date()
                    data['id'] = id = int(request.GET['id'])
                    # inscripcion = int(request.GET['ides'])
                    data['inscripcionproyecto'] = inscripcionproyecto = ParticipantesMatrices.objects.get(pk=id)
                    for infdoc in inscripcionproyecto.proyecto.informes_vinculacion():
                        if not InformesProyectoVinculacionEstudiante.objects.filter(status=True, proyecto=inscripcionproyecto, informedocente=infdoc).exists():
                            informes = InformesProyectoVinculacionEstudiante(proyecto=inscripcionproyecto, informedocente=infdoc)
                            informes.save(request)
                    excluidos = InformesProyectoVinculacionEstudiante.objects.filter(status=True, proyecto=inscripcionproyecto).exclude(informedocente__in=inscripcionproyecto.proyecto.informes_vinculacion().values_list('id', flat=True))
                    for excluido in excluidos:
                        excluido.status = False
                        excluido.save(request)
                    return render(request, 'alu_proyectovinculacion/listadomisinformes.html', data)
                except Exception as ex:
                    pass

            # elif action == 'cargarinformesvinculacion':
            #     try:
            #         data['title'] = u'Mis Informes De Proyecto de Vinculación'
            #         data['fechaactual'] = datetime.now().date()
            #         data['id'] = id = int(request.GET['id'])
            #         data['inscripcionproyecto'] = inscripcionproyecto = ProyectoVinculacionInscripcion.objects.get(pk=id)
            #         # data['inscripcionproyecto'] = inscripcionproyecto = ProyectosInvestigacion.objects.get(pk=id)
            #         for infdoc in inscripcionproyecto.proyectovinculacion.informes_vinculacion():
            #             if not InformesProyectoVinculacionEstudiante.objects.filter(status=True, proyecto__proyectovinculacion=inscripcionproyecto.proyectovinculacion, informedocente=infdoc).exists():
            #                 informes = InformesProyectoVinculacionEstudiante(proyecto=inscripcionproyecto.proyectovinculacion, informedocente=infdoc)
            #                 informes.save(request)
            #         excluidos = InformesProyectoVinculacionEstudiante.objects.filter(status=True, proyecto__proyectovinculacion=inscripcionproyecto.proyectovinculacion).exclude(informedocente__in=inscripcionproyecto.proyectovinculacion.informes_vinculacion().values_list('id', flat=True))
            #         for excluido in excluidos:
            #             excluido.status = False
            #             excluido.save(request)
            #         return render(request, 'alu_proyectovinculacion/listadomisinformes.html', data)
            #     except Exception as ex:
            #         pass

            elif action == 'cargarinforme':
                try:
                    data['informe'] = informe = InformesProyectoVinculacionEstudiante.objects.get(pk=int(request.GET['id']))
                    data['formulario'] = form = InformeProyectoVinculacionEstudianteForm(initial=model_to_dict(informe))
                    template = get_template('alu_proyectovinculacion/modal/modal_cargarinforme.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass


            # elif action == 'solicitudes':
            #     try:
            #         data['title'] = u'Solicitud de Proyecto Vinculación'
            #
            #         data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
            #         if not matricula:
            #             return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
            #         if Rubro.objects.values("id").filter(persona=persona, cancelado=False, matricula=matricula,
            #                                              status=True, fechavence__lt=datetime.now().date()).exists():
            #             return HttpResponseRedirect("/?info=Ud. aun no ha cancelado valores pendientes por matriculado")
            #         nivels = matricula.nivelmalla.orden
            #
            #         if nivels <= 10 and nivels >= 4:
            #             data['nivelmallla'] = nivels
            #
            #         data['proyectos'] = CarreraInscripcionVinculacion.objects.filter(carrera__carrera=carrera,
            #                                                                          periodo__fechainicio__lte=datetime.now(),
            #                                                                          periodo__fechafin__gte=datetime.now(),
            #                                                                          periodo__aprobado=True)
            #
            #         # solicitudes = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona,status=True,proyectovinculacion__fechainicio__year=str(datetime.now().year))
            #         solicitudes = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona,
            #                                                                     status=True)
            #         data['solicitudes'] = solicitudes
            #
            #         return render(request, "alu_proyectovinculacion/view.html", data)
            #     except Exception as ex:
            #         pass

            return HttpResponseRedirect(request.path)

        else:
            # try:
            #     data['title1'] = u'Mis Proyectos de Vinculación'
            #     data['title2'] = u'Proyectos Aperturados'
            #     data['title3'] = u'Mis Solicitudes'
            #     data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
            #     if not matricula:
            #         return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
            #     if Rubro.objects.values("id").filter(persona=persona, cancelado=False, matricula=matricula,
            #                                          status=True, fechavence__lt=datetime.now().date()).exists():
            #         return HttpResponseRedirect("/?info=Ud. aun no ha cancelado valores pendientes por matriculado")
            #     nivels = matricula.nivelmalla.orden
            #
            #     if nivels <= 10 and nivels >= 4:
            #         data['nivelmallla'] = nivels
            #
            #     # nivel_itinerario = ItinerariosVinculacionMalla.objects.filter(status=True, malla__carrera=carrera).values_list('nivel', flat=True).first()
            #     #
            #     # if nivels >= nivel_itinerario:
            #     #     data['nivelmallla'] = nivels
            #     # elif nivels <= 10 and nivels >= 4:
            #     #     data['nivelmallla'] = nivels
            #
            #     data['proyectos'] = proyectos = CarreraInscripcionVinculacion.objects.filter(carrera__carrera=carrera,
            #                                                                      periodo__fechainicio__lte=datetime.now(),
            #                                                                      periodo__fechafin__gte=datetime.now(),
            #                                                                      periodo__aprobado=True)
            #
            #     data['solicitudes'] = solicitudes = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona, status=True)
            #     # solicitudes = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona,status=True,proyectovinculacion__fechainicio__year=str(datetime.now().year))
            #     # data['misproyectos'] = misproyectos = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona,status=True, estado=2)
            #     # data['misproyectos'] = misproyectos = proyectos.carrera.proyecto.participantesmatrices_set.filter(status=True, inscripcion__persona=persona)
            #     data['misproyectos'] = misproyectos = ParticipantesMatrices.objects.filter(status=True, inscripcion__persona=persona)
            #
            #     data['cantidad_solicitudes'] = solicitudes.count()
            #     data['cantidad_proyectos'] = proyectos.count()
            #     data['cantidad_misproyectos'] = misproyectos.count()
            #     return render(request, "alu_proyectovinculacion/view.html", data)
            # except Exception as ex:
            #     pass


            try:
                panel = None
                data['title1'] = u'Mis Proyectos de Vinculación'
                data['title2'] = u'Proyectos Aperturados'
                data['title3'] = u'Mis Solicitudes'
                data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
                if not matricula:
                    return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
                if Rubro.objects.values("id").filter(persona=persona, cancelado=False, matricula=matricula,
                                                     status=True, fechavence__lt=datetime.now().date()).exists():
                    return HttpResponseRedirect("/?info=Ud. aun no ha cancelado valores pendientes por matriculado")
                nivels = matricula.nivelmalla.orden

                if matricula.inscripcion.modalidad.id == 3:
                    puede_inscribirse = True
                    asig_vinculacion = obtener_materia_asignada_vinculacion_por_nivel_v2(matricula.id)
                    if not asig_vinculacion:
                        puede_inscribirse = False
                    elif not asignaturas_aprobadas_primero_nivel_especifico(matricula.inscripcion.id, asig_vinculacion.materia.asignaturamalla.nivelmalla.orden):
                        puede_inscribirse = False
                else:
                    nivel_itinerarios = ItinerariosVinculacionMalla.objects.filter(status=True, malla__carrera=carrera).values_list('nivel__orden', flat=True)
                    if len(nivel_itinerarios) == 1:
                        nivel_malla_itinerario = nivel_itinerarios.first()
                        puede_inscribirse = asignaturas_aprobadas_primero_nivel_especifico(matricula.inscripcion.id, nivel_malla_itinerario)
                    else:
                        puede_inscribirse = asignaturas_aprobadas_primero_nivel_especifico(matricula.inscripcion.id, matricula.nivelmalla.orden)
                        if not puede_inscribirse and 'panel' in request.GET and request.GET['panel'] and request.GET['panel'] == '2' and len(nivel_itinerarios) > 1:
                            data['niveles_itinerarios_vinculacion'] = nivel_itinerarios
                        if not puede_inscribirse and 'seleccion_nivel_estudiante' in request.GET and request.GET['seleccion_nivel_estudiante']:
                            data['seleccion_nivel_estudiante'] = request.GET['seleccion_nivel_estudiante']
                            puede_inscribirse = asignaturas_aprobadas_primero_nivel_especifico(matricula.inscripcion.id, int(request.GET['seleccion_nivel_estudiante']))
                data['puede_inscribirse'] = puede_inscribirse

                nivel_itinerario = ItinerariosVinculacionMalla.objects.filter(status=True, malla__carrera=carrera).values_list('nivel', flat=True).first()
                if nivel_itinerario:
                    data['nivelmallla'] = nivel_itinerario
                elif nivels <= 10 and nivels >= 4:
                    data['nivelmallla'] = 4

                proyectos = CarreraInscripcionVinculacion.objects.filter(carrera__carrera=carrera,
                                                                         periodo__fechainicio__lte=datetime.now(),
                                                                         periodo__fechafin__gte=datetime.now(),
                                                                         periodo__aprobado=True,
                                                                         periodo__periodo = periodo
                                                                         )
                solicitudes = ProyectoVinculacionInscripcion.objects.filter(inscripcion__persona=persona, status=True)
                misproyectos = ParticipantesMatrices.objects.filter(status=True, inscripcion__persona=persona, actividad__isnull = True)

                if 'panel' in request.GET:
                    panel = request.GET['panel']
                    if panel == '2':
                        data['proyectos'] = proyectos
                    elif panel == '3':
                        data['solicitudes'] = solicitudes
                else:
                    data['misproyectos'] = misproyectos

                data['panel'] = panel
                data['cantidad_solicitudes'] = solicitudes.count()
                data['cantidad_proyectos'] = proyectos.count()
                data['cantidad_misproyectos'] = misproyectos.count()
                return render(request, "alu_proyectovinculacion/view.html", data)
            except Exception as ex:
                pass
