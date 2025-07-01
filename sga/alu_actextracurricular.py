# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.funciones import log, MiPaginador
from sga.models import ActividadExtraCurricular, ParticipanteActividadExtraCurricular


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
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'retirarse':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    if not actividad.permiteretirarse:
                        return JsonResponse({"result": "bad", "mensaje": u"No se permite retirarse de la actividad."})
                    registro = ParticipanteActividadExtraCurricular.objects.filter(actividad=actividad, inscripcion=inscripcion)[0]
                    log(u'Retiro de actividad extracurricular: %s' % registro, request, "del")
                    registro.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

            if action == 'registrarse':
                try:
                    actividad = ActividadExtraCurricular.objects.get(pk=request.POST['id'])
                    if actividad.participanteactividadextracurricular_set.values('id').count() >= actividad.cupo:
                        return JsonResponse({"result": "bad", "mensaje": u"Ya no existe cupo para la actividad."})
                    if not ParticipanteActividadExtraCurricular.objects.values('id').filter(actividad=actividad, inscripcion=inscripcion).exists():
                        registro = ParticipanteActividadExtraCurricular(actividad=actividad,
                                                                        inscripcion=inscripcion,
                                                                        nota=0,
                                                                        asistencia=0)
                        registro.save()
                        log(u'Registro alumno en actividad extracurricular: %s' % registro, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Actividades extracurriculares'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'retirarse':
                try:
                    data['title'] = u'Desea retirarse de la actividad extracurricular'
                    data['actividad'] = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    return render(request, "alu_actextracurricular/retirarse.html", data)
                except Exception as ex:
                    pass

            if action == 'registrarse':
                try:
                    data['title'] = u'Registrarse en la actividad extracurricular'
                    data['actividad'] = ActividadExtraCurricular.objects.get(pk=request.GET['id'])
                    return render(request, "alu_actextracurricular/registrarse.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Programación de actividades extracurriculares'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                actividades = ActividadExtraCurricular.objects.filter((Q(cerrado=False) | Q(participanteactividadextracurricular__inscripcion=inscripcion)), nombre__icontains=search).order_by('-fechafin').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                actividades = ActividadExtraCurricular.objects.filter((Q(cerrado=False) | Q(participanteactividadextracurricular__inscripcion=inscripcion)), id=ids).order_by('-fechafin').distinct()
            else:
                actividades = ActividadExtraCurricular.objects.filter((Q(cerrado=False) | Q(participanteactividadextracurricular__inscripcion=inscripcion))).order_by('-fechafin').distinct()
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
            data['inscripcion'] = inscripcion
            return render(request, "alu_actextracurricular/view.html", data)
