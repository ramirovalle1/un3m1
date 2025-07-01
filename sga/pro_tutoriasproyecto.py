# -*- coding: latin-1 -*-
from datetime import datetime, date, timedelta
import json
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import DIAS_LIMITES_SUBIR_PROYECTO_GRADO_COMPLETO
from sga.commonviews import adduserdata
from sga.forms import ActaAvanceTutoriaForm, CalificacionDocenteAnteproyectoForm, \
    CitaTutoriaProyectoForm, CalificarAvanceProyectoForm, SubirUrkunProyectoCompletoForm
from sga.funciones import log, generar_nombre
from sga.models import Tutoria, MESES_CHOICES, ActaAvance, AsistenciaActaAvance, Inscripcion, \
    CalificacionPreproyecto, ProyectosGrado, TutoriaProyecto, FichaProyecto, FichaCalificacionProyecto


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
                proyect = ProyectosGrado.objects.get(pk=int(request.POST['proyecto']))
                nfecha = request.POST['fecha'].split('-')
                fecha = date(int(nfecha[2]), int(nfecha[1]), int(nfecha[0]))
                tutoria = TutoriaProyecto(proyectogrado=proyect,
                                          fechainicio=datetime.now().date(),
                                          fechafin=fecha,
                                          horainicio=datetime.now().time(),
                                          horafin=request.POST['hora'],
                                          anuncion=request.POST['anuncio'])
                tutoria.save(request)
                log(u'Adiciono una cita tutoria: %s' % tutoria, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'calificar':
            try:
                calificador = CalificacionPreproyecto.objects.get(pk=int(request.POST['id']))
                form = CalificacionDocenteAnteproyectoForm(request.POST)
                if form.is_valid():
                    calificador.calificacion = form.cleaned_data['calificacion']
                    calificador.calificado = True
                    calificador.fechacalificacion = datetime.now().date()
                    calificador.save(request)
                else:
                     raise NameError('Error')
                log(u'Califico anteproyecto: %s' % calificador, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'calificaravance':
            try:
                form = CalificarAvanceProyectoForm(request.POST)
                if form.is_valid():
                    tutoria = TutoriaProyecto.objects.get(pk=int(request.POST['id']))
                    tutoria.observacion = form.cleaned_data['observacion']
                    tutoria.estado = True
                    datos = json.loads(request.POST['lista_items1'])
                    if datos:
                        for elemento in datos:
                            fichacalificacion = FichaCalificacionProyecto(proyecto=tutoria.proyectogrado,
                                                                          ficha_id=int(elemento['idficha']),
                                                                          tutoria=tutoria,
                                                                          fecha=datetime.now().date(),
                                                                          estado=True)
                            fichacalificacion.save(request)
                    tutoria.save(request)
                    proyecto= ProyectosGrado.objects.get(pk=tutoria.proyectogrado.pk)
                    if proyecto.proyecto_completo():
                        fecha = datetime.now().date()
                        proyecto.fechainicioprocompleto=datetime.now().date()
                        proyecto.fechamaxprocompleto=(datetime(fecha.year, fecha.month, fecha.day, 0, 0,0) + timedelta(days=DIAS_LIMITES_SUBIR_PROYECTO_GRADO_COMPLETO)).date()
                        proyecto.save(request)
                else:
                     raise NameError('Error')
                log(u'Califico Tutoria: %s' % tutoria, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'del':
            try:
                tutoria = TutoriaProyecto.objects.get(pk=int(request.POST['id']))
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

        if action == 'subirurkun':
                try:
                    form = SubirUrkunProyectoCompletoForm(request.FILES)
                    if form.is_valid():
                        if 'archivo' in request.FILES:
                            proyecto = ProyectosGrado.objects.get(pk=int(request.POST['id']))
                            proyecto.fechaentregaurkun=datetime.now().date()
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("urkunproyectocompleto_", newfile._name)
                            proyecto.urkun= newfile
                            proyecto.save(request)
                            log(u'Subio Informe Urkun Proyecto: %s' % proyecto, request, "add")
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
                    return render(request, "pro_tutoriasproyecto/addacta.html", data)
                except Exception as ex:
                    pass

            if action == 'calificaravance':
                try:
                    data['title'] = u'Calificar Avance de Tutoria'
                    data['tutoria'] = tutoria = TutoriaProyecto.objects.get(pk=int(request.GET['id']))
                    data['form'] = CalificarAvanceProyectoForm(initial={'proyectogrado': tutoria.proyectogrado})
                    data['listacheck']= FichaCalificacionProyecto.objects.filter(proyecto_id=tutoria.proyectogrado, estado=True)
                    lista = FichaCalificacionProyecto.objects.values_list('ficha_id').filter(proyecto_id=tutoria.proyectogrado, estado=True)
                    data['listanocheck']=FichaProyecto.objects.filter(estado=True).exclude(pk__in=lista).distinct().order_by('nivel')
                    return render(request, "pro_tutoriasproyecto/calificaravance.html", data)
                except Exception as ex:
                    pass

            if action == 'subirurkunproyecto':
                try:
                    data['title'] = u'Subir Informe del Urkun'
                    data['proyecto'] = ProyectosGrado.objects.get(pk=int(request.GET['id']))
                    data['form'] = SubirUrkunProyectoCompletoForm()
                    return render(request, "pro_tutoriasproyecto/informeurkun.html", data)
                except Exception as ex:
                    pass

            if action == 'calificar':
                try:
                    data['title'] = u'Calificar anteproyecto'
                    data['calificador'] = CalificacionPreproyecto.objects.get(pk=int(request.GET['id']))
                    data['form'] = CalificacionDocenteAnteproyectoForm()
                    return render(request, "pro_tutorias/calificar.html", data)
                except Exception as ex:
                    pass

            if action == 'tutorias':
                try:
                    data['title'] = u'Calendario de tutorías'
                    proyecto = ProyectosGrado.objects.get(pk=request.GET['id'])
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

                    tutorias = TutoriaProyecto.objects.filter(fechafin__lte=fechafin, fechainicio__gte=fechainicio, proyectogrado=proyecto).order_by('fechafin')
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
                    num=0
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
                            tutoriasdias = proyecto.tutoriaproyecto_set.filter(fechafin=fecha).order_by('id')
                            diaact = []

                            for tutoria in tutoriasdias:
                                num=num+1
                                act = 'orange' + ',' + str(num)

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
                    data['form'] = CitaTutoriaProyectoForm(initial={'horafin': '12:00'})
                    return render(request, "pro_tutoriasproyecto/tutorias.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)

        else:
            data['title'] = u'Gestión de proyectos de grado'
            #data['proyectos'] = ProyectosGrado.objects.filter(proyecto__tutor=persona, estado=1).order_by('-fechaaprobacion', 'proyecto__titulo').distinct()[:10]
            data['proyectos'] = ProyectosGrado.objects.filter(tutor__persona=persona, estado=1).order_by('-fechaaprobacion', 'proyecto').distinct()[:10]
            data['calificadorpreproyectos'] = CalificacionPreproyecto.objects.filter(profesor__persona=persona).order_by('calificado', '-fechaasignacion').distinct()[:10]
            return render(request, "pro_tutoriasproyecto/view.html", data)