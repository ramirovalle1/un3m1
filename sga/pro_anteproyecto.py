# -*- coding: latin-1 -*-
from datetime import datetime, date, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from settings import MAX_NOTA, MIN_PROMEDIO_APROBACION, PREPROYECTO_ESTADO_RECHAZADO_ID
from sga.commonviews import adduserdata
from sga.forms import CitaTutoriaForm, ActaAvanceTutoriaForm, AnteproyectoForm, CalificarAntepoyectoForm
from sga.funciones import log, generar_nombre
from sga.models import ProyectoGrado, Tutoria, MESES_CHOICES, ActaAvance, AsistenciaActaAvance, Inscripcion, CalificacionProyecto, Anteproyecto


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'nuevacita':
            try:
                proyecto = ProyectoGrado.objects.get(pk=int(request.POST['proyecto']))
                nfecha = request.POST['fecha'].split('-')
                fecha = date(int(nfecha[2]), int(nfecha[1]), int(nfecha[0]))
                hora = request.POST['hora']
                lugar = request.POST['lugar']
                tutoria = Tutoria(proyecto=proyecto,
                                  fecha=fecha,
                                  hora=hora,
                                  lugar=lugar)
                tutoria.save(request)
                log(u'Adiciono cita tutoria: %s' % tutoria, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'calificar':
            try:
                calificador = CalificacionProyecto.objects.get(pk=int(request.POST['id']))
                form = CalificarAntepoyectoForm(request.POST)
                if form.is_valid():
                    calificador.calificacion = form.cleaned_data['calificacion']
                    calificador.calificado = True
                    calificador.fechacalificacion = datetime.now().date()
                    calificador.observacion=form.cleaned_data['observacion']
                    calificador.save(request)
                    if  calificador.anteproyecto.calificado_todo():
                        if calificador.anteproyecto.calificacion_promedio()<MIN_PROMEDIO_APROBACION:
                            antepro=Anteproyecto.objects.get(pk=calificador.anteproyecto.id)
                            antepro.estado=PREPROYECTO_ESTADO_RECHAZADO_ID
                            antepro.save(request)
                else:
                     raise NameError('Error')
                log(u'Califico anteproyecto: %s' % calificador, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'del':
            try:
                tutoria = Tutoria.objects.get(pk=int(request.POST['id']))
                log(u'Elimino tutoria: %s' % tutoria, request, "del")
                tutoria.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'addacta':
            try:
                tutoria = Tutoria.objects.get(pk=int(request.POST['id']))
                asistentes = request.POST['asistentes']
                inscripciones = Inscripcion.objects.filter(id__in=[int(x) for x in asistentes.split(',')]) if asistentes else []
                form = ActaAvanceTutoriaForm(request.POST, request.FILES)
                if form.is_valid():
                    if form.cleaned_data['porcientoavance'] < tutoria.proyecto.porcientoavance:
                        return JsonResponse({"result": "bad", "mensaje": u"El porciento de avance no puede ser menos a ." + str(tutoria.proyecto.porcientoavance)})
                    if form.cleaned_data['horafin'] <= form.cleaned_data['horainicio']:
                        return JsonResponse({"result": "bad", "mensaje": u"La hora fin no puede ser menor a la hora de inicio."})
                    acta = ActaAvance(tutoria=tutoria,
                                      inicio=form.cleaned_data['horainicio'],
                                      fin=form.cleaned_data['horafin'],
                                      sugerencia=form.cleaned_data['sugerencia'],
                                      porcientoavance=form.cleaned_data['porcientoavance'])
                    acta.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("tutoria_", newfile._name)
                        acta.archivo = newfile
                        acta.save(request)
                    for asistente in tutoria.proyecto.preproyecto.inscripciones.all():
                        asistencia = AsistenciaActaAvance(actaavance=acta,
                                                          inscripcion=asistente,
                                                          asistio=True if asistente in inscripciones else False)
                        asistencia.save(request)

                    proyecto = acta.tutoria.proyecto
                    proyecto.porcientoavance = acta.porcientoavance
                    proyecto.save(request)
                    log(u'Adiciono acta de avance: %s' % tutoria, request, "add")
                else:
                     raise NameError('Error')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addacta':
                try:
                    data['title'] = u'Registrar acta de avance de tutoría'
                    data['tutoria'] = tutoria = Tutoria.objects.get(pk=int(request.GET['id']))
                    form = ActaAvanceTutoriaForm(initial={'horainicio': str(tutoria.hora),
                                                          'horafin': str((datetime(tutoria.fecha.year, tutoria.fecha.month, tutoria.fecha.day, tutoria.hora.hour, tutoria.hora.minute, 0) + timedelta(hours=1)).time()),
                                                          'porcientoavance': tutoria.proyecto.porcientoavance})

                    data['form'] = form
                    data['asistentes'] = tutoria.proyecto.preproyecto.inscripciones.all()
                    return render(request, "pro_tutorias/addacta.html", data)
                except Exception as ex:
                    pass

            if action == 'consultaracta':
                try:
                    data['title'] = u'Acta de avance de tutoría'
                    data['permite_modificar'] = False
                    data['tutoria'] = tutoria = Tutoria.objects.get(pk=int(request.GET['id']))
                    data['acta'] = acta = tutoria.acta()
                    form = ActaAvanceTutoriaForm(initial={'horainicio': str(acta.inicio),
                                                          'horafin': str(acta.fin),
                                                          'porcientoavance': acta.porcientoavance,
                                                          'sugerencia': acta.sugerencia})
                    form.sin_archivo()
                    data['form'] = form
                    data['asistentes'] = acta.asistenciaactaavance_set.all()
                    return render(request, "pro_tutorias/consultaracta.html", data)
                except Exception as ex:
                    pass

            if action == 'asistenciastutorias':
                try:
                    data['title'] = u'Asistencias de tutoría'
                    data['proyecto'] = proyecto = ProyectoGrado.objects.get(pk=int(request.GET['id']))
                    data['tutorias'] = tutorias = proyecto.tutoria_set.all()
                    data['estudiantes'] = proyecto.preproyecto.inscripciones.all()
                    data['cantidad'] = tutorias.count()
                    return render(request, "pro_tutorias/asistenciastutorias.html", data)
                except Exception as ex:
                    pass

            if action == 'calificar':
                try:
                    data['title'] = u'Calificar Anteproyecto'
                    data['calificador'] = CalificacionProyecto.objects.get(pk=int(request.GET['id']))
                    data['form'] = CalificarAntepoyectoForm()
                    data['max_nota'] = MAX_NOTA
                    return render(request, "pro_anteproyecto/calificar.html", data)
                except Exception as ex:
                    pass

            if action == 'informacion':
                try:
                    data['title'] = u'Información del proyecto'
                    data['permite_modificar'] = False
                    proyecto = Anteproyecto.objects.get(pk=request.GET['id'])
                    form = AnteproyectoForm(initial={'titulo': proyecto.titulo,
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
                    form.editar()
                    data['form'] = form
                    return render(request, "pro_anteproyecto/informacion.html", data)
                except Exception as ex:
                    pass

            if action == 'tutorias':
                try:
                    data['title'] = u'Calendario de tutorías'
                    proyecto = ProyectoGrado.objects.get(pk=request.GET['id'])
                    data['proyecto'] = proyecto
                    hoy = datetime.now().date()
                    panio = hoy.year
                    pmes = hoy.month
                    fecha = hoy
                    if 'proximo' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes + 1
                        if pmes == 13:
                            pmes = 1
                            panio = anio + 1
                        else:
                            panio = anio
                    if 'anterior' in request.GET:
                        mes = int(request.GET['mes'])
                        anio = int(request.GET['anio'])
                        pmes = mes - 1
                        if pmes == 0:
                            pmes = 12
                            panio = anio - 1
                        else:
                            panio = anio
                    fechainicio = date(panio, pmes, 1)
                    try:
                        fechafin = date(panio, pmes, 31)
                    except Exception as ex:
                        try:
                            fechafin = date(panio, pmes, 30)
                        except Exception as ex:
                            try:
                                fechafin = date(panio, pmes, 29)
                            except Exception as ex:
                                fechafin = date(panio, pmes, 28)

                    tutorias = Tutoria.objects.filter(fecha__lte=fechafin, fecha__gte=fechainicio, proyecto=proyecto)
                    s_anio = panio
                    s_mes = pmes
                    s_dia = 1
                    data['mes'] = MESES_CHOICES[s_mes - 1]
                    data['tutorias'] = tutorias
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    lista = {}
                    listaadicionartutoria = {}
                    listatutorias = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        diatut = {i: False}
                        tutoriadia = {i: None}
                        lista.update(dia)
                        listaadicionartutoria.update(diatut)
                        listatutorias.update(tutoriadia)
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(s_anio, s_mes, s_dia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(s_anio, s_mes, s_dia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: s_dia}
                            lista.update(dia)
                            if date(s_anio, s_mes, s_dia) > hoy:
                                diatut = {i[0]: True}
                                listaadicionartutoria.update(diatut)
                            tutoriasdias = proyecto.tutoria_set.filter(fecha=fecha).order_by('id')
                            diaact = []
                            for tutoria in tutoriasdias:
                                act = 'orange' + ',' + tutoria.id.__str__()
                                diaact.append(act)
                            listatutorias.update({i[0]: diaact})
                            s_dia += 1
                    data['dias_mes'] = lista
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['daymonth'] = 1
                    data['s_anio'] = s_anio
                    data['s_mes'] = s_mes
                    data['lista'] = lista
                    data['listatutorias'] = listatutorias
                    data['listaadicionartutoria'] = listaadicionartutoria
                    data['dia_actual'] = datetime.now().date().day
                    data['mostrar_dia_actual'] = fecha.month == datetime.now().date().month and fecha.year == datetime.now().date().year
                    data['form'] = CitaTutoriaForm(initial={'hora': '12:00'})
                    return render(request, "pro_tutorias/tutorias.html", data)
                except Exception as ex:
                    pass
            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Calificación de Anteproyecto'
            data['calificadoranteproyectos'] = CalificacionProyecto.objects.filter(profesor__persona=persona).order_by('calificado', '-fechaasignacion').distinct()[:10]
            return render(request, "pro_anteproyecto/view.html", data)