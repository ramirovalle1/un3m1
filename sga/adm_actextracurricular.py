# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ActextracurricularForm, RegistrarCertificadoForm
from sga.funciones import MiPaginador, log
from sga.models import ActividadExtraCurricular, ParticipanteActividadExtraCurricular, Inscripcion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'editar':
                try:
                    f = ActextracurricularForm(request.POST)
                    if f.is_valid():
                        actividad = ActividadExtraCurricular.objects.get(pk=request.POST['id'])
                        actividad.responsable = f.cleaned_data['responsable']
                        if actividad.registrados() >= f.cleaned_data['cupo']:
                            actividad.cupo = actividad.registrados()
                        else:
                            actividad.cupo = f.cleaned_data['cupo']
                        actividad.aula = f.cleaned_data['aula']
                        actividad.nombre = f.cleaned_data['nombre']
                        actividad.tipo = f.cleaned_data['tipo']
                        actividad.fechainicio = f.cleaned_data['fechainicio']
                        actividad.fechafin = f.cleaned_data['fechafin']
                        actividad.horas = f.cleaned_data['horas']
                        actividad.permiteretirarse = f.cleaned_data['permiteretirarse']
                        actividad.periocidad = f.cleaned_data['periocidad']
                        actividad.carrera = f.cleaned_data['carrera']
                        actividad.calificar = f.cleaned_data['calificar']
                        actividad.asistminima = f.cleaned_data['asistminima']
                        actividad.coordinacion = f.cleaned_data['coordinacion']
                        if f.cleaned_data['calificar']:
                            actividad.calfmaxima = f.cleaned_data['califmaxima']
                            actividad.calfminima = f.cleaned_data['califminima']
                        else:
                            actividad.calfmaxima = 0
                            actividad.calfminima = 0
                        actividad.save(request)
                        for participante in actividad.participanteactividadextracurricular_set.all():
                            participante.save(request)
                        log(u'Modifico actividad extracurricular: %s' % actividad, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addactividad':
                try:
                    f = ActextracurricularForm(request.POST, empty_permitted='carrera')
                    if f.is_valid():
                        actividad = ActividadExtraCurricular(periodo=periodo,
                                                             nombre=f.cleaned_data['nombre'],
                                                             tipo=f.cleaned_data['tipo'],
                                                             fechainicio=f.cleaned_data['fechainicio'],
                                                             fechafin=f.cleaned_data['fechafin'],
                                                             horas=f.cleaned_data['horas'],
                                                             permiteretirarse=f.cleaned_data['permiteretirarse'],
                                                             periocidad=f.cleaned_data['periocidad'],
                                                             calfmaxima=f.cleaned_data['califmaxima'] if f.cleaned_data['calificar'] else 0,
                                                             calfminima=f.cleaned_data['califminima'] if f.cleaned_data['calificar'] else 0,
                                                             calificar=f.cleaned_data['calificar'],
                                                             asistminima=f.cleaned_data['asistminima'],
                                                             responsable=f.cleaned_data['responsable'],
                                                             coordinacion=f.cleaned_data['coordinacion'],
                                                             aula=f.cleaned_data['aula'],
                                                             cupo=f.cleaned_data['cupo'])
                        actividad.save(request)
                        actividad.carrera = f.cleaned_data['carrera']
                        actividad.save(request)
                        log(u'Adiciono actividad extracurricular: %s' % actividad, request, "add")
                        return JsonResponse({"result": "ok", "id": actividad.id})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'eliminar':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    if actividad.participanteactividadextracurricular_set.exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Existen estudiantes registrados."})
                    log(u'Elimino actividad extracurricular: %s' % actividad, request, "del")
                    actividad.delete()
                    return JsonResponse({"result": "ok", "id": actividad.id})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            elif action == 'certificado':
                try:
                    participante = ParticipanteActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    f = RegistrarCertificadoForm(request.POST)
                    if f.is_valid():
                        participante.certificado = f.cleaned_data['certificado']
                        participante.controlregistro = request.user
                        participante.save(request)
                        log(u'Confirmo actividad extracurricular: %s' % participante, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'registraactividad':
                try:
                    inscripcion = Inscripcion.objects.get(pk=request.POST['id'])
                    actividad = ActividadExtraCurricular.objects.get(pk=request.POST['ida'])
                    registro = ParticipanteActividadExtraCurricular(actividad=actividad,
                                                                    inscripcion=inscripcion,
                                                                    nota=0,
                                                                    asistencia=0)
                    registro.save(request)
                    log(u"Registro actividad extracurricular: %s" % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'eliminar':
                try:
                    data['title'] = u'Eliminar actividad'
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    data['actividad'] = actividad
                    return render(request, "adm_actextracurricular/eliminar.html", data)
                except Exception as ex:
                    pass

            if action == 'abriractividad':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    actividad.cerrado = False
                    actividad.save(request)
                    for participante in actividad.participanteactividadextracurricular_set.all():
                        participante.save(request)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'cerraractividad':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    actividad.cerrado = True
                    actividad.save(request)
                    for participante in actividad.participanteactividadextracurricular_set.all():
                        participante.save(request)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'editar':
                try:
                    data['title'] = u'Editar actividad extracurricular'
                    actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    form = ActextracurricularForm(initial={'nombre': actividad.nombre,
                                                           'tipo': actividad.tipo,
                                                           'fechainicio': actividad.fechainicio,
                                                           'fechafin': actividad.fechafin,
                                                           'horas': actividad.horas,
                                                           'calificar': actividad.calificar,
                                                           'califmaxima': actividad.calfmaxima,
                                                           'califminima': actividad.calfminima,
                                                           'asistminima': actividad.asistminima,
                                                           'permiteretirarse': actividad.permiteretirarse,
                                                           'periocidad': actividad.periocidad,
                                                           'coordinacion': actividad.coordinacion,
                                                           'responsable': actividad.responsable,
                                                           'cupo': actividad.cupo,
                                                           'aula': actividad.aula,
                                                           'carrera': actividad.carrera.all()})
                    data['form'] = form
                    data['actividad'] = actividad
                    return render(request, "adm_actextracurricular/editar.html", data)
                except Exception as ex:
                    pass

            elif action == 'addactividad':
                try:
                    data['title'] = u'Adicionar actividad extracurricular'
                    data['form'] = ActextracurricularForm()
                    return render(request, "adm_actextracurricular/addactividad.html", data)
                except Exception as ex:
                    pass

            elif action == 'registrados':
                try:
                    data['title'] = u'Registrados en esta actividad'
                    data['actividad'] = actividad = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    data['registrados'] = ParticipanteActividadExtraCurricular.objects.filter(actividad=actividad).order_by('inscripcion')
                    data['reporte_0'] = obtener_reporte('certificado_extracurricular')
                    return render(request, "adm_actextracurricular/registrados.html", data)
                except Exception as ex:
                    pass

            elif action == 'retirar':
                try:
                    participante = ParticipanteActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    actividad = participante.actividad
                    inscripcion = participante.inscripcion
                    log(u'Retiro de actividad extracurricular: %s' % participante, request, "del")
                    participante.delete()
                    return HttpResponseRedirect("/adm_actextracurricular?action=registrados&id=" + str(actividad.id))
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            elif action == 'certificado':
                try:
                    data['title'] = u'Registrar certificado'
                    data['participante'] = participante = ParticipanteActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    data['form'] = RegistrarCertificadoForm()
                    return render(request, "adm_actextracurricular/certificado.html", data)
                except Exception as ex:
                    pass

            elif action == 'actividades':
                try:
                    data['title'] = u'Adicionar actividad extracurricular'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    hoy = datetime.now().date()
                    data['actividades'] = ActividadExtraCurricular.objects.filter(Q(carrera__in=[inscripcion.carrera.id]) | Q(carrera__isnull=True), fechafin__gte=hoy).order_by('-fechafin').exclude(participanteactividadextracurricular__inscripcion=inscripcion)
                    return render(request, "adm_actextracurricular/actividades.html", data)
                except Exception as ex:
                    pass

            elif action == 'registraactividad':
                try:
                    data['title'] = u'Registrar en actividad'
                    data['inscripcion'] = inscripcion = Inscripcion.objects.get(pk=request.GET['id'])
                    data['actividad'] = actividad = ActividadExtraCurricular.objects.get(pk=request.GET['ida'])
                    return render(request, "adm_actextracurricular/registraactividad.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Listado de actividades extracurriculares'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                actividades = ActividadExtraCurricular.objects.filter(nombre__icontains=search).distinct().order_by('-fechainicio')
            elif 'id' in request.GET:
                ids = int(request.GET['id'])
                actividades = ActividadExtraCurricular.objects.filter(id=ids).order_by('-fechainicio')
            else:
                actividades = ActividadExtraCurricular.objects.all().order_by('-fechainicio')
            paging = MiPaginador(actividades, 25)
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
            data['actividades'] = page.object_list
            data['reporte_0'] = obtener_reporte("lista_alumnos_inscritos_actividad")
            return render(request, "adm_actextracurricular/view.html", data)