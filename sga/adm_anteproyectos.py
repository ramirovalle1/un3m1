# -*- coding: latin-1 -*-
from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import PREPROYECTO_ESTADO_APROBADO_ID, SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID
from sga.commonviews import adduserdata
from sga.forms import CalificarPreProyectoGradoForm, PreProyectoGradoForm, ResponderCambioDatosProyectoForm, \
    AsignarCalificadorPreProyectoForm
from sga.funciones import MiPaginador, log
from sga.models import PreProyectoGrado, ProyectoGrado, CambioDatosProyecto, Inscripcion, CalificacionPreproyecto


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'calificar':
            try:
                form = CalificarPreProyectoGradoForm(request.POST)
                preproyecto = PreProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    fecha = form.cleaned_data['fechaaprobacion']
                    if int(form.cleaned_data['estado']) == PREPROYECTO_ESTADO_APROBADO_ID:
                        proyecto = ProyectoGrado(preproyecto=preproyecto,
                                                 fechaaprobacion=form.cleaned_data['fechaaprobacion'],
                                                 fechaconsejo=form.cleaned_data['fechaconsejo'],
                                                 fechalimite=(datetime(fecha.year, fecha.month, fecha.day, 0, 0, 0) + timedelta(days=365)).date())
                        proyecto.save(request)
                    preproyecto.estado = form.cleaned_data['estado']
                    preproyecto.calificacion = form.cleaned_data['calificacion']
                    preproyecto.tutortitular = form.cleaned_data['tutortitular']
                    preproyecto.tutorsecundario = form.cleaned_data['tutorsecundario']
                    preproyecto.save(request)
                    log(u'Califico anteproyecto: %s' % preproyecto, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'asignarcalificador':
            try:
                form = AsignarCalificadorPreProyectoForm(request.POST)
                preproyecto = PreProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    if preproyecto.calificacionpreproyecto_set.filter(profesor=form.cleaned_data['profesor']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya esta asignado el docente."})
                    calificador = CalificacionPreproyecto(preproyecto=preproyecto,
                                                          profesor=form.cleaned_data['profesor'],
                                                          fechaasignacion=form.cleaned_data['fecha'])
                    calificador.save(request)
                    log(u'Asigno calificador de anteproyecto: %s' % calificador, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminarcalificador':
            try:
                calificador = CalificacionPreproyecto.objects.get(pk=request.POST['id'])
                log(u'Elimino calificador de anteproyecto: %s' % calificador, request, "del")
                calificador.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'respondercambiotitulo':
            try:
                form = ResponderCambioDatosProyectoForm(request.POST)
                solicitud = CambioDatosProyecto.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    solicitud.fechaaprobacion = datetime.now().date()
                    solicitud.estado = int(form.cleaned_data['estado'])
                    solicitud.respuesta = form.cleaned_data['respuesta']
                    solicitud.save(request)
                    if solicitud.estado == SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID:
                        preproyecto = solicitud.preproyectogrado
                        preproyecto.titulo = form.cleaned_data['titulo']
                        preproyecto.save(request)
                    log(u'Respuesta cambios anteproyecto: %s' % solicitud.preproyectogrado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'respondercambiotutor':
            try:
                form = ResponderCambioDatosProyectoForm(request.POST)
                solicitud = CambioDatosProyecto.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    solicitud.fechaaprobacion = datetime.now().date()
                    solicitud.estado = int(form.cleaned_data['estado'])
                    solicitud.respuesta = form.cleaned_data['respuesta']
                    solicitud.save(request)
                    if solicitud.estado == SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID:
                        preproyecto = solicitud.preproyectogrado
                        preproyecto.tutorsugerido = form.cleaned_data['tutor']
                        preproyecto.save(request)
                    log(u'Cambio tutor anteproyecto: %s' % solicitud.preproyectogrado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'respondercambiointegrante':
            try:
                form = ResponderCambioDatosProyectoForm(request.POST)
                solicitud = CambioDatosProyecto.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    solicitud.fechaaprobacion = datetime.now().date()
                    solicitud.estado = int(form.cleaned_data['estado'])
                    solicitud.respuesta = form.cleaned_data['respuesta']
                    solicitud.save(request)
                    if solicitud.estado == SOLICITUD_PREPROYECTO_ESTADO_APROBADO_ID:
                        preproyecto = solicitud.preproyectogrado
                        listado = request.POST['otrosintegrantes']
                        integrantes = Inscripcion.objects.filter(id__in=[int(x) for x in listado.split(',')]) if listado else []
                        preproyecto.inscripciones.clear()
                        for integrante in integrantes:
                            if integrante.tiene_proyecto_activo():
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"El estudiante " + integrante.persona.nombre_completo() + " se encuentra registrado en un proyecto."})
                            preproyecto.inscripciones.add(integrante)
                        preproyecto.save(request)
                    log(u'Cambio integrante anteproyecto: %s' % solicitud.preproyectogrado, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'calificar':
                try:
                    data['title'] = u'Calificar anteproyecto'
                    proyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto
                    data['form'] = CalificarPreProyectoGradoForm(initial={'fechaaprobacion': datetime.now().date(),
                                                                          'fechaconsejo': datetime.now().date(),
                                                                          'tutortitular': proyecto.tutorsugerido})
                    return render(request, "adm_anteproyectos/calificar.html", data)
                except Exception as ex:
                    pass

            if action == 'eliminarcalificador':
                try:
                    data['title'] = u'Eliminar calificador'
                    data['calificador'] = CalificacionPreproyecto.objects.get(pk=request.GET['id'])
                    return render(request, "adm_anteproyectos/eliminarcalificador.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    proyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = PreProyectoGradoForm(initial={'titulo': proyecto.titulo,
                                                                 'fecha': proyecto.fecha,
                                                                 'tipogrado': proyecto.tipogrado,
                                                                 'tipotrabajotitulacion': proyecto.tipotrabajotitulacion,
                                                                 'tutorsugerido': proyecto.tutor_principal(),
                                                                 'referencias': proyecto.referencias,
                                                                 'resultadoesperado': proyecto.resultadoesperado,
                                                                 'descripcionpropuesta': proyecto.descripcionpropuesta,
                                                                 'objetivogeneral': proyecto.objetivogeneral,
                                                                 'objetivoespecifico': proyecto.objetivoespecifico,
                                                                 'problema': proyecto.problema,
                                                                 'metodo': proyecto.metodo,
                                                                 'palabrasclaves': proyecto.palabrasclaves,
                                                                 'sublineainvestigacion': proyecto.sublineainvestigacion})
                    return render(request, "adm_anteproyectos/informacion.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitudes':
                try:
                    data['title'] = u'Solicitudes de cambios en el proyecto'
                    proyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto
                    data['solicitudes'] = proyecto.cambiodatosproyecto_set.all()
                    return render(request, "adm_anteproyectos/solicitudes.html", data)
                except Exception as ex:
                    pass

            if action == 'respondercambiotitulo':
                try:
                    data['title'] = u'Responder solicitud de cambio de titulo'
                    data['solicitud'] = solicitud = CambioDatosProyecto.objects.get(pk=request.GET['id'])
                    form = ResponderCambioDatosProyectoForm(initial={'solicitud': solicitud.solicitud,
                                                                     'motivo': solicitud.motivo,
                                                                     'titulo': solicitud.preproyectogrado.titulo})
                    form.sin_tutor()
                    data['form'] = form
                    return render(request, "adm_anteproyectos/respondercambiotitulo.html", data)
                except Exception as ex:
                    pass

            if action == 'respondercambiotutor':
                try:
                    data['title'] = u'Responder solicitud de cambio de tutor'
                    data['solicitud'] = solicitud = CambioDatosProyecto.objects.get(pk=request.GET['id'])
                    form = ResponderCambioDatosProyectoForm(initial={'solicitud': solicitud.solicitud,
                                                                     'motivo': solicitud.motivo,
                                                                     'tutor': solicitud.preproyectogrado.tutorsugerido})
                    form.sin_titulo()
                    data['form'] = form
                    return render(request, "adm_anteproyectos/respondercambiotutor.html", data)
                except Exception as ex:
                    pass

            if action == 'asignarcalificador':
                try:
                    data['title'] = u'Asignar docente para calificación'
                    data['preproyecto'] = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    form = AsignarCalificadorPreProyectoForm(initial={'fecha': datetime.now().date()})
                    data['form'] = form
                    return render(request, "adm_anteproyectos/asignarcalificador.html", data)
                except Exception as ex:
                    pass

            if action == 'calificadores':
                try:
                    data['title'] = u'Docentes asignados a calificar el anteproyecto'
                    data['preproyecto'] = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    return render(request, "adm_anteproyectos/calificadores.html", data)
                except Exception as ex:
                    pass

            if action == 'respondercambiointegrante':
                try:
                    data['title'] = u'Responder solicitud de cambio de integrantes'
                    data['solicitud'] = solicitud = CambioDatosProyecto.objects.get(pk=request.GET['id'])
                    form = ResponderCambioDatosProyectoForm(initial={'solicitud': solicitud.solicitud,
                                                                     'motivo': solicitud.motivo})
                    form.sin_titulo()
                    form.sin_tutor()
                    data['form'] = form
                    data['integrantes'] = solicitud.preproyectogrado.inscripciones.all()
                    return render(request, "adm_anteproyectos/respondercambiointegrante.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de anteproyectos de grado'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                proyectos = PreProyectoGrado.objects.filter(Q(titulo__icontains=search) |
                                                            Q(tutortitular__nombres__icontains=search) |
                                                            Q(tutortitular__apellido1__icontains=search) |
                                                            Q(tutortitular__apellido2__icontains=search) |
                                                            Q(referencias__icontains=search) |
                                                            Q(resultadoesperado__icontains=search) |
                                                            Q(descripcionpropuesta__icontains=search) |
                                                            Q(objetivogeneral__icontains=search) |
                                                            Q(objetivoespecifico__icontains=search) |
                                                            Q(problema__icontains=search) |
                                                            Q(palabrasclaves__icontains=search)).order_by('estado', '-fecha', 'titulo').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                proyectos = PreProyectoGrado.objects.filter(id=ids)
            else:
                proyectos = PreProyectoGrado.objects.all().order_by('estado', '-fecha', 'titulo').distinct()
            paging = MiPaginador(proyectos, 25)
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
            data['proyectos'] = page.object_list
            return render(request, "adm_anteproyectos/view.html", data)