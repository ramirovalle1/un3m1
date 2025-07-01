# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import PREPROYECTO_ESTADO_PENDIENTE_ID, PREPROYECTO_CAMBIOTITULO_ID, \
    SOLICITUD_PREPROYECTO_ESTADO_PENDIENTE_ID, PREPROYECTO_CAMBIOINTEGRANTE_ID, PREPROYECTO_CAMBIOTUTOR_ID
from sga.commonviews import adduserdata
from sga.forms import PreProyectoGradoForm, CambioDatosProyectoForm
from sga.funciones import generar_nombre, log, variable_valor
from sga.models import PreProyectoGrado, CambioDatosProyecto, Tutoria, AsistenciaActaAvance, Inscripcion, miinstitucion, \
    CUENTAS_CORREOS
from sga.tasks import send_html_mail, conectar_cuenta


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = PreProyectoGradoForm(request.POST)
                if form.is_valid():
                    if PreProyectoGrado.objects.filter(titulo=form.cleaned_data['titulo']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proyecto con este titulo registrado."})
                    listado = request.POST['otrosintegrantes']
                    integrantes = Inscripcion.objects.filter(id__in=[int(x) for x in listado.split(',')]) if listado else []
                    for integrante in integrantes:
                        if integrante.tiene_proyecto_activo():
                            return JsonResponse({"result": "bad", "mensaje": u"El estudiante " + integrante.persona.nombre_completo() + " ya se encuentra registrado en un proyecto."})
                    if form.cleaned_data['fecha'] > datetime.now().date():
                        return JsonResponse({"result": "bad", "mensaje": u"La fecha no puede ser mayor que hoy."})
                    preproyecto = PreProyectoGrado(titulo=form.cleaned_data['titulo'],
                                                   fecha=form.cleaned_data['fecha'],
                                                   tipogrado=form.cleaned_data['tipogrado'],
                                                   tipotrabajotitulacion=form.cleaned_data['tipotrabajotitulacion'],
                                                   tutorsugerido=form.cleaned_data['tutorsugerido'],
                                                   estado=PREPROYECTO_ESTADO_PENDIENTE_ID,
                                                   referencias=form.cleaned_data['referencias'],
                                                   resultadoesperado=form.cleaned_data['resultadoesperado'],
                                                   descripcionpropuesta=form.cleaned_data['descripcionpropuesta'],
                                                   objetivogeneral=form.cleaned_data['objetivogeneral'],
                                                   objetivoespecifico=form.cleaned_data['objetivoespecifico'],
                                                   problema=form.cleaned_data['problema'],
                                                   metodo=form.cleaned_data['metodo'],
                                                   palabrasclaves=form.cleaned_data['palabrasclaves'],
                                                   sublineainvestigacion=form.cleaned_data['sublineainvestigacion'])
                    preproyecto.save(request)
                    for integrante in integrantes:
                        preproyecto.inscripciones.add(integrante)
                    send_html_mail("Registro anteproyecto", "emails/nuevoanteproyecto.html", {'sistema': request.session['nombresistema'], 'anteproyecto': preproyecto, 't': miinstitucion()}, inscripcion.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiotitulo':
            try:
                form = CambioDatosProyectoForm(request.POST, request.FILES)
                preproyecto = PreProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("solicitud_", newfile._name)
                    solicitud = CambioDatosProyecto(preproyectogrado=preproyecto,
                                                    fechasolicitud=datetime.now().date(),
                                                    tipocambio=PREPROYECTO_CAMBIOTITULO_ID,
                                                    solicitud=form.cleaned_data['solicitud'],
                                                    motivo=form.cleaned_data['motivo'],
                                                    nuevotitulo=form.cleaned_data['nuevotitulo'],
                                                    estado=SOLICITUD_PREPROYECTO_ESTADO_PENDIENTE_ID,
                                                    archivo=newfile)
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'delsolicitud':
            try:
                solicitud = CambioDatosProyecto.objects.get(pk=request.POST['id'])
                if solicitud.esta_pendiente():
                    solicitud.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'cambiotutor':
            try:
                form = CambioDatosProyectoForm(request.POST, request.FILES)
                preproyecto = PreProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("solicitud_", newfile._name)
                    solicitud = CambioDatosProyecto(preproyectogrado=preproyecto,
                                                    fechasolicitud=datetime.now().date(),
                                                    tipocambio=PREPROYECTO_CAMBIOTUTOR_ID,
                                                    solicitud=form.cleaned_data['solicitud'],
                                                    motivo=form.cleaned_data['motivo'],
                                                    estado=SOLICITUD_PREPROYECTO_ESTADO_PENDIENTE_ID,
                                                    archivo=newfile)
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cambiointegrante':
            try:
                form = CambioDatosProyectoForm(request.POST, request.FILES)
                preproyecto = PreProyectoGrado.objects.get(pk=request.POST['id'])
                if form.is_valid():
                    newfile = None
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("solicitud_", newfile._name)
                    solicitud = CambioDatosProyecto(preproyectogrado=preproyecto,
                                                    fechasolicitud=datetime.now().date(),
                                                    tipocambio=PREPROYECTO_CAMBIOINTEGRANTE_ID,
                                                    solicitud=form.cleaned_data['solicitud'],
                                                    motivo=form.cleaned_data['motivo'],
                                                    estado=SOLICITUD_PREPROYECTO_ESTADO_PENDIENTE_ID,
                                                    archivo=newfile)
                    solicitud.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'confirmar':
            try:
                tutoria = Tutoria.objects.get(pk=request.POST['id'])
                asistencia = AsistenciaActaAvance.objects.filter(actaavance=tutoria.acta(), inscripcion=inscripcion)[0]
                asistencia.confirmado = True
                asistencia.save(request)
                acta = tutoria.acta()
                acta.confirmada = True
                acta.save(request)
                tutoria.asistio = True
                tutoria.save(request)
                log(u'Confirmo tutoria: %s' % tutoria, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Adicionar preproyecto'
                    data['inscripcion'] = inscripcion
                    data['form'] = PreProyectoGradoForm(initial={'fecha': datetime.now().date()})
                    return render(request, "alu_tutorias/add.html", data)
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
                    return render(request, "alu_tutorias/informacion.html", data)
                except Exception as ex:
                    pass

            if action == 'solicitudes':
                try:
                    data['title'] = u'Solicitudes de cambios en el proyecto'
                    data['proyecto'] = proyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['solicitudes'] = proyecto.cambiodatosproyecto_set.all()
                    return render(request, "alu_tutorias/solicitudes.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiotitulo':
                try:
                    data['title'] = u'Solicitud de cambio de titulo'
                    data['preproyecto'] = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['form'] = CambioDatosProyectoForm()
                    return render(request, "alu_tutorias/cambiotitulo.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiotutor':
                try:
                    data['title'] = u'Solicitud de cambio de tutor'
                    data['preproyecto'] = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    form = CambioDatosProyectoForm()
                    form.sin_titulo()
                    data['form'] = form
                    return render(request, "alu_tutorias/cambiotutor.html", data)
                except Exception as ex:
                    pass

            if action == 'cambiointegrante':
                try:
                    data['title'] = u'Solicitud de cambio de integrante'
                    data['preproyecto'] = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    form = CambioDatosProyectoForm()
                    form.sin_titulo()
                    data['form'] = form
                    return render(request, "alu_tutorias/cambiointegrante.html", data)
                except Exception as ex:
                    pass

            if action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud'
                    data['solicitud'] = CambioDatosProyecto.objects.get(pk=request.GET['id'])
                    return render(request, "alu_tutorias/delsolicitud.html", data)
                except Exception as ex:
                    pass

            if action == 'tutorias':
                try:
                    data['title'] = u'Seguimiento a tutorias'
                    preproyecto = PreProyectoGrado.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto = preproyecto.proyecto_grado()
                    data['tutorias'] = proyecto.tutoria_set.all()
                    data['inscripcion'] = inscripcion
                    return render(request, "alu_tutorias/tutorias.html", data)
                except Exception as ex:
                    pass

            if action == 'confirmar':
                try:
                    data['title'] = u'Confirmar tutorias'
                    data['tutoria'] = Tutoria.objects.get(pk=request.GET['id'])
                    return render(request, "alu_tutorias/confirmar.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestion de anteproyectos y proyectos de grado'
            # if not inscripcion.tiene_porciento_cumplimiento_malla():
            #     return HttpResponseRedirect("/?info=Debe de cumplir con el % requerido de su malla para presentar un anteproyecto.")
            data['misproyectos'] = PreProyectoGrado.objects.filter(inscripciones=inscripcion)
            return render(request, "alu_tutorias/view.html", data)