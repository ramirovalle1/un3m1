# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import RegistroProyectosVinculacionForm
from sga.funciones import MiPaginador, log
from sga.models import ProyectosVinculacion, ParticipanteProyectoVinculacion


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
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'registro':
                try:
                    proyecto = ProyectosVinculacion.objects.get(pk=request.POST['id'])
                    participante = ParticipanteProyectoVinculacion(proyecto=proyecto,
                                                                   inscripcion=inscripcion,
                                                                   nota=0,
                                                                   asistencia=0,
                                                                   lider_grupo=False)
                    participante.save(request)
                    log(u'Alumno registro vinculacion: %s [%s] - %s [%s]' % (proyecto, proyecto.id, participante, participante.id), request, "add")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'registro':
                try:
                    data['title'] = u'Registro en proyectos de vinculación'
                    proyecto = ProyectosVinculacion.objects.get(pk=request.GET['id'])
                    form = RegistroProyectosVinculacionForm(initial={'condiciones': proyecto.condiciones})
                    form.solo_lectura()
                    data['form'] = form
                    data['proyecto'] = proyecto
                    return render(request, "alu_vinculacion/registro.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Proyectos de vinculación con la comunidad'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                proyectos = ProyectosVinculacion.objects.filter(Q(participanteproyectovinculacion__inscripcion=inscripcion), nombre__icontains=search).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                proyectos = ProyectosVinculacion.objects.filter((Q(participanteproyectovinculacion__inscripcion=inscripcion)), id=ids).distinct()
            else:
                proyectos = ProyectosVinculacion.objects.filter((Q(participanteproyectovinculacion__inscripcion=inscripcion)) | (Q(cerrado=False))).distinct()
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
            data['inscripcion'] = inscripcion
            return render(request, "alu_vinculacion/view.html", data)